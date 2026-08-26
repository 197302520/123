from unittest.mock import patch
from datetime import timedelta

import pytest
from celery import current_app
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from learning import tasks
from learning.models import Run


PATH3 = {
    "directed": True,
    "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
    "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}],
}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_result_is_unavailable_until_a_pending_run_has_a_real_result(api_client):
    """Returning 200 for an empty pending result would falsely report usable output."""
    run = Run.objects.create(algorithm="centrality.pagerank", graph=PATH3, parameters={}, seed=7)
    response = api_client.get(f"/api/runs/{run.id}/result/")

    assert response.status_code == 409
    assert response.json()["status"] == "pending"


@pytest.mark.django_db
def test_worker_records_completed_and_failed_terminal_states_without_fabricated_results(api_client):
    """A worker exception must not leave a run completed with an empty result."""
    successful = Run.objects.create(algorithm="centrality.pagerank", graph=PATH3, parameters={}, seed=7)
    failed = Run.objects.create(algorithm="does.not.exist", graph=PATH3, parameters={}, seed=7)

    tasks.execute_run_job(str(successful.id))
    tasks.execute_run_job(str(failed.id))
    successful.refresh_from_db()
    failed.refresh_from_db()

    assert successful.status == "completed" and successful.result["tables"]
    assert successful.started_at is not None and successful.finished_at is not None
    assert failed.status == "failed" and not failed.result
    assert failed.error["code"] == "unsupported_algorithm"
    assert api_client.get(f"/api/runs/{failed.id}/result/").status_code == 409


@pytest.mark.django_db
def test_worker_does_not_reexecute_completed_or_cancelled_terminal_runs():
    """A duplicate queue delivery must not overwrite terminal output or revive cancellation."""
    completed = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, seed=7,
        status=Run.Status.COMPLETED, result={"tables": [{"key": "sentinel"}]},
    )
    cancelled = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, seed=7,
        status=Run.Status.CANCELLED,
    )
    running = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, seed=7,
        status=Run.Status.RUNNING, result={"tables": [{"key": "in-progress-sentinel"}]},
    )

    assert tasks.execute_run_job(str(completed.id)) == "completed"
    assert tasks.execute_run_job(str(cancelled.id)) == "cancelled"
    assert tasks.execute_run_job(str(running.id)) == "running"
    completed.refresh_from_db()
    cancelled.refresh_from_db()
    running.refresh_from_db()
    assert completed.result == {"tables": [{"key": "sentinel"}]}
    assert cancelled.status == "cancelled" and cancelled.result == {}
    assert running.status == "running" and running.result == {"tables": [{"key": "in-progress-sentinel"}]}


@pytest.mark.django_db
def test_cache_key_uses_normalized_graph_parsed_defaults_algorithm_version_and_seed(api_client):
    """Hashing raw JSON would miss semantically identical requests with explicit defaults."""
    first_payload = {"algorithm": "centrality.pagerank", "graph": PATH3, "parameters": {}, "seed": 11}
    explicit_payload = {
        "algorithm": "centrality.pagerank",
        "graph": {"directed": True, "nodes": list(reversed(PATH3["nodes"])), "edges": list(reversed(PATH3["edges"]))},
        "parameters": {"alpha": 0.85, "max_iterations": 200, "tolerance": 1e-6},
        "seed": 11,
    }
    first = api_client.post("/api/runs/", first_payload, format="json").json()
    second = api_client.post("/api/runs/", explicit_payload, format="json").json()
    third = api_client.post("/api/runs/", {**first_payload, "seed": 12}, format="json").json()
    first_run, second_run, third_run = [Run.objects.get(pk=item["id"]) for item in (first, second, third)]

    assert len(first_run.cache_key) == 64
    assert second_run.cache_key == first_run.cache_key
    assert second_run.cached_from_id == first_run.id
    assert second_run.result == first_run.result
    assert third_run.cache_key != first_run.cache_key
    assert third_run.cached_from_id is None


@pytest.mark.django_db
def test_cache_canonicalizes_endpoint_order_for_undirected_edges(api_client):
    """The same undirected graph must cache-hit when an edge is submitted in reverse order."""
    graph = {**PATH3, "directed": False}
    reversed_graph = {
        **graph,
        "edges": [{"source": edge["target"], "target": edge["source"]} for edge in reversed(graph["edges"])],
    }
    payload = {"algorithm": "centrality.degree", "graph": graph, "parameters": {}, "seed": 7}
    first = api_client.post("/api/runs/", payload, format="json")
    second = api_client.post("/api/runs/", {**payload, "graph": reversed_graph}, format="json")

    first_run = Run.objects.get(pk=first.json()["id"])
    second_run = Run.objects.get(pk=second.json()["id"])
    assert second_run.cache_key == first_run.cache_key
    assert second_run.cached_from_id == first_run.id


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_queue_delivery_failure_records_failed_state_without_leaking_broker_details(api_client, caplog):
    """A broker outage must not strand a run in pending or expose connection details."""
    payload = {"algorithm": "centrality.pagerank", "graph": PATH3, "parameters": {}, "seed": 7}
    with caplog.at_level("ERROR"):
        with (
            patch("learning.views.execute_run_job.delay", side_effect=RuntimeError("redis://secret@broker")),
            patch("learning.views.execute_run_job.apply_async", side_effect=RuntimeError("redis://secret@broker")),
        ):
            response = api_client.post("/api/runs/", payload, format="json")

    run = Run.objects.latest("created_at")
    assert response.status_code == 503
    assert run.status == Run.Status.FAILED
    assert run.result == {}
    assert run.error == {"code": "queue_unavailable", "message": "任务队列暂时不可用，请稍后重试。", "path": ""}
    assert "secret" not in response.content.decode()
    assert str(run.id) in caplog.text and "centrality.pagerank" in caplog.text
    assert "secret" not in caplog.text


@pytest.mark.django_db
def test_public_cancel_is_idempotent_revokes_pending_task_and_prevents_execution(api_client):
    """A cancelled pending job must never run, even if its queue message is later delivered."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={
            "alpha": 0.85, "max_iterations": 200, "tolerance": 1e-6,
        }, seed=7,
    )
    assert hasattr(run, "task_id"), "Run must persist its Celery task identifier"
    run.task_id = f"run-{run.id}"
    run.save(update_fields=["task_id"])
    with patch.object(current_app.control, "revoke") as revoke:
        first = api_client.post(f"/api/runs/{run.id}/cancel/", {}, format="json")
        second = api_client.post(f"/api/runs/{run.id}/cancel/", {}, format="json")

    run.refresh_from_db()
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "cancelled"
    assert run.status == Run.Status.CANCELLED and run.finished_at is not None and run.result == {}
    revoke.assert_called_once_with(run.task_id, terminate=False)
    assert tasks.execute_run_job(str(run.id)) == Run.Status.CANCELLED


@pytest.mark.django_db
def test_running_cancellation_wins_the_worker_result_race(api_client, monkeypatch):
    """A worker finishing after cancellation must discard its computed result."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={
            "alpha": 0.85, "max_iterations": 200, "tolerance": 1e-6,
        }, seed=7,
    )
    assert hasattr(run, "task_id"), "Run must persist its Celery task identifier"
    run.task_id = "running-task"
    run.save(update_fields=["task_id"])

    def cancel_during_compute(*args, **kwargs):
        response = api_client.post(f"/api/runs/{run.id}/cancel/", {}, format="json")
        assert response.status_code == 200
        return {"tables": [{"key": "late-result"}]}

    monkeypatch.setattr(tasks, "execute_algorithm", cancel_during_compute)
    with patch.object(current_app.control, "revoke"):
        state = tasks.execute_run_job(str(run.id))

    run.refresh_from_db()
    assert state == Run.Status.CANCELLED
    assert run.status == Run.Status.CANCELLED and run.result == {}


@pytest.mark.django_db
def test_running_cancellation_also_wins_an_algorithm_error_race(api_client, monkeypatch):
    """A late algorithm error must not make a user-cancelled run appear failed."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="error-race-task",
    )

    def cancel_then_fail(*args, **kwargs):
        response = api_client.post(f"/api/runs/{run.id}/cancel/", {}, format="json")
        assert response.status_code == 200
        raise tasks.AlgorithmInputError("late failure")

    monkeypatch.setattr(tasks, "execute_algorithm", cancel_then_fail)
    with patch.object(current_app.control, "revoke"):
        state = tasks.execute_run_job(str(run.id))

    run.refresh_from_db()
    assert state == Run.Status.CANCELLED
    assert run.status == Run.Status.CANCELLED and run.result == {}


@pytest.mark.django_db
@override_settings(RUN_LEASE_SECONDS=60)
def test_cleanup_marks_stale_running_jobs_failed_instead_of_leaving_them_forever():
    """A worker lost after claiming a run must have an explicit terminal recovery path."""
    stale = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, status=Run.Status.RUNNING,
        started_at=timezone.now() - timedelta(seconds=61),
    )

    tasks.cleanup_expired_runs()

    stale.refresh_from_db()
    assert stale.status == Run.Status.FAILED
    assert stale.error["code"] == "worker_lease_expired"
    assert stale.finished_at is not None


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_submission_stores_task_id_and_routes_optional_gnn_work_to_ml_queue(api_client):
    """Optional GNN jobs must be addressable for cancellation and isolated on the ML worker."""
    with (
        patch("learning.views.execute_run_job.delay") as delay,
        patch("learning.views.execute_run_job.apply_async") as apply_async,
    ):
        regular = api_client.post("/api/runs/", {
            "algorithm": "centrality.pagerank", "graph": PATH3, "parameters": {}, "seed": 101,
        }, format="json")
        gnn = api_client.post("/api/runs/", {
            "algorithm": "embedding.gcn", "graph": {**PATH3, "directed": False},
            "parameters": {"clusters": 2, "epochs": 1}, "seed": 102,
        }, format="json")

    assert regular.status_code == 201 and gnn.status_code == 201
    regular_run = Run.objects.get(pk=regular.json()["id"])
    gnn_run = Run.objects.get(pk=gnn.json()["id"])
    assert getattr(regular_run, "task_id", "").startswith("run-") and getattr(gnn_run, "task_id", "").startswith("run-")
    calls = apply_async.call_args_list
    assert calls[0].kwargs == {"args": [str(regular_run.id)], "task_id": regular_run.task_id, "queue": "default"}
    assert calls[1].kwargs == {"args": [str(gnn_run.id)], "task_id": gnn_run.task_id, "queue": "ml"}
    assert not delay.called


@pytest.mark.django_db
def test_unexpected_worker_error_logs_sanitized_trace_with_run_identifiers(caplog, monkeypatch):
    """Operations need a traceback and identifiers without graph/text content in logs."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
    )
    assert hasattr(run, "task_id"), "Run must persist its Celery task identifier"
    run.task_id = "worker-log-task"
    run.save(update_fields=["task_id"])
    monkeypatch.setattr(tasks, "execute_algorithm", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("GRAPH-CONTENT-SECRET")))

    with caplog.at_level("ERROR"):
        tasks.execute_run_job(str(run.id))

    assert str(run.id) in caplog.text and "worker-log-task" in caplog.text and "centrality.pagerank" in caplog.text
    assert "GRAPH-CONTENT-SECRET" not in caplog.text

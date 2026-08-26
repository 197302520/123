from unittest.mock import patch
from datetime import timedelta
import time
import json

import pytest
from celery import current_app
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from learning import tasks
from learning import job_runner
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
def test_queue_delivery_failure_stays_pending_for_reconciliation_without_leaking_broker_details(api_client, caplog):
    """A broker outage must schedule reconciliation, not fabricate a failed algorithm result."""
    payload = {"algorithm": "centrality.pagerank", "graph": PATH3, "parameters": {}, "seed": 7}
    with caplog.at_level("ERROR"):
        with (
            patch("learning.views.execute_run_job.delay", side_effect=RuntimeError("redis://secret@broker")),
            patch("learning.views.execute_run_job.apply_async", side_effect=RuntimeError("redis://secret@broker")),
        ):
            response = api_client.post("/api/runs/", payload, format="json")

    run = Run.objects.latest("created_at")
    assert response.status_code == 201
    assert response.json()["id"] == str(run.id)
    assert response.json()["status"] == Run.Status.PENDING
    assert run.status == Run.Status.PENDING
    assert run.result == {}
    assert run.error == {}
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
    with patch.object(current_app.control, "revoke") as revoke:
        state = tasks.execute_run_job(str(run.id))

    run.refresh_from_db()
    assert state == Run.Status.CANCELLED
    assert run.status == Run.Status.CANCELLED and run.result == {}
    revoke.assert_not_called()


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
        lease_expires_at=timezone.now() - timedelta(seconds=1),
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
    record = next(record for record in caplog.records if record.name == "learning.tasks")
    assert record.exc_info is not None
    assert record.exc_info[2].tb_frame.f_code.co_name == "_execute_in_process"


@pytest.mark.django_db
def test_failed_pending_revoke_is_visible_and_retryable_without_reviving_the_run(api_client):
    """Only a queued delivery needs broker revoke; its failure remains retryable."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        status=Run.Status.PENDING, task_id="pending-revoke-task",
    )
    assert hasattr(run, "cancel_revoke_pending"), "Run must persist a cancellation-delivery flag"
    with patch.object(current_app.control, "revoke", side_effect=RuntimeError("redis://secret@broker")):
        failed = api_client.post(f"/api/runs/{run.id}/cancel/", {}, format="json")

    run.refresh_from_db()
    assert failed.status_code == 503
    assert failed.json()["status"] == Run.Status.CANCELLED
    assert "secret" not in failed.content.decode()
    assert run.status == Run.Status.CANCELLED and run.cancel_revoke_pending is True

    with patch.object(current_app.control, "revoke") as revoke:
        retried = api_client.post(f"/api/runs/{run.id}/cancel/", {}, format="json")
    run.refresh_from_db()
    assert retried.status_code == 200 and retried.json()["status"] == Run.Status.CANCELLED
    assert run.cancel_revoke_pending is False
    revoke.assert_called_once_with(run.task_id, terminate=False)


@pytest.mark.django_db(transaction=True)
@override_settings(RUN_LEASE_SECONDS=60, RUN_HEARTBEAT_SECONDS=0.01)
def test_running_worker_renews_its_lease_while_algorithm_is_active(monkeypatch):
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="heartbeat-task",
    )
    assert hasattr(run, "lease_expires_at"), "Run must persist a renewable worker lease"
    observed: list[bool] = []

    def wait_for_heartbeat(*args, **kwargs):
        initial = Run.objects.get(pk=run.id).lease_expires_at
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            current = Run.objects.get(pk=run.id)
            if current.lease_expires_at and initial and current.lease_expires_at > initial:
                observed.append(True)
                break
            time.sleep(0.02)
        return {"tables": [{"key": "heartbeat"}]}

    monkeypatch.setattr(tasks, "execute_algorithm", wait_for_heartbeat)
    assert tasks.execute_run_job(str(run.id)) == Run.Status.COMPLETED
    assert observed == [True]


@pytest.mark.django_db
@override_settings(RUN_LEASE_SECONDS=1, RUN_HEARTBEAT_SECONDS=3600)
def test_cleanup_lease_failure_wins_against_late_worker_completion(monkeypatch):
    """A worker returning after its expired lease was reclaimed must discard the late result."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="late-worker-task",
    )
    assert hasattr(run, "lease_expires_at"), "Run must persist a renewable worker lease"

    def expire_then_finish(*args, **kwargs):
        Run.objects.filter(pk=run.id).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
        tasks.cleanup_expired_runs()
        return {"tables": [{"key": "late-result"}]}

    monkeypatch.setattr(tasks, "execute_algorithm", expire_then_finish)
    assert tasks.execute_run_job(str(run.id)) == Run.Status.FAILED
    run.refresh_from_db()
    assert run.status == Run.Status.FAILED
    assert run.error["code"] == "worker_lease_expired"
    assert run.result == {}


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, PENDING_DELIVERY_SECONDS=30)
def test_cleanup_requeues_one_stale_pending_delivery_and_duplicate_delivery_is_claim_guarded(monkeypatch):
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="stale-pending-task",
    )
    assert hasattr(run, "queued_at") and hasattr(run, "requeue_count"), "Pending delivery recovery needs claim metadata"
    Run.objects.filter(pk=run.id).update(queued_at=timezone.now() - timedelta(seconds=31))
    with patch.object(tasks.execute_run_job, "apply_async") as enqueue:
        tasks.cleanup_expired_runs()
        tasks.cleanup_expired_runs()

    run.refresh_from_db()
    assert run.status == Run.Status.PENDING and run.requeue_count == 1
    enqueue.assert_called_once_with(args=[str(run.id)], task_id=run.task_id, queue="default")

    with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
        with patch.object(tasks, "execute_algorithm", return_value={"tables": [{"key": "once"}]}) as algorithm:
            assert tasks.execute_run_job(str(run.id)) == Run.Status.COMPLETED
            assert tasks.execute_run_job(str(run.id)) == Run.Status.COMPLETED
    algorithm.assert_called_once()


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, PENDING_DELIVERY_SECONDS=30, MAX_PENDING_REQUEUES=3)
def test_healthy_pending_backlog_is_never_age_forced_to_failed_after_many_intervals():
    """A healthy queue can wait over eight minutes without becoming a false terminal failure."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="healthy-backlog-task", requeue_count=99,
    )
    Run.objects.filter(pk=run.id).update(queued_at=timezone.now() - timedelta(minutes=9))

    with patch.object(tasks.execute_run_job, "apply_async") as enqueue:
        tasks.cleanup_expired_runs()

    run.refresh_from_db()
    assert run.status == Run.Status.PENDING
    assert run.finished_at is None and run.error == {}
    assert run.requeue_count == 100
    enqueue.assert_called_once_with(args=[str(run.id)], task_id=run.task_id, queue="default")


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, PENDING_DELIVERY_SECONDS=30)
def test_lost_pending_delivery_retries_after_broker_error_without_false_terminal_state(caplog):
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="lost-delivery-task",
    )
    Run.objects.filter(pk=run.id).update(queued_at=timezone.now() - timedelta(seconds=31))
    with caplog.at_level("ERROR"):
        with patch.object(tasks.execute_run_job, "apply_async", side_effect=RuntimeError("redis://secret@broker")):
            tasks.cleanup_expired_runs()

    run.refresh_from_db()
    assert run.status == Run.Status.PENDING and run.requeue_count == 1
    assert run.finished_at is None and run.error == {}
    assert "secret" not in caplog.text

    Run.objects.filter(pk=run.id).update(queued_at=timezone.now() - timedelta(seconds=31))
    with patch.object(tasks.execute_run_job, "apply_async") as recovered:
        tasks.cleanup_expired_runs()
    run.refresh_from_db()
    assert run.status == Run.Status.PENDING and run.requeue_count == 2
    recovered.assert_called_once()


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, PENDING_DELIVERY_SECONDS=30)
def test_expired_pending_run_is_deleted_without_reenqueue():
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="expired-pending-task", expires_at=timezone.now() - timedelta(seconds=1),
    )
    Run.objects.filter(pk=run.id).update(queued_at=timezone.now() - timedelta(seconds=31))

    with patch.object(tasks.execute_run_job, "apply_async") as enqueue:
        tasks.cleanup_expired_runs()

    assert not Run.objects.filter(pk=run.id).exists()
    enqueue.assert_not_called()


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, RUN_MONITOR_SECONDS=0, RUN_HEARTBEAT_SECONDS=30)
def test_running_cancel_terminates_only_isolated_child_and_discards_late_output(api_client, monkeypatch):
    """The reusable Celery worker must survive while its one calculation child is stopped."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={
            "alpha": 0.85, "max_iterations": 200, "tolerance": 1e-6,
        }, seed=7, task_id="isolated-child-task",
    )
    observed = {"started": False, "terminated": False, "killed": False}

    class Child:
        returncode = None

        def poll(self):
            if not observed["started"]:
                observed["started"] = True
                response = api_client.post(f"/api/runs/{run.id}/cancel/", {}, format="json")
                assert response.status_code == 200
            return self.returncode

        def terminate(self):
            observed["terminated"] = True
            self.returncode = -15

        def wait(self, timeout=None):
            return self.returncode

        def kill(self):
            observed["killed"] = True
            self.returncode = -9

    def start_child(current, request_path, result_path):
        result_path.write_text('{"ok":true,"result":{"tables":[{"key":"late"}]}}', encoding="utf-8")
        return Child()

    monkeypatch.setattr(tasks, "start_algorithm_subprocess", start_child, raising=False)
    with patch.object(current_app.control, "revoke") as revoke:
        state = tasks.execute_run_job(str(run.id))

    run.refresh_from_db()
    assert state == Run.Status.CANCELLED
    assert run.status == Run.Status.CANCELLED and run.result == {}
    assert observed == {"started": True, "terminated": True, "killed": False}
    revoke.assert_not_called()


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_cancelled_pending_delivery_never_launches_an_algorithm_child(api_client, monkeypatch):
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={
            "alpha": 0.85, "max_iterations": 200, "tolerance": 1e-6,
        }, seed=7, task_id="cancelled-before-claim",
    )
    with patch.object(current_app.control, "revoke"):
        response = api_client.post(f"/api/runs/{run.id}/cancel/", {}, format="json")
    assert response.status_code == 200

    def forbidden_start(*_args, **_kwargs):
        raise AssertionError("a cancelled pending job must never create its isolated child")

    monkeypatch.setattr(tasks, "start_algorithm_subprocess", forbidden_start, raising=False)
    assert tasks.execute_run_job(str(run.id)) == Run.Status.CANCELLED


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, RUN_MONITOR_SECONDS=0.01)
def test_production_worker_computes_real_result_outside_the_reusable_celery_process(monkeypatch):
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={
            "alpha": 0.85, "max_iterations": 200, "tolerance": 1e-6,
        }, seed=7, task_id="real-isolated-task",
    )

    def forbidden_in_worker(*_args, **_kwargs):
        raise AssertionError("the reusable Celery process must not execute the algorithm body")

    monkeypatch.setattr(tasks, "execute_algorithm", forbidden_in_worker)
    assert tasks.execute_run_job(str(run.id)) == Run.Status.COMPLETED
    run.refresh_from_db()
    assert run.result["tables"]


def test_isolated_runner_logs_real_sanitized_trace_with_run_identifiers(tmp_path, monkeypatch, caplog):
    request_path = tmp_path / "request.json"
    result_path = tmp_path / "result.json"
    request_path.write_text(json.dumps({
        "run_id": "run-safe-id", "task_id": "task-safe-id", "algorithm": "centrality.pagerank",
        "graph": {"private": "GRAPH-CONTENT-SECRET"}, "parameters": {}, "seed": 7,
    }), encoding="utf-8")
    monkeypatch.setattr(
        job_runner, "execute_algorithm",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("GRAPH-CONTENT-SECRET")),
    )

    with caplog.at_level("ERROR"):
        assert job_runner.main(str(request_path), str(result_path)) == 0

    record = next(record for record in caplog.records if record.name == "learning.job_runner")
    assert "run-safe-id" in caplog.text and "task-safe-id" in caplog.text and "centrality.pagerank" in caplog.text
    assert "GRAPH-CONTENT-SECRET" not in caplog.text
    assert record.exc_info is not None
    assert record.exc_info[2].tb_frame.f_code.co_name == "main"


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, RUN_MONITOR_SECONDS=0)
def test_two_hour_expiry_cleanup_stops_an_isolated_child_without_resurrecting_the_row(monkeypatch):
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="expiry-child-task",
    )
    observed = {"polled": False, "terminated": False}

    class Child:
        returncode = None

        def poll(self):
            if not observed["polled"]:
                observed["polled"] = True
                Run.objects.filter(pk=run.id).update(expires_at=timezone.now() - timedelta(seconds=1))
                tasks.cleanup_expired_runs()
            return self.returncode

        def terminate(self):
            observed["terminated"] = True
            self.returncode = -15

        def wait(self, timeout=None):
            return self.returncode

        def kill(self):
            raise AssertionError("the cooperative isolated child should stop during its grace period")

    monkeypatch.setattr(tasks, "start_algorithm_subprocess", lambda *_args: Child())

    assert tasks.execute_run_job(str(run.id)) == "expired"
    assert observed == {"polled": True, "terminated": True}
    assert not Run.objects.filter(pk=run.id).exists()


def test_isolated_child_environment_is_a_runtime_allowlist_not_a_secret_denylist(monkeypatch):
    monkeypatch.setenv("PATH", "safe-runtime-path")
    monkeypatch.setenv("EXTERNAL_API_KEY", "must-not-cross-boundary")
    monkeypatch.setenv("UNFAMILIAR_CREDENTIAL", "must-not-cross-boundary")
    monkeypatch.setenv("OMP_NUM_THREADS", "2")

    child_environment = tasks._runner_environment()

    assert child_environment["PATH"] == "safe-runtime-path"
    assert child_environment["OMP_NUM_THREADS"] == "2"
    assert "EXTERNAL_API_KEY" not in child_environment
    assert "UNFAMILIAR_CREDENTIAL" not in child_environment


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, RUN_MONITOR_SECONDS=0)
def test_monitor_failure_still_terminates_and_reaps_the_isolated_child(monkeypatch):
    """Removing unconditional cleanup would leave the live calculation child orphaned."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="monitor-failure-child",
    )

    class Child:
        alive = True
        reaped = False
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            self.alive = False
            self.returncode = -15

        def wait(self, timeout=None):
            self.reaped = True
            return self.returncode

        def kill(self):
            self.alive = False
            self.returncode = -9

    child = Child()
    monkeypatch.setattr(tasks, "start_algorithm_subprocess", lambda *_args: child)
    monkeypatch.setattr(tasks, "_current_status", lambda *_args: (_ for _ in ()).throw(RuntimeError("db down")))

    assert tasks.execute_run_job(str(run.id)) == Run.Status.FAILED
    assert child.alive is False
    assert child.reaped is True


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, RUN_MONITOR_SECONDS=0)
def test_malformed_child_result_reaps_an_already_exited_process(monkeypatch):
    """A child that exits before envelope validation must still be explicitly joined."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="malformed-envelope-child",
    )

    class Child:
        returncode = 0
        reaped = False

        def poll(self):
            return self.returncode

        def terminate(self):
            raise AssertionError("an exited child must not be terminated")

        def wait(self, timeout=None):
            self.reaped = True
            return self.returncode

        def kill(self):
            raise AssertionError("an exited child must not be killed")

    child = Child()

    def start_child(_run, _request_path, result_path):
        result_path.write_text('{"ok":true,"result":[]}', encoding="utf-8")
        return child

    monkeypatch.setattr(tasks, "start_algorithm_subprocess", start_child)

    assert tasks.execute_run_job(str(run.id)) == Run.Status.FAILED
    assert child.reaped is True


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, RUN_MONITOR_SECONDS=0)
def test_cleanup_failure_is_sanitized_and_falls_back_to_kill_and_reap(monkeypatch, caplog):
    """A terminate exception must neither leak its content nor prevent final kill/join cleanup."""
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="terminate-failure-child",
    )

    class Child:
        alive = True
        killed = False
        reaped = False
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            raise RuntimeError("GRAPH-CONTENT-SECRET")

        def wait(self, timeout=None):
            if self.alive:
                raise tasks.subprocess.TimeoutExpired("isolated-child", timeout)
            self.reaped = True
            return self.returncode

        def kill(self):
            self.killed = True
            self.alive = False
            self.returncode = -9

    child = Child()
    monkeypatch.setattr(tasks, "start_algorithm_subprocess", lambda *_args: child)
    monkeypatch.setattr(tasks, "_current_status", lambda *_args: (_ for _ in ()).throw(RuntimeError("db down")))

    with caplog.at_level("ERROR"):
        assert tasks.execute_run_job(str(run.id)) == Run.Status.FAILED

    assert child.killed is True and child.reaped is True and child.alive is False
    assert "Isolated child cleanup failed" in caplog.text
    assert "terminate-failure-child" in caplog.text
    assert "GRAPH-CONTENT-SECRET" not in caplog.text


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, RUN_MONITOR_SECONDS=0)
def test_result_read_failure_reaps_the_exited_child(monkeypatch):
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="result-read-failure-child",
    )

    class Child:
        returncode = 0
        reaped = False

        def poll(self):
            return self.returncode

        def terminate(self):
            raise AssertionError("an exited child must not be terminated")

        def wait(self, timeout=None):
            self.reaped = True
            return self.returncode

        def kill(self):
            raise AssertionError("an exited child must not be killed")

    child = Child()

    def start_child(_run, _request_path, result_path):
        result_path.write_text('{"ok":true,"result":{"tables":[]}}', encoding="utf-8")
        return child

    monkeypatch.setattr(tasks, "start_algorithm_subprocess", start_child)
    monkeypatch.setattr(tasks.Path, "read_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("read failed")))

    assert tasks.execute_run_job(str(run.id)) == Run.Status.FAILED
    assert child.reaped is True


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=False, RUN_MONITOR_SECONDS=0)
def test_tempdir_cleanup_failure_happens_after_child_reap_and_does_not_overwrite_completion(
    monkeypatch, tmp_path,
):
    run = Run.objects.create(
        algorithm="centrality.pagerank", graph=PATH3, parameters={}, resolved_parameters={}, seed=7,
        task_id="tempdir-failure-child",
    )

    class ExplodingTemporaryDirectory:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return str(tmp_path)

        def __exit__(self, *_args):
            raise OSError("tempdir cleanup failed")

    class Child:
        returncode = 0
        reaped = False

        def poll(self):
            return self.returncode

        def terminate(self):
            raise AssertionError("an exited child must not be terminated")

        def wait(self, timeout=None):
            self.reaped = True
            return self.returncode

        def kill(self):
            raise AssertionError("an exited child must not be killed")

    child = Child()

    def start_child(_run, _request_path, result_path):
        result_path.write_text(
            '{"ok":true,"result":{"tables":[{"key":"completed-before-cleanup"}]}}',
            encoding="utf-8",
        )
        return child

    monkeypatch.setattr(tasks.tempfile, "TemporaryDirectory", ExplodingTemporaryDirectory)
    monkeypatch.setattr(tasks, "start_algorithm_subprocess", start_child)

    assert tasks.execute_run_job(str(run.id)) == Run.Status.COMPLETED
    run.refresh_from_db()
    assert child.reaped is True
    assert run.status == Run.Status.COMPLETED
    assert run.result["tables"][0]["key"] == "completed-before-cleanup"

from django.urls import path

from .views import (
    AlgorithmListView, CaseDetailView, CaseListView, GraphValidationView, ModuleDetailView,
    ModuleListView, ReportView, RunListView, RunResultView, RunStatusView,
)

urlpatterns = [
    path("modules/", ModuleListView.as_view()),
    path("modules/<slug:slug>/", ModuleDetailView.as_view()),
    path("cases/", CaseListView.as_view()),
    path("cases/<slug:slug>/", CaseDetailView.as_view()),
    path("graphs/validate/", GraphValidationView.as_view()),
    path("algorithms/", AlgorithmListView.as_view()),
    path("runs/", RunListView.as_view()),
    path("runs/<uuid:run_id>/", RunStatusView.as_view()),
    path("runs/<uuid:run_id>/result/", RunResultView.as_view()),
    path("reports/", ReportView.as_view()),
]

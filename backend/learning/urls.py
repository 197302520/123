from django.urls import path

from .views import (
    AlgorithmListView, CaseDetailView, CaseListView, GraphImportView, GraphValidationView, ModuleDetailView,
    ModuleListView, ReportBundleView, ReportView, RunListView, RunResultView, RunStatusView,
)
from .teacher_views import TeacherCaseDetailView, TeacherCaseListView, TeacherSessionView

urlpatterns = [
    path("modules/", ModuleListView.as_view()),
    path("modules/<slug:slug>/", ModuleDetailView.as_view()),
    path("cases/", CaseListView.as_view()),
    path("cases/<slug:slug>/", CaseDetailView.as_view()),
    path("graphs/validate/", GraphValidationView.as_view()),
    path("graphs/import/", GraphImportView.as_view()),
    path("algorithms/", AlgorithmListView.as_view()),
    path("runs/", RunListView.as_view()),
    path("runs/<uuid:run_id>/", RunStatusView.as_view()),
    path("runs/<uuid:run_id>/result/", RunResultView.as_view()),
    path("reports/", ReportView.as_view()),
    path("reports/<uuid:run_id>/bundle/", ReportBundleView.as_view()),
    path("teacher/session/", TeacherSessionView.as_view()),
    path("teacher/cases/", TeacherCaseListView.as_view()),
    path("teacher/cases/<slug:slug>/", TeacherCaseDetailView.as_view()),
]

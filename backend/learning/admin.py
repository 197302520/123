from django.contrib import admin

from .models import Case, CourseModule, Dataset


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "status")
    list_filter = ("status",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status")
    list_filter = ("status",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "dataset", "status")
    list_filter = ("status", "module")
    prepopulated_fields = {"slug": ("title",)}

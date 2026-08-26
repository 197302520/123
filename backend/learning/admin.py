from django.contrib import admin
from django.db import transaction

from .middleware import client_ip
from .models import AuditRecord, Case, CourseModule, Dataset


class AuditedContentAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            AuditRecord.objects.create(
                actor=request.user,
                action="update" if change else "create",
                entity_type=obj._meta.model_name,
                entity_id=str(getattr(obj, "slug", obj.pk)),
                changes={"changed_fields": sorted(form.changed_data), "status": getattr(obj, "status", None)},
                source_ip=client_ip(request),
            )

    def delete_model(self, request, obj):
        with transaction.atomic():
            AuditRecord.objects.create(
                actor=request.user, action="delete", entity_type=obj._meta.model_name,
                entity_id=str(getattr(obj, "slug", obj.pk)), changes={},
                source_ip=client_ip(request),
            )
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            AuditRecord.objects.bulk_create([
                AuditRecord(
                    actor=request.user,
                    action="delete",
                    entity_type=obj._meta.model_name,
                    entity_id=str(getattr(obj, "slug", obj.pk)),
                    changes={},
                    source_ip=client_ip(request),
                )
                for obj in queryset
            ])
            super().delete_queryset(request, queryset)


@admin.register(CourseModule)
class CourseModuleAdmin(AuditedContentAdmin):
    list_display = ("order", "title", "status")
    list_filter = ("status",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Dataset)
class DatasetAdmin(AuditedContentAdmin):
    list_display = ("title", "slug", "status")
    list_filter = ("status",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Case)
class CaseAdmin(AuditedContentAdmin):
    list_display = ("title", "module", "dataset", "status")
    list_filter = ("status", "module")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(AuditRecord)
class AuditRecordAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "entity_type", "entity_id", "source_ip")
    list_filter = ("action", "entity_type")
    readonly_fields = ("actor", "action", "entity_type", "entity_id", "changes", "source_ip", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

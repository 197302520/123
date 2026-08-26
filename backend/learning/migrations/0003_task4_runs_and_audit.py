import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("learning", "0002_run_expires_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="run",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "等待中"), ("running", "运行中"), ("completed", "已完成"),
                    ("failed", "失败"), ("cancelled", "已取消"),
                ],
                default="pending", max_length=16,
            ),
        ),
        migrations.AddField(model_name="run", name="algorithm_version", field=models.CharField(default="1.0", max_length=32)),
        migrations.AddField(model_name="run", name="cache_key", field=models.CharField(blank=True, db_index=True, max_length=64)),
        migrations.AddField(model_name="run", name="error", field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name="run", name="finished_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="run", name="resolved_parameters", field=models.JSONField(default=dict)),
        migrations.AddField(model_name="run", name="started_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(
            model_name="run", name="cached_from",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="cache_hits", to="learning.run"),
        ),
        migrations.CreateModel(
            name="AuditRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=32)),
                ("entity_type", models.CharField(max_length=64)),
                ("entity_id", models.CharField(max_length=160)),
                ("changes", models.JSONField(blank=True, default=dict)),
                ("source_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
    ]

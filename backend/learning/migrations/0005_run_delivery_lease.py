from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("learning", "0004_task4_review_hardening")]

    operations = [
        migrations.AddField(
            model_name="run", name="queued_at",
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="run", name="lease_expires_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="run", name="requeue_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="run", name="cancel_revoke_pending",
            field=models.BooleanField(default=False),
        ),
    ]

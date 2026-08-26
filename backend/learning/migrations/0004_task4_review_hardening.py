from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0003_task4_runs_and_audit")]

    operations = [
        migrations.AddField(
            model_name="run",
            name="task_id",
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
    ]

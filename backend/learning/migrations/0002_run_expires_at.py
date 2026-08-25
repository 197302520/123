import learning.models

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="run",
            name="expires_at",
            field=models.DateTimeField(db_index=True, default=learning.models.run_expiry_default),
        ),
    ]

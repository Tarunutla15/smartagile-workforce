import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("smartagile", "0013_copy_signupdata_to_accounts_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="authsessionevent",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="auth_events",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="usageevent",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="usage_events",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

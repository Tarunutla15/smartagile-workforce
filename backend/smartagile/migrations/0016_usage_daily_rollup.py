import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("smartagile", "0015_delete_signupdata"),
    ]

    operations = [
        migrations.CreateModel(
            name="UsageDailyRollup",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("day", models.DateField()),
                ("total_duration_seconds", models.FloatField(default=0)),
                ("work_duration_seconds", models.FloatField(default=0)),
                ("event_count", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usage_rollups",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-day", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="usagedailyrollup",
            constraint=models.UniqueConstraint(
                fields=("user", "day"),
                name="usage_rollup_user_day_uniq",
            ),
        ),
    ]

# Generated manually for UsageEvent single-table usage storage.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("smartagile", "0011_auto_20260330_1855"),
    ]

    operations = [
        migrations.CreateModel(
            name="UsageEvent",
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
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("application", "Application"),
                            ("browser", "Browser"),
                        ],
                        max_length=16,
                    ),
                ),
                ("name", models.CharField(max_length=512)),
                ("context", models.CharField(blank=True, default="", max_length=1024)),
                ("category", models.CharField(blank=True, default="", max_length=128)),
                ("duration_seconds", models.FloatField()),
                ("idle_seconds", models.FloatField(default=0)),
                ("keystrokes", models.FloatField(default=0)),
                ("clicks", models.FloatField(default=0)),
                ("scrolls", models.FloatField(default=0)),
                ("occurred_at", models.DateTimeField()),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usage_events",
                        to="smartagile.signupdata",
                    ),
                ),
            ],
            options={
                "ordering": ["-occurred_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="usageevent",
            index=models.Index(
                fields=["user", "-occurred_at"],
                name="usage_user_occurred_desc",
            ),
        ),
        migrations.AddIndex(
            model_name="usageevent",
            index=models.Index(
                fields=["user", "occurred_at"],
                name="usage_user_occurred_asc",
            ),
        ),
    ]

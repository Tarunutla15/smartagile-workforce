# Generated manually for AuthSessionEvent

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smartagile", "0009_delete_task"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuthSessionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event", models.CharField(choices=[("login", "Login"), ("logout", "Logout")], max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auth_events",
                        to="smartagile.signupdata",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="authsessionevent",
            index=models.Index(fields=["user", "created_at"], name="smartagile_authevent_user_created"),
        ),
    ]

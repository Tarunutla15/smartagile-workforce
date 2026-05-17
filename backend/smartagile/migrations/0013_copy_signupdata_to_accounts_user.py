from django.db import connection, migrations


def copy_signup_to_user(apps, schema_editor):
    SignupData = apps.get_model("smartagile", "SignupData")
    User = apps.get_model("accounts", "User")
    for s in SignupData.objects.all():
        if User.objects.filter(pk=s.pk).exists():
            continue
        is_admin = getattr(s, "role", "") == "admin"
        User.objects.create(
            id=s.pk,
            username=s.username,
            email=s.email,
            password=s.password,
            role=getattr(s, "role", "employee") or "employee",
            profile_photo=s.profile_photo,
            is_active=True,
            is_staff=is_admin,
            is_superuser=is_admin,
            first_name="",
            last_name="",
            date_joined=s.created_at,
        )
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT setval(
                    pg_get_serial_sequence('accounts_user', 'id'),
                    COALESCE((SELECT MAX(id) FROM accounts_user), 1),
                    true
                )
                """
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("smartagile", "0012_usageevent"),
    ]

    operations = [
        migrations.RunPython(copy_signup_to_user, noop_reverse),
    ]

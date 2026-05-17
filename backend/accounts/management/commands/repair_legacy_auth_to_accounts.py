"""
Fix InconsistentMigrationHistory when the DB was built with stock auth.User + authtoken
but the project uses AUTH_USER_MODEL=accounts.User.

Typical state:
  - auth_user, authtoken_token exist; authtoken.* is applied in django_migrations
  - accounts_user is missing; accounts.0001_initial is not applied

This command:
  1. Unregisters authtoken migrations and drops authtoken_token
  2. Creates accounts_user (and m2m tables) per accounts.0001_initial
  3. Copies users from auth_user and copies group/permission m2m rows
  4. Records accounts.0001_initial in django_migrations

Then run: python manage.py migrate

From backend/ with venv active:
    python manage.py repair_legacy_auth_to_accounts
    python manage.py migrate
"""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone


def _get_sql_for_accounts_0001():
    buf = StringIO()
    call_command("sqlmigrate", "accounts", "0001", stdout=buf, no_color=True)
    sql = buf.getvalue()
    # Strip transaction wrappers; we run in our own transaction
    lines = []
    for line in sql.splitlines():
        s = line.strip().upper()
        if s in ("BEGIN;", "COMMIT;"):
            continue
        lines.append(line)
    return "\n".join(lines)


def _run_sql_statements(sql):
    """Run semicolon-separated DDL (one statement per execute for psycopg2)."""
    for raw in sql.split(";"):
        lines = [
            ln
            for ln in raw.splitlines()
            if ln.strip() and not ln.strip().startswith("--")
        ]
        chunk = "\n".join(lines).strip()
        if not chunk:
            continue
        with connection.cursor() as c:
            c.execute(chunk)


class Command(BaseCommand):
    help = "Repair DB after switching to accounts.User: legacy auth+authtoken in django_migrations without accounts app."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be done, do not modify the database",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        with connection.cursor() as c:
            c.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                ["public", "accounts_user"],
            )
            has_accounts = c.fetchone() is not None
            c.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                ["public", "auth_user"],
            )
            has_auth = c.fetchone() is not None
            c.execute(
                "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s",
                ["accounts", "0001_initial"],
            )
            has_mig = c.fetchone() is not None

        if has_accounts and has_mig:
            self.stdout.write(
                self.style.SUCCESS(
                    "accounts_user and accounts.0001_initial already present. "
                    "If you still see migration errors, run: python manage.py migrate"
                )
            )
            return

        if not has_auth:
            self.stdout.write(
                self.style.ERROR(
                    "No auth_user table: this repair is for legacy stock-auth databases only."
                )
            )
            return

        if has_accounts and not has_mig:
            self.stdout.write("Recording missing accounts.0001_initial in django_migrations")
            if not dry:
                with connection.cursor() as c:
                    c.execute(
                        "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                        ["accounts", "0001_initial", timezone.now()],
                    )
            self.stdout.write(
                self.style.SUCCESS("Done. Run: python manage.py migrate")
            )
            return

        # Build accounts from auth + resync authtoken
        sql_body = _get_sql_for_accounts_0001()
        if dry:
            self.stdout.write(self.style.WARNING("DRY RUN\n"))
            self.stdout.write("Would: unregister authtoken, drop authtoken_token, create accounts tables, copy users")
            self.stdout.write(sql_body[:500] + "...\n")
            return

        with transaction.atomic():
            with connection.cursor() as c:
                c.execute("DELETE FROM django_migrations WHERE app = 'authtoken'")
                c.execute("DROP TABLE IF EXISTS authtoken_token CASCADE")

            # Create accounts.* tables
            _run_sql_statements(sql_body)

            with connection.cursor() as c:
                c.execute(
                    """
                    INSERT INTO accounts_user (
                        id, password, last_login, is_superuser, username, first_name, last_name,
                        email, is_staff, is_active, date_joined, role, profile_photo
                    )
                    SELECT
                        u.id, u.password, u.last_login, u.is_superuser, u.username,
                        u.first_name, u.last_name, u.email, u.is_staff, u.is_active, u.date_joined,
                        'employee', NULL
                    FROM auth_user u
                    WHERE NOT EXISTS (SELECT 1 FROM accounts_user au WHERE au.id = u.id)
                    """
                )

            # M2M: copy if legacy tables exist
            with connection.cursor() as c:
                c.execute(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'auth_user_groups'
                    """
                )
                if c.fetchone():
                    c.execute(
                        """
                        INSERT INTO accounts_user_groups (user_id, group_id)
                        SELECT g.user_id, g.group_id FROM auth_user_groups g
                        WHERE NOT EXISTS (
                            SELECT 1 FROM accounts_user_groups a
                            WHERE a.user_id = g.user_id AND a.group_id = g.group_id
                        )
                        """
                    )
                c.execute(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'auth_user_user_permissions'
                    """
                )
                if c.fetchone():
                    c.execute(
                        """
                        INSERT INTO accounts_user_user_permissions (user_id, permission_id)
                        SELECT p.user_id, p.permission_id FROM auth_user_user_permissions p
                        WHERE NOT EXISTS (
                            SELECT 1 FROM accounts_user_user_permissions a
                            WHERE a.user_id = p.user_id AND a.permission_id = p.permission_id
                        )
                        """
                    )

            with connection.cursor() as c:
                c.execute(
                    "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s",
                    ["accounts", "0001_initial"],
                )
                if c.fetchone() is None:
                    c.execute(
                        "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                        ["accounts", "0001_initial", timezone.now()],
                    )
                if connection.vendor == "postgresql":
                    c.execute(
                        """
                        SELECT setval(
                            pg_get_serial_sequence('accounts_user', 'id'),
                            COALESCE((SELECT MAX(id) FROM accounts_user), 1),
                            true
                        )
                        """
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Repair complete. Next: python manage.py migrate  "
                "(authtoken and remaining apps will apply; login uses accounts_user)."
            )
        )

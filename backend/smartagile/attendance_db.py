"""
Helpers for per-user attendance tables (PostgreSQL).
Per-user PostgreSQL table: attendence_{user_id} (legacy schema; desktop agent no longer writes here).
"""
from django.db import connection
from django.utils import timezone


def _table_suffix(user_id: int) -> str:
    return f"_{int(user_id)}"


def ensure_attendance_table(cursor, user_id: int) -> None:
    """Create attendence table if missing (legacy per-user schema)."""
    suffix = _table_suffix(user_id)
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS attendence{suffix} (
            ID SERIAL PRIMARY KEY,
            login TIMESTAMP,
            date DATE,
            logout TIMESTAMP,
            duration REAL,
            UNIQUE (date)
        )
        """
    )


def record_login_attendance(user_id: int) -> None:
    """
    On successful API login: ensure today's row exists with login timestamp.
    First login of the day wins; later logins same day keep the earliest login.
    """
    uid = int(user_id)
    suffix = _table_suffix(uid)
    # Align with tracker (local wall clock on the app server)
    login_ts = timezone.localtime(timezone.now())
    work_date = login_ts.date()

    with connection.cursor() as cursor:
        ensure_attendance_table(cursor, uid)
        cursor.execute(
            f"""
            INSERT INTO attendence{suffix} (login, date, logout, duration)
            VALUES (%s, %s, NULL, 0)
            ON CONFLICT (date) DO UPDATE SET
                login = COALESCE(attendence{suffix}.login, EXCLUDED.login)
            """,
            [login_ts, work_date],
        )


def finalize_logout_attendance(user_id: int) -> None:
    """
    On API logout: set today's logout time and wall-clock duration since login
    (replaces the old in-process tracker DB update).
    """
    uid = int(user_id)
    suffix = _table_suffix(uid)
    now_ts = timezone.localtime(timezone.now())
    work_date = now_ts.date()

    with connection.cursor() as cursor:
        ensure_attendance_table(cursor, uid)
        cursor.execute(
            f"""
            UPDATE attendence{suffix}
            SET logout = %s,
                duration = CASE WHEN login IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (%s::timestamp - login))
                    ELSE COALESCE(duration, 0) END
            WHERE date = %s
            """,
            [now_ts, now_ts, work_date],
        )

"""Tier 1 reliability tests: health probe, idempotent ingest, agent heartbeat status.

Tier 2C: proactive nudge scans + notifications API.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from .models import AgentStatus, Notification, UsageEvent

User = get_user_model()


def _event(client_event_id="", **over):
    e = {
        "source_type": "application",
        "name": "Cursor",
        "context": "engine.py",
        "category": "work",
        "duration_seconds": 30.0,
        "idle_seconds": 0.0,
        "keystrokes": 10,
        "clicks": 2,
        "scrolls": 0,
        "occurred_at": "2026-06-30T09:00:00Z",
    }
    if client_event_id:
        e["client_event_id"] = client_event_id
    e.update(over)
    return e


class HealthEndpointTests(APITestCase):
    def test_health_ok_without_auth(self):
        # No credentials set — the readiness probe must still answer.
        resp = APIClient().get(reverse("health"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertEqual(resp.data["database"], "ok")
        self.assertIn("time", resp.data)


class IdempotentIngestTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="emp1", email="emp1@example.com", password="x"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("usage_events_batch")

    def test_duplicate_client_event_id_not_double_counted(self):
        payload = {"events": [_event(client_event_id="evt-abc-1")]}

        r1 = self.client.post(self.url, payload, format="json")
        self.assertEqual(r1.status_code, 202)

        # Same event id again (simulates an agent retry after an unclear failure).
        r2 = self.client.post(self.url, payload, format="json")
        self.assertEqual(r2.status_code, 202)

        self.assertEqual(
            UsageEvent.objects.filter(user=self.user, client_event_id="evt-abc-1").count(),
            1,
            "retried batch with the same client_event_id must not duplicate rows",
        )

    def test_distinct_ids_create_distinct_rows(self):
        payload = {"events": [_event(client_event_id="a"), _event(client_event_id="b")]}
        r = self.client.post(self.url, payload, format="json")
        self.assertEqual(r.status_code, 202)
        self.assertEqual(UsageEvent.objects.filter(user=self.user).count(), 2)

    def test_events_without_id_are_not_deduped(self):
        # Legacy/manual rows (no client_event_id) must never collide with each other.
        payload = {"events": [_event(), _event()]}
        r = self.client.post(self.url, payload, format="json")
        self.assertEqual(r.status_code, 202)
        self.assertEqual(UsageEvent.objects.filter(user=self.user).count(), 2)


class AgentStatusTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="emp2", email="emp2@example.com", password="x"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_status_disconnected_before_any_upload(self):
        resp = self.client.get(reverse("agent_status"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["connected"])
        self.assertIsNone(resp.data["last_seen_at"])

    def test_ingest_updates_heartbeat(self):
        self.client.post(
            reverse("usage_events_batch"),
            {"events": [_event(client_event_id="hb-1")]},
            format="json",
            HTTP_X_SMARTAGILE_AGENT_VERSION="1.2.3",
        )
        st = AgentStatus.objects.get(user=self.user)
        self.assertIsNotNone(st.last_seen_at)
        self.assertIsNotNone(st.last_event_at)
        self.assertEqual(st.agent_version, "1.2.3")

        resp = self.client.get(reverse("agent_status"))
        self.assertTrue(resp.data["connected"])
        self.assertEqual(resp.data["agent_version"], "1.2.3")


class NudgeScanTests(APITestCase):
    def setUp(self):
        from sprints.models import Sprint
        from tasks.models import Project, Task

        self.lead = User.objects.create_user(
            username="lead", email="lead@example.com", password="x"
        )
        self.dev = User.objects.create_user(
            username="dev", email="dev@example.com", password="x"
        )
        self.project = Project.objects.create(name="Apollo", lead=self.lead)
        self.today = timezone.localdate()
        self.sprint = Sprint.objects.create(
            project=self.project,
            name="S1",
            status=Sprint.Status.ACTIVE,
            start_date=self.today - timedelta(days=8),
            end_date=self.today + timedelta(days=1),  # ends tomorrow
        )
        # One open item assigned to the dev.
        Task.objects.create(
            title="Finish API",
            status="inProgress",
            user=self.dev,
            project=self.project,
            sprint=self.sprint,
        )

    def test_sprint_risk_notifies_lead(self):
        from .nudges import scan_sprint_risks

        created = scan_sprint_risks()
        self.assertGreaterEqual(created, 1)
        n = Notification.objects.filter(user=self.lead, kind="sprint_ending").first()
        self.assertIsNotNone(n)
        self.assertIn(f"project={self.project.pk}", n.link)
        self.assertIn(f"sprint={self.sprint.pk}", n.link)

    def test_sprint_risk_is_idempotent(self):
        from .nudges import scan_sprint_risks

        scan_sprint_risks()
        scan_sprint_risks()  # second run same day must not duplicate
        self.assertEqual(
            Notification.objects.filter(user=self.lead, kind="sprint_ending").count(), 1
        )

    def test_personal_nudge_notifies_assignee(self):
        from .nudges import scan_personal_nudges

        created = scan_personal_nudges()
        self.assertGreaterEqual(created, 1)
        self.assertTrue(
            Notification.objects.filter(user=self.dev, kind="my_items_due").exists()
        )


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@example.com", password="x"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        for i in range(3):
            Notification.objects.create(
                user=self.user,
                kind="test",
                title=f"N{i}",
                dedupe_key=f"test:{i}",
            )

    def test_list_and_unread_count(self):
        resp = self.client.get(reverse("notifications"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["unread"], 3)
        self.assertEqual(len(resp.data["results"]), 3)

    def test_mark_one_read(self):
        nid = Notification.objects.filter(user=self.user).first().pk
        resp = self.client.post(reverse("notification_read", args=[nid]))
        self.assertEqual(resp.data["unread"], 2)

    def test_mark_all_read(self):
        resp = self.client.post(reverse("notifications_read_all"))
        self.assertEqual(resp.data["unread"], 0)
        self.assertFalse(
            Notification.objects.filter(user=self.user, read_at__isnull=True).exists()
        )


class KnowledgeIndexTests(APITestCase):
    """Tier 2B: doc-RAG indexing + access-scoped retrieval (keyword fallback path)."""

    def setUp(self):
        from sprints.models import Sprint, WorkItemComment
        from tasks.models import Project, Task

        self.member = User.objects.create_user(
            username="kmember", email="kmember@example.com", password="x"
        )
        self.outsider = User.objects.create_user(
            username="koutsider", email="koutsider@example.com", password="x"
        )
        self.project = Project.objects.create(name="Phoenix", lead=self.member)
        self.sprint = Sprint.objects.create(
            project=self.project,
            name="S9",
            goal="Stabilize the authentication subsystem before launch.",
            status=Sprint.Status.ACTIVE,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=7),
        )
        self.task = Task.objects.create(
            title="Login session bug",
            description="Users get logged out randomly when the refresh token rotates.",
            status="inProgress",
            user=self.member,
            project=self.project,
            sprint=self.sprint,
        )
        self.comment = WorkItemComment.objects.create(
            task=self.task,
            author=self.member,
            body="Root cause is a clock skew between the auth service and the gateway.",
        )

    def test_reindex_creates_chunks_for_each_source(self):
        from assistant.knowledge import reindex_all
        from .models import KnowledgeChunk

        counts = reindex_all()
        self.assertEqual(counts["tasks"], 1)
        self.assertEqual(counts["comments"], 1)
        self.assertEqual(counts["sprints"], 1)

        types = set(
            KnowledgeChunk.objects.filter(project=self.project).values_list(
                "source_type", flat=True
            )
        )
        self.assertEqual(types, {"work_item", "comment", "sprint_goal"})

    def test_reindex_is_idempotent(self):
        from assistant.knowledge import index_task, reindex_all

        reindex_all()
        # Unchanged row -> no re-embed/rewrite work reported.
        self.assertFalse(index_task(self.task.pk))

    def test_retrieval_scoped_to_visible_projects(self):
        from assistant.knowledge import retrieve_knowledge, reindex_all

        reindex_all()
        hits = retrieve_knowledge(self.member, "clock skew auth gateway", limit=5)
        self.assertTrue(hits)
        self.assertTrue(any("clock skew" in h["snippet"] for h in hits))

        # An outsider who can't see the project gets nothing.
        self.assertEqual(
            retrieve_knowledge(self.outsider, "clock skew auth gateway", limit=5), []
        )

    def test_deleting_source_removes_chunk(self):
        from assistant.knowledge import index_task, reindex_all
        from .models import KnowledgeChunk

        reindex_all()
        self.assertTrue(
            KnowledgeChunk.objects.filter(source_type="work_item", source_id=self.task.pk).exists()
        )
        tid = self.task.pk
        self.task.delete()
        index_task(tid)
        self.assertFalse(
            KnowledgeChunk.objects.filter(source_type="work_item", source_id=tid).exists()
        )

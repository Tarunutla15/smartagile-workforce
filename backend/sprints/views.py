from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tasks.models import Project, Task
from tasks.serializers import UserMiniSerializer

from . import attribution, group_metrics, metrics, services
from .models import Sprint, SprintStatusChange, WorkItemComment
from .serializers import (
    SprintSerializer,
    StatusChangeSerializer,
    WorkItemCommentSerializer,
    WorkItemSerializer,
)

User = get_user_model()

# Fields an employee may edit on a task that is assigned to them. Project/sprint/assignee
# changes are planning/ownership actions reserved for managers and admins.
EMPLOYEE_EDITABLE_FIELDS = {"title", "description", "story_points", "priority", "item_type"}

STATUS_COLUMNS = [
    {"key": "todo", "label": "To Do"},
    {"key": "inProgress", "label": "In Progress"},
    {"key": "done", "label": "Done"},
]


def _sprint_queryset(user):
    return (
        Sprint.objects.filter(project_id__in=services.visible_project_ids(user))
        .select_related("project")
        .prefetch_related("items")
    )


def _get_sprint_or_404(user, pk):
    return get_object_or_404(_sprint_queryset(user), pk=pk)


class SprintListCreateView(APIView):
    """GET list (filter by ?project= & ?status=); POST create (lead/manager/admin)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _sprint_queryset(request.user)
        project_id = request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        sprint_status = request.query_params.get("status")
        if sprint_status:
            qs = qs.filter(status=sprint_status)
        return Response(SprintSerializer(qs, many=True).data)

    def post(self, request):
        ser = SprintSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        project = ser.validated_data["project"]
        if not services.can_manage_project(request.user, project):
            return Response(
                {"error": "Only the project lead, manager, or an admin can create sprints."},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        sprint = ser.save(created_by=request.user)
        return Response(
            SprintSerializer(sprint).data, status=http_status.HTTP_201_CREATED
        )


class SprintDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        sprint = _get_sprint_or_404(request.user, pk)
        return Response(SprintSerializer(sprint).data)

    def patch(self, request, pk):
        sprint = _get_sprint_or_404(request.user, pk)
        if not services.can_manage_project(request.user, sprint.project_id):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        ser = SprintSerializer(sprint, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(SprintSerializer(sprint).data)

    def delete(self, request, pk):
        sprint = _get_sprint_or_404(request.user, pk)
        if not services.can_manage_project(request.user, sprint.project_id):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        sprint.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)


class SprintStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sprint = _get_sprint_or_404(request.user, pk)
        if not services.can_manage_project(request.user, sprint.project_id):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        services.start_sprint(sprint, by=request.user)
        return Response(SprintSerializer(sprint).data)


class SprintCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sprint = _get_sprint_or_404(request.user, pk)
        if not services.can_manage_project(request.user, sprint.project_id):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        # Optional: ?move=backlog or ?move=<sprint_id> for unfinished items.
        move = request.data.get("move_incomplete_to")
        target = None
        if move == "backlog":
            target = "backlog"
        elif move:
            target = _get_sprint_or_404(request.user, move)
        services.complete_sprint(sprint, move_incomplete_to=target, by=request.user)
        return Response(SprintSerializer(sprint).data)


class SprintBoardView(APIView):
    """Scrum board: items grouped into status columns."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        sprint = _get_sprint_or_404(request.user, pk)
        items = (
            sprint.items.select_related("user", "project").order_by("rank", "-id")
        )
        by_status = {c["key"]: [] for c in STATUS_COLUMNS}
        for item in items:
            by_status.setdefault(item.status, []).append(item)
        columns = [
            {
                "key": col["key"],
                "label": col["label"],
                "items": WorkItemSerializer(by_status.get(col["key"], []), many=True).data,
            }
            for col in STATUS_COLUMNS
        ]
        return Response({"sprint": SprintSerializer(sprint).data, "columns": columns})


class SprintBurndownView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        sprint = _get_sprint_or_404(request.user, pk)
        return Response(metrics.burndown(sprint))


class SprintReportView(APIView):
    """Everything the overview dashboard needs in one call."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        sprint = _get_sprint_or_404(request.user, pk)
        return Response(
            {
                "summary": metrics.sprint_summary(sprint),
                "velocity": metrics.velocity_history(sprint.project_id),
                "burndown": metrics.burndown(sprint),
                "distribution": metrics.type_distribution(sprint),
            }
        )


class SprintEffortView(APIView):
    """Focus / office time invested in the sprint (from the desktop agent)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        sprint = _get_sprint_or_404(request.user, pk)
        return Response(metrics.sprint_effort(sprint))


class SprintItemEffortView(APIView):
    """Actual tracked focus time per work item in the sprint."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        sprint = _get_sprint_or_404(request.user, pk)
        return Response(metrics.sprint_item_effort(sprint))


def _timer_payload(session):
    if session is None:
        return {"active": False}
    return {
        "active": True,
        "session_id": session.id,
        "task_id": session.task_id,
        "task_title": session.task.title,
        "started_at": session.started_at.isoformat(),
        "elapsed_seconds": round(session.duration_seconds, 1),
    }


class TimerActiveView(APIView):
    """The current user's running focus timer, if any."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        session = attribution.active_session(request.user.pk)
        return Response(_timer_payload(session))


class TimerStartView(APIView):
    """Start (or switch) the focus timer to a task. Closes any prior open session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        task_id = request.data.get("task")
        if task_id in (None, ""):
            return Response({"error": "task is required."}, status=http_status.HTTP_400_BAD_REQUEST)
        task = get_object_or_404(Task.objects.select_related("project"), pk=task_id)
        if task.project_id and not services.can_view_project(request.user, task.project_id):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        session = attribution.start_session(request.user.pk, task.pk)
        session.task = task  # avoid re-query in payload
        return Response(_timer_payload(session))


class TimerStopView(APIView):
    """Stop the current user's running focus timer."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        session = attribution.stop_session(request.user.pk)
        if session is None:
            return Response({"active": False, "stopped": False})
        return Response({"active": False, "stopped": True, "session_id": session.id,
                         "task_id": session.task_id, "duration_seconds": round(session.duration_seconds, 1)})


class BacklogView(APIView):
    """Project backlog: items with no sprint, ranked."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project")
        if not project_id:
            return Response({"error": "project query param required."}, status=http_status.HTTP_400_BAD_REQUEST)
        if not services.can_view_project(request.user, int(project_id)):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        items = (
            Task.objects.filter(project_id=project_id, sprint__isnull=True)
            .select_related("user", "project")
            .order_by("rank", "-id")
        )
        return Response(WorkItemSerializer(items, many=True).data)


class OrgSummaryView(APIView):
    """Org-wide live summary for the admin Overview (admin role required)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, "role", None) != "admin":
            return Response({"error": "Admin role required."}, status=http_status.HTTP_403_FORBIDDEN)
        try:
            days = int(request.query_params.get("days", 14))
        except (TypeError, ValueError):
            days = 14
        days = max(1, min(days, 90))
        return Response(group_metrics.org_summary(days=days))


class AssistantScopeView(APIView):
    """
    Tells the assistant UI which perspectives the current user may use and which
    projects they can chat about. Employees get "my work" only; managers get the
    projects they lead/manage; admins get every project.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = services.assistant_role(request.user)
        can_broad = role in ("manager", "admin")
        project_ids = services.manageable_project_ids(request.user) if can_broad else set()
        projects = (
            Project.objects.filter(pk__in=project_ids).order_by("name") if project_ids else []
        )
        return Response(
            {
                "role": role,
                "can_team": can_broad,
                "can_project": can_broad,
                "projects": [{"id": p.id, "name": p.name} for p in projects],
            }
        )


class GroupListView(APIView):
    """Projects the user can see, presented as selectable 'groups' (teams)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        ids = services.visible_project_ids(request.user)
        projects = Project.objects.filter(pk__in=ids).order_by("name")
        return Response(
            [
                {
                    "id": p.id,
                    "name": p.name,
                    "lead": p.lead.username if p.lead_id else None,
                }
                for p in projects
            ]
        )


class GroupSummaryView(APIView):
    """One-shot live summary for the Group dashboard (roster + productivity + status)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not services.can_view_project(request.user, pk):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        project = get_object_or_404(Project, pk=pk)
        try:
            days = int(request.query_params.get("days", 14))
        except (TypeError, ValueError):
            days = 14
        days = max(1, min(days, 90))
        return Response(group_metrics.group_summary(project, days=days))


class ProjectMembersView(APIView):
    """Members (+ lead/manager) of a project, for assignee pickers."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not services.can_view_project(request.user, pk):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        project = get_object_or_404(Project, pk=pk)
        ids = set(project.members.values_list("user_id", flat=True))
        if project.lead_id:
            ids.add(project.lead_id)
        if project.manager_id:
            ids.add(project.manager_id)
        users = User.objects.filter(pk__in=ids).order_by("username")
        return Response(UserMiniSerializer(users, many=True).data)


class WorkItemListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = WorkItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        project = ser.validated_data.get("project")
        # Only a project manager/lead (or admin) may create and assign work items.
        if not project or not services.can_manage_project(request.user, project.pk):
            return Response(
                {"error": "Only a project manager or admin can create tasks."},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        item = ser.save(created_by=request.user)
        return Response(WorkItemSerializer(item).data, status=http_status.HTTP_201_CREATED)


class WorkItemDetailView(APIView):
    """
    Update a work item with role-aware rules:
      - admin / project manager: full edit (any field, any assignee, status, planning).
      - employee (member): may edit only tasks assigned to them (limited fields + status),
        and may self-assign an *unassigned* task to themselves. They can never reassign,
        move tasks between sprints, or edit tasks that are not theirs.
    Status changes always go through the audited service so the burndown stays correct.
    """

    permission_classes = [IsAuthenticated]

    def _get_item(self, pk):
        return get_object_or_404(Task.objects.select_related("project", "user"), pk=pk)

    def _can_view(self, user, item):
        if item.project_id is None:
            return item.user_id == user.pk or item.created_by_id == user.pk
        return services.can_view_project(user, item.project_id)

    @staticmethod
    def _scalar(value):
        if isinstance(value, list):
            return value[0] if value else None
        return value

    def get(self, request, pk):
        item = self._get_item(pk)
        if not self._can_view(request.user, item):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        return Response(WorkItemSerializer(item).data)

    def patch(self, request, pk):
        item = self._get_item(pk)
        user = request.user
        if not self._can_view(user, item):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)

        is_manager = bool(item.project_id and services.can_manage_project(user, item.project_id))
        is_owner = item.user_id == user.pk

        data = dict(request.data)
        new_status = self._scalar(data.pop("status", None))

        assignee_provided = "assignee_id" in data
        requested_assignee = self._scalar(data.get("assignee_id")) if assignee_provided else None
        # Treat "assign to current owner" as a no-op (avoids spurious 403s).
        if assignee_provided and requested_assignee == item.user_id:
            assignee_provided = False
            data.pop("assignee_id", None)

        if not is_manager:
            if assignee_provided:
                # Employees may only self-assign a currently-unassigned task.
                self_assign = item.user_id is None and str(requested_assignee) == str(user.pk)
                if not self_assign:
                    return Response(
                        {"error": "Reassigning a task is restricted to its manager or an admin."},
                        status=http_status.HTTP_403_FORBIDDEN,
                    )
                # Limit this request strictly to the self-assignment.
                data = {"assignee_id": user.pk}
                new_status = None
            else:
                if not is_owner:
                    return Response(
                        {"error": "You can only update tasks assigned to you."},
                        status=http_status.HTTP_403_FORBIDDEN,
                    )
                disallowed = set(data.keys()) - EMPLOYEE_EDITABLE_FIELDS
                if disallowed:
                    return Response(
                        {
                            "error": "You can update the details and status of your task; "
                            "project, sprint and assignee changes are manager/admin only."
                        },
                        status=http_status.HTTP_403_FORBIDDEN,
                    )

        if data:
            ser = WorkItemSerializer(item, data=data, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()

        if new_status and new_status != item.status:
            services.apply_status_change(item, new_status, changed_by=user)

        item.refresh_from_db()
        return Response(WorkItemSerializer(item).data)

    def delete(self, request, pk):
        item = self._get_item(pk)
        if not (item.project_id and services.can_manage_project(request.user, item.project_id)):
            return Response(
                {"error": "Only a project manager or admin can delete tasks."},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        item.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)


def _can_view_item(user, item):
    if item.project_id is None:
        return item.user_id == user.pk or item.created_by_id == user.pk
    return services.can_view_project(user, item.project_id)


class WorkItemDetailDataView(APIView):
    """
    Everything the item-detail drawer needs in one call: the item, its
    status-history timeline, the comment feed, and actual tracked focus time.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        item = get_object_or_404(
            Task.objects.select_related("project", "user", "sprint"), pk=pk
        )
        if not _can_view_item(request.user, item):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)

        history = (
            SprintStatusChange.objects.filter(task=item)
            .select_related("changed_by")
            .order_by("changed_at", "id")
        )
        comments = item.comments.select_related("author").all()
        can_manage = bool(item.project_id and services.can_manage_project(request.user, item.project_id))
        return Response(
            {
                "item": WorkItemSerializer(item).data,
                "history": StatusChangeSerializer(history, many=True).data,
                "comments": WorkItemCommentSerializer(comments, many=True).data,
                "effort": metrics.work_item_effort(item),
                "can_manage": can_manage,
                "is_owner": item.user_id == request.user.pk,
            }
        )


class WorkItemCommentListCreateView(APIView):
    """List / add comments on a work item. Any project member who can view may comment."""

    permission_classes = [IsAuthenticated]

    def _get_item(self, pk):
        return get_object_or_404(Task.objects.select_related("project", "user"), pk=pk)

    def get(self, request, pk):
        item = self._get_item(pk)
        if not _can_view_item(request.user, item):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        comments = item.comments.select_related("author").all()
        return Response(WorkItemCommentSerializer(comments, many=True).data)

    def post(self, request, pk):
        item = self._get_item(pk)
        if not _can_view_item(request.user, item):
            return Response({"error": "Not allowed."}, status=http_status.HTTP_403_FORBIDDEN)
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response(
                {"error": "Comment body is required."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        comment = WorkItemComment.objects.create(task=item, author=request.user, body=body)
        return Response(
            WorkItemCommentSerializer(comment).data, status=http_status.HTTP_201_CREATED
        )

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..brain import generate_assistant_reply
from ..memory import extract_and_store_memories
from ..report import _EMAIL_RE, build_usage_report, render_report_email
from smartagile.models import AssistantChatMessage, AssistantChatSession
from smartagile.serializers import (
    AssistantChatMessageSerializer,
    AssistantChatSessionDetailSerializer,
    AssistantChatSessionListSerializer,
    AssistantUserMessageInSerializer,
)
from smartagile.tasks import send_usage_report_email

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class AssistantSessionListCreateView(APIView):
    """List or create chat sessions for the current user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        qs = AssistantChatSession.objects.filter(user=request.user)
        return Response(AssistantChatSessionListSerializer(qs, many=True).data)

    def post(self, request, *args, **kwargs):
        body = request.data or {}
        title = body.get("title")
        if not isinstance(title, str):
            title = "New chat"
        title = title.strip()[:200] or "New chat"
        s = AssistantChatSession.objects.create(user=request.user, title=title)
        s = (
            AssistantChatSession.objects.prefetch_related("messages")
            .filter(pk=s.pk)
            .get()
        )
        return Response(
            AssistantChatSessionDetailSerializer(s).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name="dispatch")
class AssistantSessionDetailView(APIView):
    """Get or delete a single session (with messages on GET)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id, *args, **kwargs):
        s = get_object_or_404(
            AssistantChatSession.objects.prefetch_related("messages"),
            pk=session_id,
            user=request.user,
        )
        return Response(AssistantChatSessionDetailSerializer(s).data)

    def delete(self, request, session_id, *args, **kwargs):
        s = get_object_or_404(AssistantChatSession, pk=session_id, user=request.user)
        s.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name="dispatch")
class AssistantSessionMessageView(APIView):
    """Post a user message; persist assistant reply with optional structured result_json."""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id, *args, **kwargs):
        s = get_object_or_404(AssistantChatSession, pk=session_id, user=request.user)
        ser_in = AssistantUserMessageInSerializer(data=request.data)
        ser_in.is_valid(raise_exception=True)
        content = (ser_in.validated_data.get("content") or "").strip()
        if not content:
            return Response(
                {"error": "content is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user_msg = AssistantChatMessage.objects.create(
                session=s,
                role=AssistantChatMessage.Role.USER,
                content=content,
                result_json=None,
            )
            if s.title == "New chat" and content:
                s.title = (content[:57] + "…") if len(content) > 60 else content

            # Store lightweight long-term memory candidates from the user message.
            try:
                extract_and_store_memories(request.user, content)
            except Exception:
                logger.exception("extract_and_store_memories failed")

            text, result_json = generate_assistant_reply(
                request.user,
                content,
                session_id=s.pk,
            )
            asst_msg = AssistantChatMessage.objects.create(
                session=s,
                role=AssistantChatMessage.Role.ASSISTANT,
                content=text,
                result_json=result_json,
            )
            s.save()

        return Response(
            {
                "user_message": AssistantChatMessageSerializer(user_msg).data,
                "assistant_message": AssistantChatMessageSerializer(asst_msg).data,
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name="dispatch")
class AssistantReportConfirmView(APIView):
    """
    Confirm + send a usage report drafted earlier in the chat.

    Body: {"message_id": <draft assistant message id>, "recipient": "<optional override>"}.
    Rebuilds the report from the stored period (fresh data), sends the email, and appends
    an assistant "sent" message. Refuses to send the same draft twice.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id, *args, **kwargs):
        s = get_object_or_404(AssistantChatSession, pk=session_id, user=request.user)

        body = request.data or {}
        try:
            message_id = int(body.get("message_id"))
        except (TypeError, ValueError):
            return Response({"error": "message_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        draft_msg = get_object_or_404(
            AssistantChatMessage,
            pk=message_id,
            session=s,
            role=AssistantChatMessage.Role.ASSISTANT,
        )
        rj = draft_msg.result_json if isinstance(draft_msg.result_json, dict) else {}
        if rj.get("kind") != "email_report_draft":
            return Response(
                {"error": "That message is not a report draft."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        draft = rj.get("draft") or {}

        # Double-send guard: was this draft already sent in this session?
        already = (
            AssistantChatMessage.objects.filter(
                session=s,
                role=AssistantChatMessage.Role.ASSISTANT,
                result_json__kind="email_report_sent",
                result_json__draft_message_id=message_id,
            ).exists()
        )
        if already:
            return Response(
                {"error": "This report was already sent."},
                status=status.HTTP_409_CONFLICT,
            )

        # Recipient: explicit override > drafted recipient.
        recipient = (str(body.get("recipient") or "").strip()) or (draft.get("recipient") or "")
        recipient = recipient.strip()
        if not recipient or not _EMAIL_RE.fullmatch(recipient):
            return Response(
                {"error": "Please provide a valid email address to send the report to."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        period = draft.get("period") or {"kind": "yesterday"}
        report = build_usage_report(request.user, period)
        subject, html_body, text_body = render_report_email(report, user=request.user)

        try:
            send_usage_report_email(recipient, subject, html_body, text_body)
        except RuntimeError as exc:
            logger.warning("report email not configured: %s", exc)
            return Response(
                {"error": "Email isn't configured on the server yet (missing SMTP credentials)."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("send_usage_report_email failed for %r", recipient)
            return Response(
                {"error": "Sending the email failed. Please try again in a moment."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        label = report.get("period_label") or draft.get("period_label") or "your activity"
        text = f"Sent your **{label}** usage report to **{recipient}**."
        with transaction.atomic():
            sent_msg = AssistantChatMessage.objects.create(
                session=s,
                role=AssistantChatMessage.Role.ASSISTANT,
                content=text,
                result_json={
                    "kind": "email_report_sent",
                    "draft_message_id": message_id,
                    "recipient": recipient,
                    "period_label": label,
                    "subject": subject,
                },
            )
            s.save()

        return Response(
            {"assistant_message": AssistantChatMessageSerializer(sent_msg).data},
            status=status.HTTP_201_CREATED,
        )


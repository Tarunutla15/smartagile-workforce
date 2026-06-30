import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Box,
  Fab,
  Paper,
  Typography,
  TextField,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Divider,
  Button,
  Chip,
  Collapse,
  LinearProgress,
  Stack,
  CircularProgress,
  Avatar,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import SendIcon from "@mui/icons-material/Send";
import AddCommentOutlinedIcon from "@mui/icons-material/AddCommentOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import ViewSidebarIcon from "@mui/icons-material/ViewSidebar";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import FullscreenIcon from "@mui/icons-material/Fullscreen";
import FullscreenExitIcon from "@mui/icons-material/FullscreenExit";
import MinimizeIcon from "@mui/icons-material/Minimize";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useSession } from "../context/SessionContext";

const ACCENT = "#4f46e5";
const ACCENT_GRADIENT = "linear-gradient(135deg, #6366f1 0%, #4f46e5 55%, #7c3aed 100%)";

// Theme-aware surfaces so cards/bubbles stay legible in both light and dark mode.
const isDark = (t) => t.palette.mode === "dark";
const richCardSx = {
  borderRadius: 2.5,
  border: 1,
  borderColor: (t) => (isDark(t) ? "rgba(255,255,255,0.12)" : "rgba(79,70,229,0.16)"),
  bgcolor: (t) => (isDark(t) ? "rgba(124,58,237,0.14)" : "rgba(79,70,229,0.05)"),
};
const assistantBubbleSx = {
  bgcolor: (t) => (isDark(t) ? "rgba(255,255,255,0.07)" : "#f1f5f9"),
  borderColor: (t) => (isDark(t) ? "rgba(255,255,255,0.10)" : "rgba(15,23,42,0.08)"),
};
const softChip = (color) => ({
  height: 20,
  fontSize: 10,
  fontWeight: 700,
  bgcolor: `${color}26`,
  color,
  border: 1,
  borderColor: `${color}66`,
});
const PANEL_H = "min(600px, min(90vh, calc(100dvh - 32px)))";
const PANEL_W = "min(920px, calc(100% - 32px))";
const LS_HISTORY = "sa_assistant_history_open";
const LS_POS = "sa_assistant_pos";
const LS_SCOPE = "sa_assistant_scope";
const EDGE_MARGIN = 8;

const clamp = (v, min, max) => Math.min(Math.max(v, min), max);

// Perspective the user can ask from. "me" = their own work (employee view);
// "team"/"project" surface everyone's sprint items (manager view, gated server-side).
const SCOPES = [
  { value: "me", label: "My work", icon: <PersonOutlineIcon sx={{ fontSize: 16 }} />, hint: "Answers about your own tasks and time" },
  { value: "team", label: "Team", icon: <GroupsOutlinedIcon sx={{ fontSize: 16 }} />, hint: "Your team's sprint board (members & leads)" },
  { value: "project", label: "Project", icon: <FolderOutlinedIcon sx={{ fontSize: 16 }} />, hint: "Whole project / org rollups (managers & admins)" },
];

// Suggested prompts per scope shown on an empty chat.
const SUGGESTIONS = {
  me: [
    "What tasks are assigned to me in the sprint?",
    "What are my pending tasks?",
    "How productive was I today?",
    "Email me my weekly report",
  ],
  team: [
    "What's the sprint status?",
    "List the pending tasks in the sprint",
    "Show the sprint burndown",
    "Which tasks are in progress?",
  ],
  project: [
    "List the sprints",
    "What's the sprint status?",
    "Show completed items in the sprint",
    "Create a sprint called Sprint 5",
  ],
};

const WORK_STATUS = {
  todo: { label: "To Do", color: "#94a3b8" },
  inProgress: { label: "In Progress", color: "#f59e0b" },
  done: { label: "Done", color: "#10b981" },
};

/**
 * Renders a simple preview of assistant text: **bold** segments, rest plain.
 */
function FormattedText({ text }) {
  if (!text) return null;
  const parts = String(text).split(/(\*\*[^*]+\*\*)/g);
  return (
    <Box component="span" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
      {parts.map((p, i) => {
        if (p.startsWith("**") && p.endsWith("**") && p.length > 4) {
          return (
            <Box component="strong" key={i} sx={{ fontWeight: 700 }}>
              {p.slice(2, -2)}
            </Box>
          );
        }
        return <span key={i}>{p}</span>;
      })}
    </Box>
  );
}

function ResultJsonBlock({ data }) {
  const [open, setOpen] = useState(false);
  if (data == null) return null;
  let s;
  try {
    s = JSON.stringify(data, null, 2);
  } catch {
    s = String(data);
  }
  if (s.length < 2) return null;
  return (
    <Box sx={{ mt: 0.5 }}>
      <Button
        size="small"
        endIcon={<ExpandMoreIcon sx={{ transform: open ? "rotate(180deg)" : 0, transition: "0.2s" }} />}
        onClick={() => setOpen((v) => !v)}
        sx={{ textTransform: "none", fontSize: 12, p: 0, minWidth: 0, color: "text.secondary" }}
      >
        Structured data (JSON)
      </Button>
      <Collapse in={open}>
        <Box
          component="pre"
          sx={{
            mt: 0.5,
            p: 1,
            borderRadius: 1,
            bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(0,0,0,0.25)" : "rgba(0,0,0,0.04)"),
            fontSize: 11,
            overflow: "auto",
            maxHeight: 200,
          }}
        >
          {s}
        </Box>
      </Collapse>
    </Box>
  );
}

function ThinkingBubble() {
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <CircularProgress size={14} thickness={5} />
      <Typography variant="body2" sx={{ opacity: 0.85 }}>
        Thinking…
      </Typography>
    </Stack>
  );
}

const EMAIL_RE = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

/**
 * Draft card for an emailed usage report. Lets the user confirm/override the recipient
 * and Send (calls the confirm endpoint) or Cancel (local only).
 */
function ReportDraftCard({ sessionId, messageId, draft, alreadySent, onSent }) {
  const [recipient, setRecipient] = useState(draft?.recipient || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [canceled, setCanceled] = useState(false);

  const summary = draft?.summary || {};
  const apps = (draft?.top_apps || []).slice(0, 3);
  const validRecipient = EMAIL_RE.test((recipient || "").trim());

  const handleSend = async () => {
    if (!validRecipient || busy) return;
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post(`/api/assistant/sessions/${sessionId}/report/confirm/`, {
        message_id: messageId,
        recipient: recipient.trim(),
      });
      onSent?.(data.assistant_message);
    } catch (e) {
      setError(e?.response?.data?.error || e?.message || "Could not send the report");
    } finally {
      setBusy(false);
    }
  };

  const done = alreadySent;

  return (
    <Box
      sx={{
        mt: 1,
        p: 1.25,
        borderRadius: 2,
        border: 1,
        borderColor: "divider",
        ...richCardSx,
      }}
    >
      <Typography sx={{ fontSize: 13, fontWeight: 700, color: "text.primary", mb: 0.5 }}>
        Email report{draft?.period_label ? ` — ${draft.period_label}` : ""}
      </Typography>

      {draft?.has_data ? (
        <Box sx={{ mb: 1 }}>
          <Stack direction="row" spacing={2} sx={{ mb: 0.5 }}>
            <Box>
              <Typography sx={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 0.5, color: "text.secondary" }}>
                Total
              </Typography>
              <Typography sx={{ fontSize: 14, fontWeight: 700 }}>{summary.total_human || "—"}</Typography>
            </Box>
            <Box>
              <Typography sx={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 0.5, color: "text.secondary" }}>
                Focus
              </Typography>
              <Typography sx={{ fontSize: 14, fontWeight: 700 }}>{summary.focus_pct || "—"}</Typography>
            </Box>
          </Stack>
          {apps.length > 0 && (
            <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
              Top: {apps.map((a) => `${a.name} (${a.duration_human})`).join(", ")}
            </Typography>
          )}
        </Box>
      ) : (
        <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1 }}>
          No tracked activity for this period yet — the email will say so.
        </Typography>
      )}

      <TextField
        size="small"
        fullWidth
        label="Send to"
        placeholder="name@example.com"
        value={recipient}
        disabled={done || canceled || busy}
        onChange={(e) => setRecipient(e.target.value)}
        error={Boolean(recipient) && !validRecipient}
        sx={{ mb: 1 }}
      />

      {error && (
        <Typography color="error" sx={{ fontSize: 12, mb: 1 }}>
          {error}
        </Typography>
      )}

      {done ? (
        <Typography sx={{ fontSize: 13, fontWeight: 600, color: "success.main" }}>
          ✓ Sent
        </Typography>
      ) : canceled ? (
        <Typography sx={{ fontSize: 13, color: "text.secondary" }}>Canceled.</Typography>
      ) : (
        <Stack direction="row" spacing={1}>
          <Button
            variant="contained"
            size="small"
            onClick={handleSend}
            disabled={!validRecipient || busy}
            startIcon={busy ? <CircularProgress size={14} color="inherit" /> : <SendIcon sx={{ fontSize: 16 }} />}
            sx={{ textTransform: "none", bgcolor: ACCENT, "&:hover": { bgcolor: "#4338ca" } }}
          >
            {busy ? "Sending…" : "Send"}
          </Button>
          <Button
            variant="text"
            size="small"
            onClick={() => setCanceled(true)}
            disabled={busy}
            sx={{ textTransform: "none", color: "text.secondary" }}
          >
            Cancel
          </Button>
        </Stack>
      )}
    </Box>
  );
}

const SPRINT_ACTION_KINDS = new Set([
  "sprint_created",
  "sprint_started",
  "sprint_completed",
  "work_item_added",
  "work_item_moved",
  "work_item_status",
]);

const SPRINT_STATUS_COLOR = { planned: "default", active: "success", completed: "info" };

// When a rich sprint card fully represents the answer, hide the duplicate plain text.
function sprintCardIsRich(rj) {
  if (!rj || typeof rj !== "object") return false;
  if (rj.kind === "sprint_status") return true;
  if (rj.kind === "sprint_items") return (rj.items || []).length > 0;
  if (rj.kind === "sprint_list") return (rj.sprints || []).length > 0;
  if (rj.kind === "team_overview") return (rj.members || []).length > 0;
  if (rj.kind === "team_roster") return (rj.members || []).length > 0;
  if (rj.kind === "project_list") return (rj.projects || []).length > 0;
  // A compound answer renders each part itself (cards + text), so the duplicate
  // top-level concatenated text is always hidden.
  if (rj.kind === "sprint_multi") return true;
  return false;
}

/**
 * Compact card for the sprint skill's structured results: a confirmation chip for
 * actions, key metrics for status, and a list for "list sprints".
 */
const clickableSx = {
  cursor: "pointer",
  transition: "background-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease",
  "&:hover": {
    transform: "translateY(-1px)",
    boxShadow: "0 6px 18px rgba(79,70,229,0.18)",
    borderColor: ACCENT,
  },
};

const rowHoverSx = {
  borderRadius: 1.5,
  px: 0.5,
  mx: -0.5,
  cursor: "pointer",
  transition: "background-color 0.12s ease",
  "&:hover": { bgcolor: (t) => (isDark(t) ? "rgba(124,58,237,0.20)" : "rgba(79,70,229,0.08)") },
};

function SprintResultCard({ data, onNavigate }) {
  const kind = data?.kind;
  if (
    !kind ||
    (!kind.startsWith("sprint_") &&
      !kind.startsWith("work_item_") &&
      !kind.startsWith("team_") &&
      kind !== "project_list")
  ) {
    return null;
  }

  if (kind === "sprint_error" || kind === "sprint_help") return null;

  // Compound answer: render each part (a rich card when available, otherwise the
  // part's own text) so every sub-question in one message is shown.
  if (kind === "sprint_multi") {
    const parts = Array.isArray(data.parts) ? data.parts : [];
    if (!parts.length) return null;
    return (
      <Stack spacing={1} sx={{ mt: 0.5 }}>
        {parts.map((p, i) =>
          sprintCardIsRich(p) ? (
            <SprintResultCard key={i} data={p} onNavigate={onNavigate} />
          ) : p?.text ? (
            <FormattedText key={i} text={p.text} />
          ) : null
        )}
      </Stack>
    );
  }

  const open = (target) => (onNavigate ? () => onNavigate(target) : undefined);

  if (kind === "sprint_status") {
    const s = data.summary || {};
    const sp = data.sprint || {};
    const eff = data.effort;
    const pct = s.completion_pct ?? 0;
    return (
      <Box
        onClick={open(sp)}
        sx={{ mt: 1, p: 1.25, ...richCardSx, ...(onNavigate ? clickableSx : {}) }}
      >
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.75 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{sp.name}</Typography>
          <Chip size="small" label={sp.status} color={SPRINT_STATUS_COLOR[sp.status] || "default"} />
          <Box sx={{ flex: 1 }} />
          {onNavigate && <OpenInNewIcon sx={{ fontSize: 15, color: "text.secondary" }} />}
        </Stack>
        <LinearProgress variant="determinate" value={Math.min(100, pct)} sx={{ height: 8, borderRadius: 4, mb: 0.75 }} />
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip size="small" variant="outlined" label={`${s.done_count}/${s.item_count} items`} />
          <Chip size="small" variant="outlined" label={`${s.done_points}/${s.total_points} pts`} />
          <Chip size="small" variant="outlined" label={`${pct}% done`} />
          {eff?.focus_hours ? (
            <Chip size="small" variant="outlined" color="success" label={`${eff.focus_hours}h focus`} />
          ) : null}
        </Stack>
      </Box>
    );
  }

  if (kind === "team_overview" || kind === "team_roster") {
    const members = data.members || [];
    if (!members.length) return null;
    const initials = (name) => (name || "?").slice(0, 2).toUpperCase();
    const teamTarget = { id: data.sprint?.id, project_id: data.project_id };
    return (
      <Box
        onClick={open(teamTarget)}
        sx={{ mt: 1, p: 1.25, ...richCardSx, ...(onNavigate ? clickableSx : {}) }}
      >
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <GroupsOutlinedIcon sx={{ fontSize: 18, color: ACCENT }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 700, flex: 1 }}>
            {data.project || "Team"}
          </Typography>
          {data.sprint?.name && <Chip size="small" variant="outlined" label={data.sprint.name} />}
          <Typography variant="caption" color="text.secondary">
            {members.length} {members.length === 1 ? "person" : "people"}
          </Typography>
          {onNavigate && <OpenInNewIcon sx={{ fontSize: 15, color: "text.secondary" }} />}
        </Stack>
        <Stack spacing={1}>
          {members.map((mem) => (
            <Stack key={mem.username} direction="row" spacing={1} alignItems="center">
              <Avatar
                sx={{
                  width: 26,
                  height: 26,
                  fontSize: 11,
                  fontWeight: 700,
                  bgcolor: (t) => (isDark(t) ? "rgba(124,58,237,0.35)" : "rgba(79,70,229,0.16)"),
                  color: (t) => (isDark(t) ? "#c7d2fe" : ACCENT),
                }}
              >
                {initials(mem.username)}
              </Avatar>
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Stack direction="row" spacing={0.75} alignItems="center">
                  <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
                    {mem.username}
                  </Typography>
                  <Chip size="small" label={mem.role} sx={{ height: 18, fontSize: 10 }} />
                </Stack>
                {kind === "team_overview" && (
                  <Typography variant="caption" color="text.secondary" noWrap title={mem.doing || ""}>
                    {mem.doing
                      ? `On: ${mem.doing}${mem.todo_count ? ` · ${mem.todo_count} to-do` : ""}`
                      : mem.open_count
                        ? `${mem.todo_count} to-do`
                        : "No open items"}
                  </Typography>
                )}
              </Box>
              {kind === "team_overview" && (
                <Chip
                  size="small"
                  variant="outlined"
                  color={mem.in_progress?.length ? "warning" : "default"}
                  label={`${mem.open_count || 0} open`}
                  sx={{ height: 20, fontSize: 10 }}
                />
              )}
            </Stack>
          ))}
        </Stack>
      </Box>
    );
  }

  if (kind === "sprint_items") {
    const items = data.items || [];
    const sp = data.sprint || {};
    if (!items.length) return null;
    return (
      <Box sx={{ mt: 1, p: 1.25, ...richCardSx }}>
        <Stack
          direction="row"
          spacing={1}
          alignItems="center"
          onClick={open(sp)}
          sx={{ mb: 1, ...(onNavigate ? { cursor: "pointer" } : {}) }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{sp.name || "Sprint"}</Typography>
          {data.filter && data.filter !== "all" && (
            <Chip size="small" variant="outlined" label={WORK_STATUS[data.filter]?.label || data.filter} />
          )}
          {data.mine && <Chip size="small" color="primary" variant="outlined" label="Assigned to me" />}
          <Box sx={{ flex: 1 }} />
          <Typography variant="caption" color="text.secondary">{items.length} item{items.length === 1 ? "" : "s"}</Typography>
          {onNavigate && <OpenInNewIcon sx={{ fontSize: 15, color: "text.secondary" }} />}
        </Stack>
        <Stack spacing={0.75}>
          {items.slice(0, 20).map((it) => {
            const st = WORK_STATUS[it.status] || { label: it.status, color: "#94a3b8" };
            return (
              <Stack
                key={it.id}
                direction="row"
                spacing={1}
                alignItems="center"
                onClick={open({ ...sp, item_id: it.id })}
                sx={onNavigate ? rowHoverSx : undefined}
              >
                <Box sx={{ width: 9, height: 9, borderRadius: "50%", bgcolor: st.color, flexShrink: 0 }} />
                <Typography variant="body2" sx={{ fontWeight: 600, flex: 1, minWidth: 0 }} noWrap title={it.title}>
                  {it.title}
                </Typography>
                {it.story_points != null && (
                  <Chip size="small" variant="outlined" label={`${it.story_points} pts`} sx={{ height: 20, fontSize: 10 }} />
                )}
                <Chip size="small" label={st.label} sx={softChip(st.color)} />
                {!data.mine && it.assignee && (
                  <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
                    @{it.assignee}
                  </Typography>
                )}
              </Stack>
            );
          })}
        </Stack>
        {items.length > 20 && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
            +{items.length - 20} more…
          </Typography>
        )}
      </Box>
    );
  }

  if (kind === "sprint_list") {
    const sprints = data.sprints || [];
    if (!sprints.length) return null;
    return (
      <Box sx={{ mt: 1 }}>
        <Stack spacing={0.5}>
          {sprints.slice(0, 12).map((s) => (
            <Stack
              key={s.id}
              direction="row"
              spacing={1}
              alignItems="center"
              onClick={open(s)}
              sx={onNavigate ? { ...rowHoverSx, py: 0.25 } : undefined}
            >
              <Chip size="small" label={s.status} color={SPRINT_STATUS_COLOR[s.status] || "default"} sx={{ minWidth: 78 }} />
              <Typography variant="body2" sx={{ fontWeight: 600, flex: 1 }}>{s.name}</Typography>
              {s.project && (
                <Typography variant="caption" color="text.secondary">· {s.project}</Typography>
              )}
              {onNavigate && <OpenInNewIcon sx={{ fontSize: 14, color: "text.secondary" }} />}
            </Stack>
          ))}
        </Stack>
      </Box>
    );
  }

  if (kind === "project_list") {
    const projects = data.projects || [];
    if (!projects.length) return null;
    return (
      <Box sx={{ mt: 1, p: 1.25, ...richCardSx }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <FolderOutlinedIcon sx={{ fontSize: 18, color: ACCENT }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 700, flex: 1 }}>
            {projects.length === 1 ? "Your project" : `Your projects (${projects.length})`}
          </Typography>
        </Stack>
        <Stack spacing={0.5}>
          {projects.slice(0, 12).map((p) => (
            <Stack
              key={p.id}
              direction="row"
              spacing={1}
              alignItems="center"
              onClick={open({ id: p.sprint_id, project_id: p.id })}
              sx={onNavigate ? { ...rowHoverSx, py: 0.25 } : undefined}
            >
              <Typography variant="body2" sx={{ fontWeight: 600, flex: 1, minWidth: 0 }} noWrap>
                {p.name}
              </Typography>
              {p.active_sprint ? (
                <Chip size="small" color="success" variant="outlined" label={p.active_sprint} />
              ) : (
                <Typography variant="caption" color="text.secondary">
                  no active sprint
                </Typography>
              )}
              {onNavigate && <OpenInNewIcon sx={{ fontSize: 14, color: "text.secondary" }} />}
            </Stack>
          ))}
        </Stack>
      </Box>
    );
  }

  if (SPRINT_ACTION_KINDS.has(kind)) {
    const label = {
      sprint_created: "Sprint created",
      sprint_started: "Sprint started",
      sprint_completed: "Sprint completed",
      work_item_added: "Item added",
      work_item_moved: "Item moved",
      work_item_status: "Status updated",
    }[kind];
    const target = data.sprint || (data.last_sprint ? { id: data.last_sprint } : null);
    return (
      <Box sx={{ mt: 1 }}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Chip size="small" color="success" variant="outlined" label={`✓ ${label}`} />
          {onNavigate && target && (
            <Chip
              size="small"
              variant="outlined"
              icon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
              label="Open board"
              onClick={open(target)}
              sx={{ cursor: "pointer", "&:hover": { borderColor: ACCENT, color: ACCENT } }}
            />
          )}
        </Stack>
      </Box>
    );
  }
  return null;
}

function AssistantChatWidget() {
  const { user, loading: sessionLoading } = useSession();
  const navigate = useNavigate();
  const [panelOpen, setPanelOpen] = useState(false);
  const [maximized, setMaximized] = useState(false);

  // Open the relevant page for a result the user clicked (deep-links the sprint board).
  const goToSprint = useCallback(
    (target) => {
      if (!target) return;
      const params = new URLSearchParams();
      if (target.project_id) params.set("project", String(target.project_id));
      if (target.id) params.set("sprint", String(target.id));
      const qs = params.toString();
      const base = user?.role === "admin" ? "/admin/sprint-dashboard" : "/sprint-dashboard";
      navigate(`${base}${qs ? `?${qs}` : ""}`);
      // Minimize to the bubble so the page is visible; chat state is preserved
      // (the widget stays mounted), so reopening returns to the same place.
      setMaximized(false);
      setPanelOpen(false);
    },
    [navigate, user]
  );
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loadSessionsBusy, setLoadSessionsBusy] = useState(false);
  const [loadChatBusy, setLoadChatBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState("");
  const msgListRef = useRef(null);
  const [historyOpen, setHistoryOpen] = useState(() => {
    try {
      return localStorage.getItem(LS_HISTORY) !== "0";
    } catch {
      return true;
    }
  });
  const [deletingId, setDeletingId] = useState(null);
  const [scope, setScope] = useState(() => {
    try {
      const v = localStorage.getItem(LS_SCOPE);
      if (v === "me" || v === "team" || v === "project") return v;
    } catch {
      /* ignore */
    }
    return "me";
  });
  // Role-based perspective config from the server: which scopes are allowed and
  // which projects the user may chat about (employees get "me" only).
  const [scopeConfig, setScopeConfig] = useState({ role: "employee", can_team: false, can_project: false, projects: [] });
  const [projectId, setProjectId] = useState(null);

  const setScopePersist = useCallback((v) => {
    if (!v) return;
    setScope(v);
    try {
      localStorage.setItem(LS_SCOPE, v);
    } catch {
      /* ignore */
    }
  }, []);

  // Visible scope options for this user (employees can't pick team/project).
  const scopeOptions = useMemo(() => {
    if (scopeConfig.can_team || scopeConfig.can_project) return SCOPES;
    return SCOPES.filter((s) => s.value === "me");
  }, [scopeConfig]);

  const needsProject = (scope === "team" || scope === "project") && (scopeConfig.projects || []).length > 0;

  // --- Draggable panel position (top-left in px; null => default bottom-right) ---
  const panelRef = useRef(null);
  const dragRef = useRef({ dragging: false, offsetX: 0, offsetY: 0 });
  const [pos, setPos] = useState(() => {
    try {
      const raw = localStorage.getItem(LS_POS);
      if (!raw) return null;
      const p = JSON.parse(raw);
      if (p && typeof p.x === "number" && typeof p.y === "number") return p;
    } catch {
      /* ignore */
    }
    return null;
  });

  const clampToViewport = useCallback((p) => {
    const el = panelRef.current;
    const w = el ? el.offsetWidth : 360;
    const h = el ? el.offsetHeight : 480;
    return {
      x: clamp(p.x, EDGE_MARGIN, Math.max(EDGE_MARGIN, window.innerWidth - w - EDGE_MARGIN)),
      y: clamp(p.y, EDGE_MARGIN, Math.max(EDGE_MARGIN, window.innerHeight - h - EDGE_MARGIN)),
    };
  }, []);

  const onDragPointerMove = useCallback(
    (e) => {
      if (!dragRef.current.dragging) return;
      const next = clampToViewport({
        x: e.clientX - dragRef.current.offsetX,
        y: e.clientY - dragRef.current.offsetY,
      });
      setPos(next);
    },
    [clampToViewport]
  );

  const onDragPointerUp = useCallback(() => {
    if (!dragRef.current.dragging) return;
    dragRef.current.dragging = false;
    window.removeEventListener("pointermove", onDragPointerMove);
    window.removeEventListener("pointerup", onDragPointerUp);
    setPos((p) => {
      if (p) {
        try {
          localStorage.setItem(LS_POS, JSON.stringify(p));
        } catch {
          /* ignore */
        }
      }
      return p;
    });
  }, [onDragPointerMove]);

  const onHeaderPointerDown = useCallback(
    (e) => {
      // Don't start a drag when interacting with the header buttons.
      if (e.target.closest("button")) return;
      const el = panelRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      dragRef.current = {
        dragging: true,
        offsetX: e.clientX - rect.left,
        offsetY: e.clientY - rect.top,
      };
      setPos({ x: rect.left, y: rect.top });
      window.addEventListener("pointermove", onDragPointerMove);
      window.addEventListener("pointerup", onDragPointerUp);
    },
    [onDragPointerMove, onDragPointerUp]
  );

  // Keep the panel on-screen when it opens or the window resizes.
  useEffect(() => {
    if (!panelOpen) return undefined;
    const reclamp = () => setPos((p) => (p ? clampToViewport(p) : p));
    const id = requestAnimationFrame(reclamp);
    window.addEventListener("resize", reclamp);
    return () => {
      cancelAnimationFrame(id);
      window.removeEventListener("resize", reclamp);
    };
  }, [panelOpen, clampToViewport]);

  useEffect(
    () => () => {
      window.removeEventListener("pointermove", onDragPointerMove);
      window.removeEventListener("pointerup", onDragPointerUp);
    },
    [onDragPointerMove, onDragPointerUp]
  );

  const setHistoryOpenPersist = useCallback((open) => {
    setHistoryOpen(open);
    try {
      localStorage.setItem(LS_HISTORY, open ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, []);

  const loadSessions = useCallback(async () => {
    setLoadSessionsBusy(true);
    setErr("");
    try {
      const { data } = await api.get("/api/assistant/sessions/");
      setSessions(Array.isArray(data) ? data : []);
    } catch (e) {
      setErr(e?.response?.data?.detail || e?.message || "Failed to load sessions");
    } finally {
      setLoadSessionsBusy(false);
    }
  }, []);

  const loadSessionDetail = useCallback(async (id) => {
    if (id == null) return;
    setLoadChatBusy(true);
    setErr("");
    try {
      const { data } = await api.get(`/api/assistant/sessions/${id}/`);
      setActiveId(data.id);
      setMessages(data.messages || []);
    } catch (e) {
      setErr(e?.response?.data?.detail || e?.message || "Failed to load chat");
    } finally {
      setLoadChatBusy(false);
    }
  }, []);

  useEffect(() => {
    if (panelOpen && user && !sessionLoading) {
      loadSessions();
    }
  }, [panelOpen, user, sessionLoading, loadSessions]);

  // Load the role-based perspective config once the panel opens.
  useEffect(() => {
    if (!panelOpen || !user || sessionLoading) return;
    let alive = true;
    (async () => {
      try {
        const { data } = await api.get("/sprintapi/assistant/scope/");
        if (!alive) return;
        const cfg = {
          role: data?.role || "employee",
          can_team: Boolean(data?.can_team),
          can_project: Boolean(data?.can_project),
          projects: Array.isArray(data?.projects) ? data.projects : [],
        };
        setScopeConfig(cfg);
        // Employees can't use team/project — clamp back to "my work".
        if (!cfg.can_team && !cfg.can_project) {
          setScope("me");
        }
        // Default the chosen project to the first available one.
        setProjectId((prev) => prev ?? (cfg.projects[0]?.id ?? null));
      } catch {
        if (alive) setScopeConfig({ role: "employee", can_team: false, can_project: false, projects: [] });
      }
    })();
    return () => {
      alive = false;
    };
  }, [panelOpen, user, sessionLoading]);

  const scrollToBottom = useCallback(() => {
    const el = msgListRef.current;
    if (!el) return;
    // next frame helps when React just rendered new nodes
    requestAnimationFrame(() => {
      try {
        el.scrollTop = el.scrollHeight;
      } catch {
        /* ignore */
      }
    });
  }, []);

  useEffect(() => {
    if (panelOpen) scrollToBottom();
  }, [panelOpen, scrollToBottom]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const canSend = useMemo(() => Boolean(input.trim() && !sending), [input, sending]);

  // Draft ids that already have a corresponding "sent" message (survives reloads).
  const sentDraftIds = useMemo(() => {
    const set = new Set();
    for (const m of messages) {
      const rj = m?.result_json;
      if (rj && rj.kind === "email_report_sent" && rj.draft_message_id != null) {
        set.add(Number(rj.draft_message_id));
      }
    }
    return set;
  }, [messages]);

  const handleReportSent = useCallback((assistantMessage) => {
    if (!assistantMessage) return;
    setMessages((prev) => [...prev, assistantMessage]);
  }, []);

  const handleNewChat = async () => {
    setErr("");
    setSending(true);
    try {
      const { data } = await api.post("/api/assistant/sessions/", { title: "New chat" });
      setActiveId(data.id);
      setMessages(data.messages || []);
      await loadSessions();
    } catch (e) {
      setErr(e?.response?.data?.detail || e?.message || "Could not start a chat");
    } finally {
      setSending(false);
    }
  };

  const handleSend = async (overrideText) => {
    const t = (typeof overrideText === "string" ? overrideText : input).trim();
    if (!t || sending) return;
    const localUserId = `local-user-${Date.now()}`;
    const localAsstId = `local-asst-${Date.now()}`;
    setInput("");
    setSending(true);
    setErr("");
    setMessages((prev) => [
      ...prev,
      { id: localUserId, role: "user", content: t, result_json: null, created_at: new Date().toISOString() },
      { id: localAsstId, role: "assistant", content: "", result_json: null, created_at: new Date().toISOString(), _pending: true },
    ]);
    try {
      // Typing without an open chat starts a new one automatically.
      let sid = activeId;
      if (!sid) {
        const { data: created } = await api.post("/api/assistant/sessions/", { title: "New chat" });
        sid = created.id;
        setActiveId(created.id);
      }
      const payload = { content: t, scope };
      if ((scope === "team" || scope === "project") && projectId) payload.project_id = projectId;
      const { data } = await api.post(`/api/assistant/sessions/${sid}/messages/`, payload);
      setMessages((prev) => {
        const without = prev.filter((m) => !String(m.id).startsWith("local-"));
        return [
          ...without,
          data.user_message,
          data.assistant_message,
        ];
      });
      await loadSessions();
    } catch (e) {
      setErr(e?.response?.data?.detail || e?.message || "Send failed");
      setInput(t);
      // Remove the pending assistant bubble on error.
      setMessages((prev) => prev.filter((m) => String(m.id) !== localAsstId));
    } finally {
      setSending(false);
    }
  };

  const handleDeleteSession = async (id) => {
    if (id == null) return;
    if (!window.confirm("Delete this chat? This cannot be undone.")) return;
    setErr("");
    setDeletingId(id);
    try {
      await api.delete(`/api/assistant/sessions/${id}/`);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeId === id) {
        setActiveId(null);
        setMessages([]);
      }
    } catch (e) {
      setErr(e?.response?.data?.detail || e?.message || "Could not delete chat");
    } finally {
      setDeletingId(null);
    }
  };

  if (sessionLoading || !user) return null;

  return (
    <>
      {panelOpen && (
        <Box
          ref={panelRef}
          className="assistant-modal-panel"
          tabIndex={-1}
          sx={{
            position: "fixed",
            ...(maximized
              ? { inset: 12, width: "auto", height: "auto", maxWidth: "none", maxHeight: "none" }
              : {
                  ...(pos ? { left: pos.x, top: pos.y } : { right: 24, bottom: 24 }),
                  width: PANEL_W,
                  maxWidth: "min(920px, calc(100vw - 32px))",
                  height: PANEL_H,
                  maxHeight: "min(90vh, 100dvh - 32px)",
                }),
            display: "flex",
            flexDirection: "column",
            outline: "none",
            overflow: "hidden",
            zIndex: (t) => t.zIndex.modal,
          }}
        >
          <Paper
            elevation={0}
            sx={{
              flex: 1,
              minHeight: 0,
              display: "flex",
              flexDirection: "column",
              borderRadius: 3.5,
              overflow: "hidden",
              border: 1,
              borderColor: (t) => (isDark(t) ? "rgba(255,255,255,0.12)" : "rgba(15,23,42,0.08)"),
              boxShadow: (t) =>
                isDark(t)
                  ? "0 24px 60px rgba(0,0,0,0.55), 0 2px 8px rgba(0,0,0,0.4)"
                  : "0 24px 60px rgba(15,23,42,0.18), 0 2px 8px rgba(15,23,42,0.08)",
            }}
          >
            <Box
              onPointerDown={maximized ? undefined : onHeaderPointerDown}
              sx={{
                px: 1.25,
                py: 1,
                display: "flex",
                alignItems: "center",
                gap: 0.75,
                cursor: maximized ? "default" : "move",
                touchAction: "none",
                userSelect: "none",
                color: "#fff",
                background:
                  "radial-gradient(120% 140% at 0% 0%, rgba(255,255,255,0.22) 0%, rgba(255,255,255,0) 42%), " +
                  ACCENT_GRADIENT,
                boxShadow: "0 2px 12px rgba(79,70,229,0.35)",
              }}
            >
              <Tooltip title={historyOpen ? "Hide chat list" : "Show chat list"}>
                <IconButton
                  size="small"
                  onClick={() => setHistoryOpenPersist(!historyOpen)}
                  aria-label={historyOpen ? "Hide chat list" : "Show chat list"}
                  sx={{ color: "rgba(255,255,255,0.85)" }}
                >
                  {historyOpen ? <ChevronLeftIcon fontSize="small" /> : <ViewSidebarIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
              <Avatar
                sx={{
                  width: 30,
                  height: 30,
                  bgcolor: "rgba(255,255,255,0.2)",
                  color: "#fff",
                }}
              >
                <AutoAwesomeIcon sx={{ fontSize: 18 }} />
              </Avatar>
              <Box sx={{ flex: 1, minWidth: 0, lineHeight: 1.1 }}>
                <Typography fontWeight={700} sx={{ fontSize: 15, lineHeight: 1.2 }} noWrap>
                  SmartAgile Assistant
                </Typography>
                <Typography sx={{ fontSize: 11, opacity: 0.85 }} noWrap>
                  Sprints · tasks · productivity
                </Typography>
              </Box>
              {!historyOpen && (
                <Tooltip title="New chat">
                  <IconButton
                    size="small"
                    onClick={handleNewChat}
                    disabled={sending}
                    aria-label="New chat"
                    sx={{ color: "#fff" }}
                  >
                    <AddCommentOutlinedIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
              {activeId && (
                <Tooltip title="Delete this chat">
                  <IconButton
                    size="small"
                    onClick={() => handleDeleteSession(activeId)}
                    disabled={deletingId === activeId}
                    aria-label="Delete this chat"
                    sx={{ color: "rgba(255,255,255,0.9)" }}
                  >
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
              <Tooltip title="Minimize">
                <IconButton
                  size="small"
                  onClick={() => setPanelOpen(false)}
                  aria-label="Minimize"
                  sx={{ color: "#fff", "& svg": { mt: "-6px" } }}
                >
                  <MinimizeIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title={maximized ? "Restore" : "Maximize"}>
                <IconButton
                  size="small"
                  onClick={() => setMaximized((v) => !v)}
                  aria-label={maximized ? "Restore" : "Maximize"}
                  sx={{ color: "#fff" }}
                >
                  {maximized ? <FullscreenExitIcon fontSize="small" /> : <FullscreenIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
              <Tooltip title="Close">
                <IconButton size="small" onClick={() => setPanelOpen(false)} aria-label="close" sx={{ color: "#fff" }}>
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            {err && (
              <Box
                sx={{
                  px: 2,
                  py: 0.5,
                  bgcolor: (t) => (isDark(t) ? "rgba(239,68,68,0.18)" : "rgba(239,68,68,0.10)"),
                  borderBottom: 1,
                  borderColor: (t) => (isDark(t) ? "rgba(239,68,68,0.35)" : "rgba(239,68,68,0.25)"),
                }}
              >
                <Typography variant="caption" sx={{ color: (t) => (isDark(t) ? "#fca5a5" : "#b91c1c") }}>
                  {err}
                </Typography>
              </Box>
            )}
            <Box sx={{ flex: 1, minHeight: 0, display: "flex" }}>
              {/* history (optional) */}
              {historyOpen && (
                <Box
                  sx={{
                    width: 240,
                    flexShrink: 0,
                    borderRight: 1,
                    borderColor: "divider",
                    display: "flex",
                    flexDirection: "column",
                    bgcolor: (t) => (isDark(t) ? "rgba(0,0,0,0.28)" : "rgba(15,23,42,0.025)"),
                  }}
                >
                  <Box sx={{ p: 1 }}>
                    <Button
                      fullWidth
                      size="small"
                      startIcon={<AddCommentOutlinedIcon />}
                      onClick={handleNewChat}
                      disabled={sending}
                      sx={{
                        textTransform: "none",
                        fontWeight: 600,
                        borderRadius: 2,
                        color: "#fff",
                        background: ACCENT_GRADIENT,
                        boxShadow: "none",
                        "&:hover": { background: ACCENT_GRADIENT, filter: "brightness(1.06)" },
                      }}
                      variant="contained"
                    >
                      New chat
                    </Button>
                  </Box>
                  {loadSessionsBusy ? <LinearProgress /> : <Divider />}
                  <List
                    dense
                    sx={{
                      overflowY: "auto",
                      flex: 1,
                      minHeight: 0,
                      py: 0,
                      WebkitOverflowScrolling: "touch",
                    }}
                  >
                    {sessions.map((s) => (
                      <Box
                        key={s.id}
                        sx={{
                          display: "flex",
                          alignItems: "stretch",
                          borderBottom: 1,
                          borderColor: "divider",
                        }}
                      >
                        <ListItemButton
                          selected={s.id === activeId}
                          onClick={() => loadSessionDetail(s.id)}
                          alignItems="flex-start"
                          sx={{
                            flex: 1,
                            minWidth: 0,
                            pr: 0.5,
                            borderLeft: "3px solid transparent",
                            "&.Mui-selected": {
                              borderLeftColor: ACCENT,
                              bgcolor: (t) => (isDark(t) ? "rgba(124,58,237,0.20)" : "rgba(79,70,229,0.10)"),
                              "&:hover": {
                                bgcolor: (t) => (isDark(t) ? "rgba(124,58,237,0.26)" : "rgba(79,70,229,0.14)"),
                              },
                            },
                          }}
                        >
                          <ListItemText
                            primary={s.title || "Chat"}
                            primaryTypographyProps={{ noWrap: true, fontSize: 13, fontWeight: s.id === activeId ? 700 : 500 }}
                            secondary={s.updated_at ? new Date(s.updated_at).toLocaleString() : ""}
                            secondaryTypographyProps={{ fontSize: 10 }}
                          />
                        </ListItemButton>
                        <IconButton
                          size="small"
                          aria-label="Delete chat"
                          disabled={deletingId === s.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteSession(s.id);
                          }}
                          sx={{ alignSelf: "center", color: "text.disabled", "&:hover": { color: "error.main" } }}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    ))}
                  </List>
                </Box>
              )}
              {/* messages */}
              <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
                {loadChatBusy && <LinearProgress />}
                <Box
                  component="div"
                  sx={{
                    flex: 1,
                    minHeight: 0,
                    overflowY: "auto",
                    overflowX: "hidden",
                    WebkitOverflowScrolling: "touch",
                    p: 1.5,
                    display: "flex",
                    flexDirection: "column",
                    gap: 1.25,
                    background: (t) =>
                      isDark(t)
                        ? "linear-gradient(180deg, rgba(124,58,237,0.08) 0%, rgba(0,0,0,0) 28%)"
                        : "linear-gradient(180deg, rgba(79,70,229,0.05) 0%, rgba(255,255,255,0) 28%)",
                    "&::-webkit-scrollbar": { width: 8 },
                    "&::-webkit-scrollbar-thumb": {
                      borderRadius: 8,
                      bgcolor: (t) => (isDark(t) ? "rgba(255,255,255,0.16)" : "rgba(15,23,42,0.18)"),
                    },
                  }}
                  ref={msgListRef}
                >
                  {messages.length === 0 && !loadChatBusy && (
                    <Box sx={{ py: 2, px: 0.5, textAlign: "center", m: "auto" }}>
                      <Avatar
                        sx={{
                          width: 52,
                          height: 52,
                          mx: "auto",
                          mb: 1.5,
                          background: ACCENT_GRADIENT,
                          boxShadow: "0 8px 22px rgba(79,70,229,0.45)",
                        }}
                      >
                        <AutoAwesomeIcon />
                      </Avatar>
                      <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5 }}>
                        Hi {user?.username || user?.first_name || "there"} 👋
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Ask me about your sprint, tasks, or productivity. Pick a perspective below, then try one of these:
                      </Typography>
                      <Stack spacing={1} sx={{ maxWidth: 420, mx: "auto" }}>
                        {(SUGGESTIONS[scope] || SUGGESTIONS.me).map((s) => (
                          <Chip
                            key={s}
                            label={s}
                            onClick={() => handleSend(s)}
                            disabled={sending}
                            variant="outlined"
                            icon={<AutoAwesomeIcon sx={{ fontSize: 15, color: `${ACCENT} !important` }} />}
                            sx={{
                              justifyContent: "flex-start",
                              height: "auto",
                              py: 0.85,
                              borderRadius: 2.5,
                              fontSize: 13,
                              borderColor: (t) => (isDark(t) ? "rgba(255,255,255,0.16)" : "rgba(15,23,42,0.14)"),
                              transition: "all 0.15s ease",
                              "& .MuiChip-label": { whiteSpace: "normal", textAlign: "left" },
                              "&:hover": {
                                borderColor: ACCENT,
                                bgcolor: (t) => (isDark(t) ? "rgba(124,58,237,0.18)" : "rgba(79,70,229,0.07)"),
                                transform: "translateY(-1px)",
                              },
                            }}
                          />
                        ))}
                      </Stack>
                    </Box>
                  )}
                  {messages.map((m) => {
                    const isUser = m.role === "user";
                    const hideText = !isUser && !m._pending && sprintCardIsRich(m.result_json);
                    return (
                      <Stack
                        key={m.id}
                        direction="row"
                        spacing={1}
                        sx={{
                          alignSelf: isUser ? "flex-end" : "flex-start",
                          maxWidth: "92%",
                          flexDirection: isUser ? "row-reverse" : "row",
                          alignItems: "flex-end",
                        }}
                      >
                        {!isUser && (
                          <Avatar
                            sx={{ width: 26, height: 26, background: ACCENT_GRADIENT, flexShrink: 0, mb: 0.25 }}
                          >
                            <AutoAwesomeIcon sx={{ fontSize: 15 }} />
                          </Avatar>
                        )}
                        <Box
                          sx={{
                            px: 1.5,
                            py: 1.1,
                            borderRadius: 2.5,
                            ...(isUser
                              ? { borderBottomRightRadius: 6 }
                              : { borderBottomLeftRadius: 6 }),
                            background: isUser ? ACCENT_GRADIENT : assistantBubbleSx.bgcolor,
                            color: isUser ? "#fff" : "text.primary",
                            border: isUser ? 0 : 1,
                            borderColor: assistantBubbleSx.borderColor,
                            boxShadow: isUser
                              ? "0 6px 18px rgba(79,70,229,0.28)"
                              : (t) => (isDark(t) ? "none" : "0 1px 2px rgba(15,23,42,0.06)"),
                            minWidth: 0,
                          }}
                        >
                          {m.role === "assistant" ? (
                            m._pending ? (
                              <ThinkingBubble />
                            ) : hideText ? null : (
                              <FormattedText text={m.content} />
                            )
                          ) : (
                            <Typography component="div" variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                              {m.content}
                            </Typography>
                          )}
                          {m.role === "assistant" && !m._pending && m.result_json?.kind === "email_report_draft" && (
                            <ReportDraftCard
                              sessionId={activeId}
                              messageId={m.id}
                              draft={m.result_json.draft}
                              alreadySent={sentDraftIds.has(Number(m.id))}
                              onSent={handleReportSent}
                            />
                          )}
                          {m.role === "assistant" && !m._pending && (
                            <SprintResultCard data={m.result_json} onNavigate={goToSprint} />
                          )}
                          {m.role === "assistant" && !m._pending && !hideText && <ResultJsonBlock data={m.result_json} />}
                        </Box>
                      </Stack>
                    );
                  })}
                </Box>
                <Box
                  sx={{
                    p: 1.5,
                    pt: 1,
                    borderTop: 1,
                    borderColor: "divider",
                    bgcolor: (t) => (isDark(t) ? "rgba(255,255,255,0.02)" : "rgba(15,23,42,0.015)"),
                  }}
                >
                  {(scopeConfig.can_team || scopeConfig.can_project) && (
                    <Stack
                      direction="row"
                      spacing={1}
                      alignItems="center"
                      useFlexGap
                      flexWrap="wrap"
                      sx={{ mb: 1 }}
                    >
                      <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
                        Ask as
                      </Typography>
                      <ToggleButtonGroup
                        size="small"
                        exclusive
                        value={scope}
                        onChange={(_e, v) => setScopePersist(v)}
                        sx={{
                          flexWrap: "wrap",
                          "& .MuiToggleButton-root": {
                            textTransform: "none",
                            px: 1.25,
                            py: 0.35,
                            gap: 0.5,
                            fontSize: 12,
                            border: 1,
                            borderColor: "divider",
                            borderRadius: "999px !important",
                            mx: 0.25,
                            "&.Mui-selected": {
                              background: ACCENT_GRADIENT,
                              color: "#fff",
                              "&:hover": { background: ACCENT_GRADIENT },
                            },
                          },
                        }}
                      >
                        {scopeOptions.map((s) => (
                          <ToggleButton key={s.value} value={s.value} aria-label={s.label}>
                            <Tooltip title={s.hint} placement="top">
                              <Stack direction="row" spacing={0.5} alignItems="center">
                                {s.icon}
                                <span>{s.label}</span>
                              </Stack>
                            </Tooltip>
                          </ToggleButton>
                        ))}
                      </ToggleButtonGroup>
                      {needsProject && (
                        <TextField
                          select
                          size="small"
                          value={projectId ?? ""}
                          onChange={(e) => setProjectId(Number(e.target.value))}
                          sx={{ minWidth: 150, "& .MuiOutlinedInput-root": { borderRadius: 2 } }}
                        >
                          {(scopeConfig.projects || []).map((p) => (
                            <MenuItem key={p.id} value={p.id} sx={{ fontSize: 13 }}>
                              {p.name}
                            </MenuItem>
                          ))}
                        </TextField>
                      )}
                    </Stack>
                  )}
                  <Stack direction="row" spacing={1} alignItems="flex-end">
                    <TextField
                      fullWidth
                      multiline
                      maxRows={4}
                      size="small"
                      placeholder="Ask about sprints, tasks or your productivity…"
                      value={input}
                      disabled={sending}
                      autoFocus
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSend();
                        }
                      }}
                      sx={{
                        "& .MuiOutlinedInput-root": {
                          borderRadius: 3,
                          bgcolor: (t) => (isDark(t) ? "rgba(255,255,255,0.05)" : "#fff"),
                          "& fieldset": {
                            borderColor: (t) => (isDark(t) ? "rgba(255,255,255,0.14)" : "rgba(15,23,42,0.14)"),
                          },
                          "&:hover fieldset": { borderColor: ACCENT },
                          "&.Mui-focused fieldset": { borderColor: ACCENT, borderWidth: 2 },
                        },
                      }}
                    />
                    <Tooltip title="Send">
                      <span>
                        <IconButton
                          onClick={() => handleSend()}
                          disabled={!canSend}
                          aria-label="send"
                          sx={{
                            background: ACCENT_GRADIENT,
                            color: "#fff",
                            width: 40,
                            height: 40,
                            flexShrink: 0,
                            boxShadow: "0 4px 12px rgba(79,70,229,0.35)",
                            "&:hover": { background: ACCENT_GRADIENT, filter: "brightness(1.08)" },
                            "&.Mui-disabled": {
                              background: (t) => (isDark(t) ? "rgba(255,255,255,0.10)" : "rgba(15,23,42,0.10)"),
                              color: (t) => (isDark(t) ? "rgba(255,255,255,0.35)" : "rgba(15,23,42,0.30)"),
                              boxShadow: "none",
                            },
                          }}
                        >
                          {sending ? <CircularProgress size={18} color="inherit" /> : <SendIcon fontSize="small" />}
                        </IconButton>
                      </span>
                    </Tooltip>
                  </Stack>
                </Box>
              </Box>
            </Box>
          </Paper>
        </Box>
      )}

      {!panelOpen && (
        <Fab
          color="default"
          aria-label="open assistant"
          onClick={() => setPanelOpen(true)}
          sx={{
            position: "fixed",
            right: 24,
            bottom: 24,
            zIndex: (t) => t.zIndex.drawer + 2,
            background: ACCENT_GRADIENT,
            color: "#fff",
            transition: "transform 0.15s ease, box-shadow 0.15s ease",
            "&:hover": {
              background: ACCENT_GRADIENT,
              filter: "brightness(1.08)",
              transform: "translateY(-2px)",
              boxShadow: "0 16px 36px rgba(79,70,229,0.55)",
            },
            boxShadow: "0 10px 28px rgba(79,70,229,0.45)",
          }}
        >
          <AutoAwesomeIcon />
        </Fab>
      )}
    </>
  );
}

export default AssistantChatWidget;

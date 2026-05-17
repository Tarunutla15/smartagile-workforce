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
  Divider,
  Button,
  Collapse,
  LinearProgress,
  Stack,
  Modal,
  CircularProgress,
} from "@mui/material";
import ChatIcon from "@mui/icons-material/Chat";
import CloseIcon from "@mui/icons-material/Close";
import SendIcon from "@mui/icons-material/Send";
import AddCommentOutlinedIcon from "@mui/icons-material/AddCommentOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import ViewSidebarIcon from "@mui/icons-material/ViewSidebar";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import { api } from "../api/client";
import { useSession } from "../context/SessionContext";

const ACCENT = "#0d9488";
const PANEL_H = "min(560px, min(90vh, calc(100dvh - 32px)))";
const PANEL_W = "min(920px, calc(100% - 32px))";
const LS_HISTORY = "sa_assistant_history_open";

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

function AssistantChatWidget() {
  const { user, loading: sessionLoading } = useSession();
  const [panelOpen, setPanelOpen] = useState(false);
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

  const canSend = useMemo(() => Boolean(activeId && input.trim() && !sending), [activeId, input, sending]);

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

  const handleSend = async () => {
    const t = input.trim();
    if (!t || !activeId || sending) return;
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
      const { data } = await api.post(`/api/assistant/sessions/${activeId}/messages/`, { content: t });
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
      <Modal
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
        disableScrollLock={false}
        keepMounted={false}
        closeAfterTransition={false}
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 2,
          zIndex: (t) => t.zIndex.modal,
        }}
        BackdropProps={{ sx: { backgroundColor: "rgba(0,0,0,0.4)" } }}
      >
        <Box
          onClick={(e) => e.stopPropagation()}
          className="assistant-modal-panel"
          tabIndex={-1}
          sx={{
            position: "relative",
            width: PANEL_W,
            maxWidth: "min(920px, calc(100vw - 32px))",
            height: PANEL_H,
            maxHeight: "min(90vh, 100dvh - 32px)",
            display: "flex",
            flexDirection: "column",
            outline: "none",
            overflow: "hidden",
          }}
        >
          <Paper
            elevation={12}
            sx={{
              flex: 1,
              minHeight: 0,
              display: "flex",
              flexDirection: "column",
              borderRadius: 2,
              overflow: "hidden",
              border: 1,
              borderColor: "divider",
            }}
          >
            <Box
              sx={{
                px: 1,
                py: 1.25,
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                borderBottom: 1,
                borderColor: "divider",
                background: (t) =>
                  t.palette.mode === "dark" ? "rgba(15, 118, 110, 0.15)" : "rgba(13, 148, 136, 0.08)",
              }}
            >
              <IconButton
                size="small"
                onClick={() => setHistoryOpenPersist(!historyOpen)}
                aria-label={historyOpen ? "Hide chat list" : "Show chat list"}
                title={historyOpen ? "Hide chat list" : "Show chat list"}
                sx={{ color: "text.secondary" }}
              >
                {historyOpen ? <ChevronLeftIcon fontSize="small" /> : <ViewSidebarIcon fontSize="small" />}
              </IconButton>
              <Typography fontWeight={700} sx={{ color: "text.primary", flex: 1, pl: 0.5 }}>
                SmartAgile assistant
              </Typography>
              {!historyOpen && (
                <IconButton
                  size="small"
                  onClick={handleNewChat}
                  disabled={sending}
                  aria-label="New chat"
                  title="New chat"
                  sx={{ color: ACCENT }}
                >
                  <AddCommentOutlinedIcon fontSize="small" />
                </IconButton>
              )}
              {activeId && (
                <IconButton
                  size="small"
                  onClick={() => handleDeleteSession(activeId)}
                  disabled={deletingId === activeId}
                  aria-label="Delete this chat"
                  title="Delete this chat"
                  sx={{ color: "error.main" }}
                >
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              )}
              <IconButton size="small" onClick={() => setPanelOpen(false)} aria-label="close">
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>
            {err && (
              <Box sx={{ px: 2, py: 0.5, bgcolor: "error.light" }}>
                <Typography variant="caption" color="error.contrastText">
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
                    bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(0,0,0,0.2)" : "rgba(0,0,0,0.02)"),
                  }}
                >
                  <Box sx={{ p: 1 }}>
                    <Button
                      fullWidth
                      size="small"
                      startIcon={<AddCommentOutlinedIcon />}
                      onClick={handleNewChat}
                      disabled={sending}
                      sx={{ textTransform: "none", color: ACCENT, borderColor: "rgba(13,148,136,0.4)" }}
                      variant="outlined"
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
                          sx={{ flex: 1, minWidth: 0, pr: 0.5 }}
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
                  }}
                  ref={msgListRef}
                >
                  {!activeId && (
                    <Box sx={{ py: 3, textAlign: "center" }}>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {historyOpen
                          ? "Open a chat from the list or start a new one. Messages are saved to your account."
                          : "Show the chat list from the top-left, or start a new chat below."}
                      </Typography>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<AddCommentOutlinedIcon />}
                        onClick={handleNewChat}
                        disabled={sending}
                        sx={{ textTransform: "none", color: ACCENT, borderColor: "rgba(13,148,136,0.4)" }}
                      >
                        New chat
                      </Button>
                    </Box>
                  )}
                  {messages.map((m) => (
                    <Box
                      key={m.id}
                      sx={{
                        alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                        maxWidth: "90%",
                        px: 1.5,
                        py: 1.1,
                        borderRadius: 2,
                        bgcolor:
                          m.role === "user"
                            ? ACCENT
                            : (t) => (t.palette.mode === "dark" ? "rgba(255,255,255,0.07)" : "rgba(15,23,42,0.055)"),
                        color: m.role === "user" ? "#fff" : "text.primary",
                        border: m.role === "assistant" ? 1 : 0,
                        borderColor: "divider",
                        boxShadow: m.role === "user" ? "0 8px 22px rgba(13,148,136,0.18)" : "none",
                      }}
                    >
                      {m.role === "assistant" ? (
                        m._pending ? (
                          <ThinkingBubble />
                        ) : (
                          <FormattedText text={m.content} />
                        )
                      ) : (
                        <Typography component="div" variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                          {m.content}
                        </Typography>
                      )}
                      {m.role === "assistant" && !m._pending && <ResultJsonBlock data={m.result_json} />}
                    </Box>
                  ))}
                </Box>
                <Box sx={{ p: 1.5, borderTop: 1, borderColor: "divider" }}>
                  <Stack direction="row" spacing={1} alignItems="flex-end">
                    <TextField
                      fullWidth
                      multiline
                      maxRows={4}
                      size="small"
                      placeholder={activeId ? "Ask about your productivity (saved to this chat)…" : "Select or start a chat…"}
                      value={input}
                      disabled={!activeId || sending}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSend();
                        }
                      }}
                    />
                    <IconButton
                      color="primary"
                      onClick={handleSend}
                      disabled={!canSend}
                      aria-label="send"
                      sx={{ color: ACCENT }}
                    >
                      <SendIcon />
                    </IconButton>
                  </Stack>
                </Box>
              </Box>
            </Box>
          </Paper>
        </Box>
      </Modal>

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
            bgcolor: ACCENT,
            color: "#fff",
            "&:hover": { bgcolor: "#0f766e" },
            boxShadow: 4,
          }}
        >
          <ChatIcon />
        </Fab>
      )}
    </>
  );
}

export default AssistantChatWidget;

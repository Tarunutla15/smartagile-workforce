import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Box, Button, CircularProgress, Typography } from "@mui/material";
import { API_ORIGIN, getAccessToken, getRefreshToken } from "../api/client";
import { useSession } from "../context/SessionContext";

const PAIRING_PORT = process.env.REACT_APP_AGENT_LOCAL_PORT || "38475";
const PAIRING_BASE = `http://127.0.0.1:${PAIRING_PORT}`;

/**
 * One-click: send JWTs to the local desktop agent (no copy-paste).
 * Agent must be running: `python continous_task.py` (listens on PAIRING_BASE).
 */
export default function DesktopAgentConnect() {
  const { user } = useSession();
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pairing, setPairing] = useState(false);
  const [message, setMessage] = useState("");

  const pollHealth = useCallback(async () => {
    try {
      const r = await fetch(`${PAIRING_BASE}/health`, { method: "GET" });
      if (!r.ok) {
        setHealth(null);
        return;
      }
      setHealth(await r.json());
    } catch {
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    pollHealth();
    const id = setInterval(pollHealth, 5000);
    return () => clearInterval(id);
  }, [pollHealth]);

  const connect = async () => {
    const access = getAccessToken();
    const refresh = getRefreshToken();
    if (!access || !refresh) {
      setMessage("Log in to SmartAgile in this browser, then try again.");
      return;
    }
    const paired = health?.paired_user_id;
    const current = user?.id;
    const willOverwrite = Boolean(health?.has_tokens && paired && current && paired !== current);
    if (willOverwrite) {
      const ok = window.confirm(
        `This PC is currently paired to user id ${paired}. Connecting now will switch the desktop agent to your current account (user id ${current}). Continue?`
      );
      if (!ok) return;
    }
    setPairing(true);
    setMessage("");
    try {
      const r = await fetch(`${PAIRING_BASE}/pair`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          access,
          refresh,
          api_base: API_ORIGIN.replace(/\/$/, ""),
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (r.ok) {
        setMessage("Connected. The agent can send usage on this PC until you log out or revoke sessions.");
        pollHealth();
      } else {
        setMessage(data.error || `Pairing failed (${r.status})`);
      }
    } catch (e) {
      setMessage(
        "Could not reach the agent. Start it on this machine: run continous_task.py in desktop-agent."
      );
    } finally {
      setPairing(false);
    }
  };

  const agentOnline = health && health.ok;
  const pairedUserMismatch = useMemo(() => {
    const paired = health?.paired_user_id;
    const current = user?.id;
    return Boolean(agentOnline && health?.has_tokens && paired && current && paired !== current);
  }, [agentOnline, health, user]);

  return (
    <Box sx={{ mt: 1 }}>
      <Typography variant="subtitle2" fontWeight={700} gutterBottom>
        Desktop activity agent
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        The tracker runs as a small program on <strong>this computer</strong> (not inside the website).
        After you start it, use the button below so you never have to paste API keys.
      </Typography>
      <Alert severity="warning" sx={{ mb: 1.5, py: 0.75 }} variant="outlined">
        <strong>Same machine only.</strong> “Connect” talks to{" "}
        <code>127.0.0.1</code> on the PC where the browser is open. If someone else logs into your
        server from <em>their</em> laptop, they must run the desktop agent on <em>their</em> laptop
        too — your friend’s browser cannot reach the agent on your computer.
      </Alert>
      {loading && <CircularProgress size={20} sx={{ mb: 1 }} />}
      {!loading && !agentOnline && (
        <Alert severity="info" sx={{ mb: 1, py: 0.5 }}>
          Agent not detected on <code>127.0.0.1:{PAIRING_PORT}</code>. From the repo, run:{" "}
          <code>python continous_task.py</code> in the <code>desktop-agent</code> folder, then
          return here.
        </Alert>
      )}
      {agentOnline && (
        <Alert
          severity={pairedUserMismatch ? "warning" : health?.has_tokens ? "success" : "warning"}
          sx={{ mb: 1, py: 0.5 }}
        >
          {pairedUserMismatch
            ? `Agent is paired to a different account (paired user id ${health?.paired_user_id}, you are user id ${user?.id}). Usage uploads will go to the paired account until you connect again.`
            : health?.has_tokens
              ? `Agent is running and has saved tokens (paired user id ${health?.paired_user_id ?? "unknown"}). Usage will upload automatically.`
              : "Agent is running. Click the button to save your session to this PC."}
        </Alert>
      )}
      <Button
        variant="contained"
        size="small"
        disabled={!agentOnline || pairing}
        onClick={connect}
      >
        {pairing ? "Connecting…" : "Connect desktop app (save tokens to this PC)"}
      </Button>
      {message && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {message}
        </Typography>
      )}
    </Box>
  );
}

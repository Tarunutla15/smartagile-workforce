import React, { useCallback, useEffect, useState } from "react";
import { format } from "date-fns";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import NorthEastIcon from "@mui/icons-material/NorthEast";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { api } from "../api/client";

const ACCENT = "#0d9488";

function typeShort(st) {
  if (st === "browser") return "web";
  if (st === "application") return "app";
  return st || "";
}

function shortName(n, max = 22) {
  if (!n) return "—";
  return n.length > max ? `${n.slice(0, max - 1)}…` : n;
}

function scrollToMainIntelligence() {
  const el = document.getElementById("employee-intelligence");
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

/**
 * Compact “at a glance” intelligence for the employee overview sidebar (replaces static help text).
 */
export default function IntelligenceSidePanel() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [payload, setPayload] = useState(null);
  const today = format(new Date(), "yyyy-MM-dd");

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const { data } = await api.get("/api/insights/summary/", { params: { date: today } });
      setPayload(data);
    } catch (e) {
      setErr(e?.response?.data?.error || e?.message || "Could not load");
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [today]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        borderRadius: 2,
        border: 1,
        borderColor: "divider",
        overflow: "hidden",
        background: (t) =>
          t.palette.mode === "dark"
            ? "linear-gradient(165deg, rgba(13,148,136,0.12) 0%, rgba(15,23,42,0.95) 50%, #0f172a 100%)"
            : "linear-gradient(165deg, #ecfdf5 0%, #ffffff 45%, #f8fafc 100%)",
        boxShadow: (t) =>
          t.palette.mode === "dark" ? "0 2px 16px rgba(0,0,0,0.35)" : "0 4px 20px rgba(15, 23, 42, 0.07)",
        position: "relative",
        "&::after": {
          content: '""',
          position: "absolute",
          top: 0,
          right: 0,
          width: 100,
          height: 100,
          background: (t) =>
            `radial-gradient(circle at 100% 0%, ${
              t.palette.mode === "dark" ? "rgba(13,148,136,0.2)" : "rgba(13,148,136,0.12)"
            } 0%, transparent 65%)`,
          pointerEvents: "none",
        },
      }}
    >
      <Box sx={{ p: 2, position: "relative", zIndex: 1, display: "flex", flexDirection: "column", flex: 1 }}>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={1} sx={{ mb: 1.5 }}>
          <Stack direction="row" alignItems="center" gap={1} sx={{ minWidth: 0 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: 1.5,
                display: "grid",
                placeItems: "center",
                bgcolor: "rgba(13, 148, 136, 0.15)",
                border: 1,
                borderColor: "rgba(13, 148, 136, 0.35)",
                color: ACCENT,
                flexShrink: 0,
              }}
            >
              <AutoAwesomeOutlinedIcon fontSize="small" />
            </Box>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle1" fontWeight={800} letterSpacing={-0.2} lineHeight={1.2}>
                Intelligence
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block">
                Today · {today}
              </Typography>
            </Box>
          </Stack>
        </Stack>

        {loading && (
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", py: 4 }}>
            <CircularProgress size={26} thickness={4} sx={{ color: ACCENT }} />
          </Box>
        )}

        {!loading && err && (
          <Typography variant="body2" color="error" sx={{ py: 1 }}>
            {err}
          </Typography>
        )}

        {!loading && !err && payload && (
          <>
            {(() => {
              const f = payload?.features;
              const aa = payload?.app_activity || {};
              const pairs = (Array.isArray(aa.top_switch_pairs) ? aa.top_switch_pairs : []).slice(0, 3);
              const opened = (Array.isArray(aa.most_opened_apps) ? aa.most_opened_apps : []).slice(0, 3);
              const hasN = f && (f.event_count > 0 || f.total_duration_seconds > 0);

              return (
                <>
                  {hasN && (
                    <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.75} sx={{ mb: 2 }}>
                      <Chip
                        size="small"
                        label={f.focus_score != null ? `Focus ${Math.round(f.focus_score * 100)}%` : "Focus n/a"}
                        sx={{ fontWeight: 700, bgcolor: "rgba(13,148,136,0.12)" }}
                      />
                      <Chip size="small" variant="outlined" label={`${f.app_switch_count} switches`} />
                    </Stack>
                  )}

                  {pairs.length > 0 && (
                    <Box sx={{ mb: 2 }}>
                      <Stack direction="row" alignItems="center" gap={0.5} sx={{ mb: 1 }}>
                        <SwapHorizIcon sx={{ fontSize: 18, color: ACCENT }} />
                        <Typography variant="overline" color="text.secondary" fontWeight={800} letterSpacing={0.8}>
                          Top switches
                        </Typography>
                      </Stack>
                      <Stack spacing={1}>
                        {pairs.map((p, i) => (
                          <Box
                            key={`${p.from_name}-${p.to_name}-${i}`}
                            sx={{
                              p: 1.1,
                              borderRadius: 1.5,
                              border: 1,
                              borderColor: "divider",
                              bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.75)"),
                            }}
                          >
                            <Stack
                              direction="row"
                              alignItems="center"
                              justifyContent="space-between"
                              gap={0.5}
                              sx={{ mb: 0.5 }}
                            >
                              <Typography variant="caption" color="text.secondary" noWrap title={p.from_name}>
                                {shortName(p.from_name, 16)}
                                <Box component="span" sx={{ opacity: 0.6, fontSize: "0.65rem", ml: 0.25 }}>
                                  ({typeShort(p.from_source_type)})
                                </Box>
                              </Typography>
                              <Chip size="small" label={`${p.count}×`} sx={{ height: 20, fontSize: "0.7rem", fontWeight: 800 }} />
                            </Stack>
                            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", py: 0.25, opacity: 0.5 }}>
                              <NorthEastIcon sx={{ fontSize: 16, transform: "rotate(90deg)" }} />
                            </Box>
                            <Typography variant="body2" fontWeight={700} noWrap title={p.to_name}>
                              {shortName(p.to_name, 24)}
                              <Box component="span" sx={{ fontWeight: 500, color: "text.secondary", fontSize: "0.7rem", ml: 0.5 }}>
                                ({typeShort(p.to_source_type)})
                              </Box>
                            </Typography>
                          </Box>
                        ))}
                      </Stack>
                    </Box>
                  )}

                  {opened.length > 0 && (
                    <Box sx={{ mb: 1.5 }}>
                      <Stack direction="row" alignItems="center" gap={0.5} sx={{ mb: 1 }}>
                        <OpenInNewIcon sx={{ fontSize: 18, color: ACCENT }} />
                        <Typography variant="overline" color="text.secondary" fontWeight={800} letterSpacing={0.8}>
                          Most opened
                        </Typography>
                      </Stack>
                      <Stack spacing={0.75}>
                        {opened.map((a, i) => (
                          <Stack
                            key={`${a.name}-${i}`}
                            direction="row"
                            alignItems="center"
                            justifyContent="space-between"
                            gap={1}
                            sx={{
                              py: 0.75,
                              px: 1,
                              borderRadius: 1,
                              bgcolor: (t) => (t.palette.mode === "dark" ? "action.hover" : "rgba(0,0,0,0.02)"),
                            }}
                          >
                            <Typography variant="body2" fontWeight={600} noWrap title={a.name} sx={{ minWidth: 0, fontSize: "0.8rem" }}>
                              {i + 1}. {shortName(a.name, 20)}
                            </Typography>
                            <Chip
                              size="small"
                              label={`${a.open_count} opens`}
                              variant="outlined"
                              sx={{ height: 22, fontSize: "0.7rem", flexShrink: 0 }}
                            />
                          </Stack>
                        ))}
                      </Stack>
                    </Box>
                  )}

                  {!hasN && pairs.length === 0 && opened.length === 0 && (
                    <Typography variant="body2" color="text.secondary" sx={{ py: 1, lineHeight: 1.5 }}>
                      No agent activity for today yet. Open the full panel below when data is available.
                    </Typography>
                  )}
                </>
              );
            })()}

            <Divider sx={{ my: 1.5, borderColor: "divider" }} />

            <Button
              fullWidth
              variant="contained"
              size="small"
              onClick={scrollToMainIntelligence}
              endIcon={<NorthEastIcon sx={{ fontSize: 16 }} />}
              sx={{
                mt: 0.5,
                textTransform: "none",
                fontWeight: 700,
                borderRadius: 1.5,
                py: 1,
                bgcolor: ACCENT,
                boxShadow: "0 2px 8px rgba(13,148,136,0.35)",
                "&:hover": { bgcolor: "#0f766e" },
              }}
            >
              Open full intelligence
            </Button>
          </>
        )}
      </Box>
    </Box>
  );
}

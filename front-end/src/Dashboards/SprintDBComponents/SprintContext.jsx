import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useSearchParams } from "react-router-dom";
import { listProjects, listSprints } from "../../api/sprints";
import { useSession } from "../../context/SessionContext";

const SprintContext = createContext(null);

export const useSprint = () => {
  const ctx = useContext(SprintContext);
  if (!ctx) throw new Error("useSprint must be used within <SprintProvider>");
  return ctx;
};

export const SprintProvider = ({ children }) => {
  const { user } = useSession();
  const [searchParams] = useSearchParams();

  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState(null);
  const [sprints, setSprints] = useState([]);
  const [sprintId, setSprintId] = useState(null);

  // Deep-link support: ?project=<id>&sprint=<id> (e.g. from the AI assistant).
  useEffect(() => {
    const p = Number(searchParams.get("project")) || null;
    const s = Number(searchParams.get("sprint")) || null;
    if (p) setProjectId(p);
    if (s) setSprintId(s);
  }, [searchParams]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingSprints, setLoadingSprints] = useState(false);
  const [error, setError] = useState("");
  // Bumped after any mutation so tabs can re-fetch their own data.
  const [refreshKey, setRefreshKey] = useState(0);
  const notifyChange = useCallback(() => setRefreshKey((k) => k + 1), []);

  const loadProjects = useCallback(async () => {
    setLoadingProjects(true);
    setError("");
    try {
      const rows = await listProjects();
      setProjects(rows);
      setProjectId((prev) => prev ?? (rows[0]?.id ?? null));
    } catch (e) {
      setError("Could not load your projects.");
      setProjects([]);
    } finally {
      setLoadingProjects(false);
    }
  }, []);

  const refreshSprints = useCallback(async () => {
    if (!projectId) {
      setSprints([]);
      setSprintId(null);
      return;
    }
    setLoadingSprints(true);
    try {
      const rows = await listSprints(projectId);
      setSprints(rows);
      setSprintId((prev) => {
        if (prev && rows.some((s) => s.id === prev)) return prev;
        // Prefer the active sprint, else the most recent.
        const active = rows.find((s) => s.status === "active");
        return active?.id ?? rows[0]?.id ?? null;
      });
    } catch (e) {
      setSprints([]);
      setSprintId(null);
    } finally {
      setLoadingSprints(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    refreshSprints();
  }, [refreshSprints, refreshKey]);

  const selectedProject = useMemo(
    () => projects.find((p) => p.id === projectId) || null,
    [projects, projectId]
  );
  const selectedSprint = useMemo(
    () => sprints.find((s) => s.id === sprintId) || null,
    [sprints, sprintId]
  );

  const canManage = useMemo(() => {
    if (user?.role === "admin") return true;
    const role = (selectedProject?.your_role || "").toLowerCase();
    return role.includes("lead") || role.includes("manager");
  }, [user, selectedProject]);

  const value = useMemo(
    () => ({
      user,
      projects,
      projectId,
      setProjectId: (id) => {
        setProjectId(id);
        setSprintId(null);
      },
      selectedProject,
      sprints,
      sprintId,
      setSprintId,
      selectedSprint,
      loadingProjects,
      loadingSprints,
      error,
      canManage,
      refreshKey,
      notifyChange,
      refreshSprints,
      reloadProjects: loadProjects,
    }),
    [
      user,
      projects,
      projectId,
      selectedProject,
      sprints,
      sprintId,
      selectedSprint,
      loadingProjects,
      loadingSprints,
      error,
      canManage,
      refreshKey,
      notifyChange,
      refreshSprints,
      loadProjects,
    ]
  );

  return <SprintContext.Provider value={value}>{children}</SprintContext.Provider>;
};

export default SprintContext;

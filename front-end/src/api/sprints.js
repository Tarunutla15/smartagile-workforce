import { api } from "./client";

/**
 * Thin wrappers around the `sprints` Django app (`/sprintapi/`).
 * Every call returns the parsed response body (or throws on HTTP error).
 */

export async function listProjects() {
  const { data } = await api.get("/taskapi/my-projects/");
  return Array.isArray(data) ? data : [];
}

export async function listSprints(projectId, { status } = {}) {
  const params = {};
  if (projectId) params.project = projectId;
  if (status) params.status = status;
  const { data } = await api.get("/sprintapi/sprints/", { params });
  return Array.isArray(data) ? data : [];
}

export async function createSprint(payload) {
  const { data } = await api.post("/sprintapi/sprints/", payload);
  return data;
}

export async function updateSprint(id, payload) {
  const { data } = await api.patch(`/sprintapi/sprints/${id}/`, payload);
  return data;
}

export async function deleteSprint(id) {
  await api.delete(`/sprintapi/sprints/${id}/`);
}

export async function startSprint(id) {
  const { data } = await api.post(`/sprintapi/sprints/${id}/start/`, {});
  return data;
}

export async function completeSprint(id, moveIncompleteTo) {
  const body = moveIncompleteTo ? { move_incomplete_to: moveIncompleteTo } : {};
  const { data } = await api.post(`/sprintapi/sprints/${id}/complete/`, body);
  return data;
}

export async function getSprintReport(id) {
  const { data } = await api.get(`/sprintapi/sprints/${id}/report/`);
  return data;
}

export async function getSprintBurndown(id) {
  const { data } = await api.get(`/sprintapi/sprints/${id}/burndown/`);
  return data;
}

export async function getSprintEffort(id) {
  const { data } = await api.get(`/sprintapi/sprints/${id}/effort/`);
  return data;
}

export async function getSprintBoard(id) {
  const { data } = await api.get(`/sprintapi/sprints/${id}/board/`);
  return data;
}

export async function getBacklog(projectId) {
  const { data } = await api.get("/sprintapi/backlog/", { params: { project: projectId } });
  return Array.isArray(data) ? data : [];
}

export async function getProjectMembers(projectId) {
  const { data } = await api.get(`/sprintapi/projects/${projectId}/members/`);
  return Array.isArray(data) ? data : [];
}

export async function listGroups() {
  const { data } = await api.get("/sprintapi/groups/");
  return Array.isArray(data) ? data : [];
}

export async function getGroupSummary(groupId, { days = 14 } = {}) {
  const { data } = await api.get(`/sprintapi/groups/${groupId}/summary/`, {
    params: { days },
  });
  return data;
}

export async function getOrgSummary({ days = 14 } = {}) {
  const { data } = await api.get("/sprintapi/org/summary/", { params: { days } });
  return data;
}

export async function getSprintItemEffort(id) {
  const { data } = await api.get(`/sprintapi/sprints/${id}/item-effort/`);
  return data;
}

export async function getActiveTimer() {
  const { data } = await api.get("/sprintapi/timer/active/");
  return data;
}

export async function startTimer(taskId) {
  const { data } = await api.post("/sprintapi/timer/start/", { task: taskId });
  return data;
}

export async function stopTimer() {
  const { data } = await api.post("/sprintapi/timer/stop/", {});
  return data;
}

export async function createWorkItem(payload) {
  const { data } = await api.post("/sprintapi/items/", payload);
  return data;
}

export async function updateWorkItem(id, payload) {
  const { data } = await api.patch(`/sprintapi/items/${id}/`, payload);
  return data;
}

export async function deleteWorkItem(id) {
  await api.delete(`/sprintapi/items/${id}/`);
}

export async function getWorkItemDetail(id) {
  const { data } = await api.get(`/sprintapi/items/${id}/detail/`);
  return data;
}

export async function addWorkItemComment(id, body) {
  const { data } = await api.post(`/sprintapi/items/${id}/comments/`, { body });
  return data;
}

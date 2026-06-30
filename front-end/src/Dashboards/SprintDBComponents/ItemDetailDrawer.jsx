import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Avatar,
  Box,
  Button,
  CircularProgress,
  Divider,
  Drawer,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import TimerOutlinedIcon from '@mui/icons-material/TimerOutlined';
import HistoryRoundedIcon from '@mui/icons-material/HistoryRounded';
import {
  getWorkItemDetail,
  addWorkItemComment,
  updateWorkItem,
} from '../../api/sprints';

const STATUS_OPTIONS = [
  { value: 'todo', label: 'To Do' },
  { value: 'inProgress', label: 'In Progress' },
  { value: 'done', label: 'Done' },
];
const TYPE_OPTIONS = ['story', 'task', 'bug', 'chore', 'spike'];
const PRIORITY_OPTIONS = ['none', 'low', 'medium', 'high', 'urgent'];

const STATUS_LABEL = {
  todo: 'To Do',
  inProgress: 'In Progress',
  done: 'Done',
};

function timeAgo(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return d.toLocaleDateString();
}

function initials(name) {
  if (!name) return '?';
  return name.slice(0, 2).toUpperCase();
}

/**
 * Side panel for a single work item: editable details, status-history timeline,
 * actual focus time, and a comment feed.
 */
export default function ItemDetailDrawer({
  itemId,
  open,
  onClose,
  members = [],
  onChanged,
}) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  // Local editable copy of the fields.
  const [form, setForm] = useState({});
  const [comment, setComment] = useState('');
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    if (!itemId) return;
    setLoading(true);
    setError('');
    try {
      const d = await getWorkItemDetail(itemId);
      setData(d);
      const it = d.item || {};
      setForm({
        title: it.title || '',
        description: it.description || '',
        status: it.status || 'todo',
        item_type: it.item_type || 'task',
        priority: it.priority || 'none',
        story_points: it.story_points ?? '',
        assignee_id: it.assignee?.id ?? '',
      });
    } catch (e) {
      setError('Could not load this item.');
    } finally {
      setLoading(false);
    }
  }, [itemId]);

  useEffect(() => {
    if (open && itemId) load();
  }, [open, itemId, load]);

  const item = data?.item;
  const canManage = !!data?.can_manage;
  const isOwner = !!data?.is_owner;
  const canEdit = canManage || isOwner;

  const dirty = useMemo(() => {
    if (!item) return false;
    return (
      form.title !== (item.title || '') ||
      form.description !== (item.description || '') ||
      form.status !== item.status ||
      form.item_type !== item.item_type ||
      form.priority !== (item.priority || 'none') ||
      String(form.story_points) !== String(item.story_points ?? '') ||
      String(form.assignee_id) !== String(item.assignee?.id ?? '')
    );
  }, [form, item]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSave = async () => {
    if (!item) return;
    setSaving(true);
    setError('');
    try {
      const payload = {};
      if (form.title !== (item.title || '')) payload.title = form.title.trim();
      if (form.description !== (item.description || '')) payload.description = form.description;
      if (form.item_type !== item.item_type) payload.item_type = form.item_type;
      if (form.priority !== (item.priority || 'none')) payload.priority = form.priority;
      if (String(form.story_points) !== String(item.story_points ?? '')) {
        payload.story_points = form.story_points === '' ? null : Number(form.story_points);
      }
      if (canManage && String(form.assignee_id) !== String(item.assignee?.id ?? '')) {
        payload.assignee_id = form.assignee_id === '' ? null : Number(form.assignee_id);
      }
      if (form.status !== item.status) payload.status = form.status;
      await updateWorkItem(item.id, payload);
      await load();
      onChanged && onChanged();
    } catch (e) {
      setError(e?.response?.data?.error || 'Could not save changes.');
    } finally {
      setSaving(false);
    }
  };

  const handleComment = async () => {
    const body = comment.trim();
    if (!body || !item) return;
    setPosting(true);
    try {
      await addWorkItemComment(item.id, body);
      setComment('');
      await load();
    } catch (e) {
      setError('Could not post comment.');
    } finally {
      setPosting(false);
    }
  };

  const effort = data?.effort;
  const history = data?.history || [];
  const comments = data?.comments || [];

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{ sx: { width: { xs: '100%', sm: 440 }, maxWidth: '100%' } }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Header */}
        <Box
          sx={{
            px: 2,
            py: 1.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'text.secondary' }}>
            {item ? `#${item.id}` : 'Item'} · {item ? STATUS_LABEL[item.status] || item.status : ''}
          </Typography>
          <IconButton size="small" onClick={onClose}>
            <CloseRoundedIcon fontSize="small" />
          </IconButton>
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : !item ? (
          <Box sx={{ p: 3 }}>
            <Typography color="error">{error || 'Item not found.'}</Typography>
          </Box>
        ) : (
          <Box sx={{ flex: 1, overflowY: 'auto', px: 2, py: 2 }}>
            {error && (
              <Typography variant="body2" color="error" sx={{ mb: 1.5 }}>
                {error}
              </Typography>
            )}

            {/* Title */}
            <TextField
              fullWidth
              multiline
              variant="standard"
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
              disabled={!canEdit}
              InputProps={{ sx: { fontSize: 18, fontWeight: 700 } }}
              sx={{ mb: 2 }}
            />

            {/* Meta grid */}
            <Stack spacing={1.5} sx={{ mb: 2 }}>
              <Stack direction="row" spacing={1.5}>
                <TextField
                  select
                  size="small"
                  label="Status"
                  value={form.status}
                  onChange={(e) => set('status', e.target.value)}
                  disabled={!canEdit}
                  sx={{ flex: 1 }}
                >
                  {STATUS_OPTIONS.map((o) => (
                    <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  size="small"
                  label="Type"
                  value={form.item_type}
                  onChange={(e) => set('item_type', e.target.value)}
                  disabled={!canEdit}
                  sx={{ flex: 1, textTransform: 'capitalize' }}
                >
                  {TYPE_OPTIONS.map((t) => (
                    <MenuItem key={t} value={t} sx={{ textTransform: 'capitalize' }}>{t}</MenuItem>
                  ))}
                </TextField>
              </Stack>
              <Stack direction="row" spacing={1.5}>
                <TextField
                  select
                  size="small"
                  label="Priority"
                  value={form.priority}
                  onChange={(e) => set('priority', e.target.value)}
                  disabled={!canEdit}
                  sx={{ flex: 1, textTransform: 'capitalize' }}
                >
                  {PRIORITY_OPTIONS.map((p) => (
                    <MenuItem key={p} value={p} sx={{ textTransform: 'capitalize' }}>{p}</MenuItem>
                  ))}
                </TextField>
                <TextField
                  size="small"
                  type="number"
                  label="Story points"
                  value={form.story_points}
                  onChange={(e) => set('story_points', e.target.value)}
                  disabled={!canEdit}
                  sx={{ flex: 1 }}
                />
              </Stack>
              {/* Assignee: managers can reassign; others see read-only */}
              {canManage ? (
                <TextField
                  select
                  size="small"
                  label="Assignee"
                  value={form.assignee_id}
                  onChange={(e) => set('assignee_id', e.target.value)}
                  SelectProps={{ displayEmpty: true }}
                >
                  <MenuItem value="" sx={{ fontStyle: 'italic' }}>Unassigned</MenuItem>
                  {members.map((m) => (
                    <MenuItem key={m.id} value={m.id}>{m.username}</MenuItem>
                  ))}
                </TextField>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Assignee: {item.assignee ? `@${item.assignee.username}` : 'Unassigned'}
                </Typography>
              )}
            </Stack>

            {/* Focus time */}
            {effort && (effort.focus_hours > 0 || effort.session_count > 0) && (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  p: 1.25,
                  mb: 2,
                  borderRadius: 1.5,
                  bgcolor: 'rgba(16,185,129,0.08)',
                }}
              >
                <TimerOutlinedIcon sx={{ color: '#10b981' }} />
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {effort.focus_hours}h focus · {effort.office_hours}h tracked
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {effort.session_count} timer session{effort.session_count === 1 ? '' : 's'}
                  </Typography>
                </Box>
              </Box>
            )}

            {/* Description */}
            <Typography variant="overline" color="text.secondary">Description</Typography>
            <TextField
              fullWidth
              multiline
              minRows={3}
              size="small"
              placeholder={canEdit ? 'Add a description…' : 'No description'}
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              disabled={!canEdit}
              sx={{ mt: 0.5, mb: 1 }}
            />

            {canEdit && (
              <Button
                variant="contained"
                size="small"
                onClick={handleSave}
                disabled={!dirty || saving}
                sx={{ mb: 2 }}
              >
                {saving ? 'Saving…' : 'Save changes'}
              </Button>
            )}

            <Divider sx={{ my: 2 }} />

            {/* Status history timeline */}
            <Stack direction="row" alignItems="center" spacing={0.75} sx={{ mb: 1 }}>
              <HistoryRoundedIcon fontSize="small" sx={{ color: 'text.secondary' }} />
              <Typography variant="overline" color="text.secondary">Activity</Typography>
            </Stack>
            {history.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                No status changes recorded yet.
              </Typography>
            ) : (
              <Box sx={{ pl: 1, mb: 2 }}>
                {history.map((h) => (
                  <Box key={h.id} sx={{ position: 'relative', pl: 2, pb: 1.5 }}>
                    <Box
                      sx={{
                        position: 'absolute',
                        left: 0,
                        top: 5,
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        bgcolor: h.to_status === 'done' ? '#10b981' : '#6366f1',
                      }}
                    />
                    <Typography variant="body2">
                      <b>{h.changed_by?.username || 'Someone'}</b>{' '}
                      moved {h.from_status ? STATUS_LABEL[h.from_status] || h.from_status : 'new'} →{' '}
                      <b>{STATUS_LABEL[h.to_status] || h.to_status}</b>
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {timeAgo(h.changed_at)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            )}

            <Divider sx={{ my: 2 }} />

            {/* Comments */}
            <Typography variant="overline" color="text.secondary">
              Comments ({comments.length})
            </Typography>
            <Stack spacing={1.5} sx={{ mt: 1, mb: 1.5 }}>
              {comments.map((c) => (
                <Stack key={c.id} direction="row" spacing={1.25} alignItems="flex-start">
                  <Avatar sx={{ width: 28, height: 28, fontSize: 12, bgcolor: '#6366f1' }}>
                    {initials(c.author?.username)}
                  </Avatar>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2">
                      <b>{c.author?.username || 'Unknown'}</b>{' '}
                      <Typography component="span" variant="caption" color="text.secondary">
                        {timeAgo(c.created_at)}
                      </Typography>
                    </Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {c.body}
                    </Typography>
                  </Box>
                </Stack>
              ))}
              {comments.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  No comments yet. Start the discussion.
                </Typography>
              )}
            </Stack>
          </Box>
        )}

        {/* Comment composer (pinned to bottom) */}
        {item && !loading && (
          <Box sx={{ p: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
            <Stack direction="row" spacing={1} alignItems="flex-end">
              <TextField
                fullWidth
                size="small"
                multiline
                maxRows={4}
                placeholder="Write a comment…"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleComment();
                }}
              />
              <Tooltip title="Comment (Ctrl/⌘+Enter)">
                <span>
                  <IconButton
                    color="primary"
                    onClick={handleComment}
                    disabled={!comment.trim() || posting}
                  >
                    <SendRoundedIcon />
                  </IconButton>
                </span>
              </Tooltip>
            </Stack>
          </Box>
        )}
      </Box>
    </Drawer>
  );
}

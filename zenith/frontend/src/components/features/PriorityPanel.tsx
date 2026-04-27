import { useMemo, useState, type Dispatch, type SetStateAction } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { GlassButton } from '../ui/GlassButton';
import { GlassInput, GlassTextarea } from '../ui/GlassInput';
import { useAuth } from '../../contexts/AuthContext';
import { useChat } from '../../contexts/ChatContext';
import {
  calendarAPI,
  gmailAPI,
  priorityAPI,
  tasksAPI,
  type EmailActionItem,
  type PriorityFeedItem,
} from '../../lib/api';
import {
  AlertCircle,
  Calendar,
  CheckSquare,
  ChevronRight,
  ClipboardList,
  Mail,
  MessageSquare,
  RefreshCw,
  Sparkles,
  X,
} from 'lucide-react';

type ReplyEditorState = {
  kind: 'reply';
  item: EmailActionItem;
  to: string;
  subject: string;
  body: string;
};

type TaskEditorState = {
  kind: 'task';
  item: EmailActionItem;
  title: string;
  description: string;
  due: string;
};

type MeetingEditorState = {
  kind: 'meeting';
  item: EmailActionItem;
  title: string;
  description: string;
  attendees: string;
  start: string;
  end: string;
};

type ActionEditorState = ReplyEditorState | TaskEditorState | MeetingEditorState;

function parseEmailAddress(value: string) {
  const bracketMatch = value.match(/<([^>]+)>/);
  if (bracketMatch?.[1]) {
    return bracketMatch[1].trim();
  }

  const plainMatch = value.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  return plainMatch?.[0] ?? '';
}

function parseEmailList(value: string) {
  return value
    .split(/[,\n]/)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function toDateTimeInputValue(value?: string | null) {
  if (!value) {
    return '';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }

  const offsetMs = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function getDefaultMeetingWindow() {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  start.setHours(start.getHours() + 1);

  const end = new Date(start.getTime() + 30 * 60 * 1000);
  return {
    start: toDateTimeInputValue(start.toISOString()),
    end: toDateTimeInputValue(end.toISOString()),
  };
}

function actionBadgeClasses(item: PriorityFeedItem) {
  if (item.type === 'meeting_prep') {
    return 'bg-amber-500/15 text-amber-300 border-amber-400/30';
  }

  if (item.action_type === 'reply') {
    return 'bg-sky-500/15 text-sky-300 border-sky-400/30';
  }
  if (item.action_type === 'task') {
    return 'bg-emerald-500/15 text-emerald-300 border-emerald-400/30';
  }
  if (item.action_type === 'meeting') {
    return 'bg-orange-500/15 text-orange-300 border-orange-400/30';
  }
  return 'bg-white/10 text-white/60 border-white/10';
}

function actionLabel(item: PriorityFeedItem) {
  if (item.type === 'meeting_prep') {
    return item.status === 'ready' ? 'Prep Ready' : 'Needs Clarification';
  }

  if (item.action_type === 'reply') {
    return 'Reply';
  }
  if (item.action_type === 'task') {
    return 'Task';
  }
  if (item.action_type === 'meeting') {
    return 'Meeting';
  }
  return 'Ignore';
}

function createEditorForItem(item: EmailActionItem, uiAction: string): ActionEditorState | null {
  if (item.action_type === 'reply') {
    return {
      kind: 'reply',
      item,
      to: parseEmailAddress(item.from),
      subject: item.title.toLowerCase().startsWith('re:') ? item.title : `Re: ${item.title}`,
      body: item.draft_reply ?? '',
    };
  }

  if (item.action_type === 'task' && item.task_payload) {
    return {
      kind: 'task',
      item,
      title: item.task_payload.title,
      description: item.task_payload.description ?? '',
      due: toDateTimeInputValue(item.task_payload.due),
    };
  }

  if (item.action_type === 'meeting' && item.meeting_payload) {
    const defaultWindow = getDefaultMeetingWindow();
    const senderEmail = parseEmailAddress(item.from);
    const attendees = item.meeting_payload.attendees.length > 0
      ? item.meeting_payload.attendees.join(', ')
      : senderEmail;

    return {
      kind: 'meeting',
      item,
      title: item.meeting_payload.title || item.title,
      description: item.meeting_payload.description ?? '',
      attendees,
      start: toDateTimeInputValue(item.meeting_payload.start_time) || defaultWindow.start,
      end: toDateTimeInputValue(item.meeting_payload.end_time) || defaultWindow.end,
    };
  }

  if (uiAction === 'Ignore') {
    return null;
  }

  return null;
}

function ActionEditorModal({
  editor,
  setEditor,
  onSubmit,
  isLoading,
}: {
  editor: ActionEditorState | null;
  setEditor: Dispatch<SetStateAction<ActionEditorState | null>>;
  onSubmit: () => void;
  isLoading: boolean;
}) {
  if (!editor) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={() => setEditor(null)}
      >
        <motion.div
          initial={{ scale: 0.96, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.96, opacity: 0 }}
          onClick={(event) => event.stopPropagation()}
          className="w-full max-w-xl"
        >
          <GlassPanel variant="strong" className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  {editor.kind === 'reply' ? 'Reply Draft' : editor.kind === 'task' ? 'Task Draft' : 'Meeting Draft'}
                </h3>
                <p className="text-xs text-white/40 mt-1">{editor.item.title}</p>
              </div>
              <button
                type="button"
                onClick={() => setEditor(null)}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                aria-label="Close editor"
              >
                <X className="w-5 h-5 text-white/60" />
              </button>
            </div>

            {editor.kind === 'reply' && (
              <div className="space-y-3">
                <GlassInput
                  label="Recipient"
                  value={editor.to}
                  onChange={(event) => setEditor((current) => current && current.kind === 'reply'
                    ? { ...current, to: event.target.value }
                    : current)}
                />
                <GlassInput
                  label="Subject"
                  value={editor.subject}
                  onChange={(event) => setEditor((current) => current && current.kind === 'reply'
                    ? { ...current, subject: event.target.value }
                    : current)}
                />
                <GlassTextarea
                  label="Reply"
                  rows={8}
                  value={editor.body}
                  onChange={(event) => setEditor((current) => current && current.kind === 'reply'
                    ? { ...current, body: event.target.value }
                    : current)}
                />
              </div>
            )}

            {editor.kind === 'task' && (
              <div className="space-y-3">
                <GlassInput
                  label="Task Title"
                  value={editor.title}
                  onChange={(event) => setEditor((current) => current && current.kind === 'task'
                    ? { ...current, title: event.target.value }
                    : current)}
                />
                <GlassTextarea
                  label="Description"
                  rows={5}
                  value={editor.description}
                  onChange={(event) => setEditor((current) => current && current.kind === 'task'
                    ? { ...current, description: event.target.value }
                    : current)}
                />
                <GlassInput
                  label="Due"
                  type="datetime-local"
                  value={editor.due}
                  onChange={(event) => setEditor((current) => current && current.kind === 'task'
                    ? { ...current, due: event.target.value }
                    : current)}
                />
              </div>
            )}

            {editor.kind === 'meeting' && (
              <div className="space-y-3">
                <GlassInput
                  label="Meeting Title"
                  value={editor.title}
                  onChange={(event) => setEditor((current) => current && current.kind === 'meeting'
                    ? { ...current, title: event.target.value }
                    : current)}
                />
                <GlassTextarea
                  label="Description"
                  rows={4}
                  value={editor.description}
                  onChange={(event) => setEditor((current) => current && current.kind === 'meeting'
                    ? { ...current, description: event.target.value }
                    : current)}
                />
                <GlassInput
                  label="Attendees"
                  value={editor.attendees}
                  onChange={(event) => setEditor((current) => current && current.kind === 'meeting'
                    ? { ...current, attendees: event.target.value }
                    : current)}
                  placeholder="person@example.com, another@example.com"
                />
                <div className="grid grid-cols-2 gap-3">
                  <GlassInput
                    label="Start"
                    type="datetime-local"
                    value={editor.start}
                    onChange={(event) => setEditor((current) => current && current.kind === 'meeting'
                      ? { ...current, start: event.target.value }
                      : current)}
                  />
                  <GlassInput
                    label="End"
                    type="datetime-local"
                    value={editor.end}
                    onChange={(event) => setEditor((current) => current && current.kind === 'meeting'
                      ? { ...current, end: event.target.value }
                      : current)}
                  />
                </div>
              </div>
            )}

            <div className="flex gap-2">
              <GlassButton
                variant="ghost"
                size="md"
                className="flex-1"
                onClick={() => setEditor(null)}
              >
                Cancel
              </GlassButton>
              <GlassButton
                variant="primary"
                size="md"
                className="flex-1"
                isLoading={isLoading}
                onClick={onSubmit}
              >
                {editor.kind === 'reply' ? 'Send Reply' : editor.kind === 'task' ? 'Add Task' : 'Schedule Meeting'}
              </GlassButton>
            </div>
          </GlassPanel>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export function PriorityPanel() {
  const { isAuthenticated } = useAuth();
  const { sendMessage } = useChat();
  const queryClient = useQueryClient();
  const [isExpanded, setIsExpanded] = useState(true);
  const [dismissedIds, setDismissedIds] = useState<string[]>([]);
  const [editor, setEditor] = useState<ActionEditorState | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['priority-feed'],
    queryFn: () => priorityAPI.getFeed(),
    enabled: isAuthenticated,
    refetchInterval: isExpanded ? 60000 : false,
  });

  const items = useMemo(
    () => (data?.items ?? []).filter((item) => !dismissedIds.includes(item.id)),
    [data?.items, dismissedIds],
  );

  const actionMutation = useMutation({
    mutationFn: async (currentEditor: ActionEditorState) => {
      if (currentEditor.kind === 'reply') {
        const recipient = currentEditor.to.trim();
        if (!parseEmailAddress(recipient)) {
          throw new Error('Add a valid recipient email address before sending.');
        }

        await gmailAPI.sendEmail({
          to: [recipient],
          subject: currentEditor.subject.trim(),
          body: currentEditor.body.trim(),
        });

        return {
          message: 'Reply sent.',
          invalidateKeys: [['gmail', 'messages'], ['priority-feed']] as Array<readonly unknown[]>,
        };
      }

      if (currentEditor.kind === 'task') {
        const preview = await tasksAPI.editTaskPreview({
          title: currentEditor.title.trim(),
          description: currentEditor.description.trim() || undefined,
          due: currentEditor.due ? new Date(currentEditor.due).toISOString() : undefined,
        });

        await tasksAPI.addTask({
          title: preview.task_payload.title,
          notes: preview.task_payload.description ?? undefined,
          due_date: preview.task_payload.due ?? undefined,
        });

        return {
          message: 'Task added.',
          invalidateKeys: [['tasks'], ['priority-feed']] as Array<readonly unknown[]>,
        };
      }

      const startIso = new Date(currentEditor.start).toISOString();
      const endIso = new Date(currentEditor.end).toISOString();
      if (new Date(endIso).getTime() <= new Date(startIso).getTime()) {
        throw new Error('Meeting end time must be after the start time.');
      }

      await calendarAPI.createEventWithMeet({
        summary: currentEditor.title.trim(),
        description: currentEditor.description.trim() || undefined,
        attendees: parseEmailList(currentEditor.attendees),
        start_time: startIso,
        end_time: endIso,
      });

      return {
        message: 'Meeting scheduled.',
        invalidateKeys: [['calendar', 'events'], ['priority-feed']] as Array<readonly unknown[]>,
      };
    },
    onSuccess: async (result, currentEditor) => {
      setNotice(result.message);
      setDismissedIds((prev) => [...prev, currentEditor.item.id]);
      setEditor(null);
      await Promise.all(result.invalidateKeys.map((queryKey) => queryClient.invalidateQueries({ queryKey })));
    },
  });

  if (!isAuthenticated) {
    return null;
  }

  return (
    <>
      <GlassPanel className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div
            className="flex items-center gap-2 cursor-pointer flex-1"
            onClick={() => setIsExpanded((prev) => !prev)}
          >
            <ClipboardList className="w-5 h-5 text-neutral-400" />
            <h3 className="text-sm font-semibold text-white/90">Priority Area</h3>
            <span className="text-xs text-white/40">({items.length})</span>
            <motion.div
              animate={{ rotate: isExpanded ? 90 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronRight className="w-4 h-4 text-white/40" />
            </motion.div>
          </div>

          <button
            type="button"
            onClick={() => refetch()}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            title="Refresh priority area"
          >
            <RefreshCw className={`w-4 h-4 text-white/50 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {!isExpanded && (
          <p className="text-xs text-white/50">Top inbox actions and meeting prep suggestions are tucked in here.</p>
        )}

        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            className="space-y-3 overflow-hidden"
          >
            {notice && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
                {notice}
              </div>
            )}

            {isLoading && (
              <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-4 text-sm text-white/50">
                Building your priority feed...
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-4 text-sm text-red-300">
                Unable to load the priority area right now.
              </div>
            )}

            {!isLoading && !error && items.length === 0 && (
              <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-4 text-sm text-white/50">
                Nothing urgent right now. You can refresh later if your inbox changes.
              </div>
            )}

            {items.map((item) => (
              <div key={item.id} className="rounded-xl border border-white/10 bg-white/5 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${actionBadgeClasses(item)}`}>
                        {actionLabel(item)}
                      </span>
                      <p className="text-sm font-medium text-white/90 truncate">{item.title}</p>
                    </div>

                    {item.type === 'email_action' && (
                      <>
                        <p className="text-xs text-white/50">{item.from}</p>
                        <p className="text-sm text-white/75 leading-relaxed">{item.summary}</p>
                        <p className="text-xs text-white/40">{item.reason}</p>
                      </>
                    )}

                    {item.type === 'meeting_prep' && (
                      <>
                        <p className="text-sm text-white/75 leading-relaxed">{item.summary}</p>
                        <p className="text-xs text-white/40">{item.reason}</p>
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                          <div className="rounded-lg border border-white/10 bg-black/10 p-3">
                            <div className="flex items-center gap-2 mb-2">
                              <AlertCircle className="w-4 h-4 text-amber-300" />
                              <p className="text-xs font-medium text-white/70">Risks</p>
                            </div>
                            <div className="space-y-1">
                              {item.prep.risks.slice(0, 3).map((risk) => (
                                <p key={risk} className="text-xs text-white/55">• {risk}</p>
                              ))}
                              {item.prep.risks.length === 0 && (
                                <p className="text-xs text-white/40">No immediate risks detected.</p>
                              )}
                            </div>
                          </div>
                          <div className="rounded-lg border border-white/10 bg-black/10 p-3">
                            <div className="flex items-center gap-2 mb-2">
                              <Sparkles className="w-4 h-4 text-sky-300" />
                              <p className="text-xs font-medium text-white/70">Talking Points</p>
                            </div>
                            <div className="space-y-1">
                              {item.prep.talking_points.slice(0, 3).map((point) => (
                                <p key={point} className="text-xs text-white/55">• {point}</p>
                              ))}
                              {item.prep.talking_points.length === 0 && (
                                <p className="text-xs text-white/40">No talking points suggested yet.</p>
                              )}
                            </div>
                          </div>
                        </div>
                        <GlassButton
                          variant="ghost"
                          size="sm"
                          className="w-full justify-center"
                          onClick={() => sendMessage(`Help me prepare for "${item.title}" and expand the key talking points and risks.`)}
                        >
                          <MessageSquare className="w-4 h-4 mr-2" />
                          Open in Chat
                        </GlassButton>
                      </>
                    )}
                  </div>

                  <div className="flex-shrink-0">
                    {item.type === 'email_action' && item.action_type === 'reply' && (
                      <Mail className="w-5 h-5 text-sky-300" />
                    )}
                    {item.type === 'email_action' && item.action_type === 'task' && (
                      <CheckSquare className="w-5 h-5 text-emerald-300" />
                    )}
                    {item.type === 'email_action' && item.action_type === 'meeting' && (
                      <Calendar className="w-5 h-5 text-orange-300" />
                    )}
                    {item.type === 'meeting_prep' && (
                      <Sparkles className="w-5 h-5 text-amber-300" />
                    )}
                  </div>
                </div>

                {item.type === 'email_action' && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {item.ui_actions.map((uiAction) => {
                      if (uiAction === 'Ignore' || uiAction === 'Ignore only') {
                        return (
                          <button
                            key={uiAction}
                            type="button"
                            onClick={() => {
                              setNotice('Dismissed from the priority area.');
                              setDismissedIds((prev) => [...prev, item.id]);
                            }}
                            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-white/60 hover:bg-white/10 transition-colors"
                          >
                            {uiAction}
                          </button>
                        );
                      }

                      if (uiAction === 'Autoprep') {
                        return (
                          <button
                            key={uiAction}
                            type="button"
                            onClick={() => sendMessage(`Prepare me for a meeting related to "${item.title}" using the surrounding email context.`)}
                            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-white/80 hover:bg-white/10 transition-colors"
                          >
                            {uiAction}
                          </button>
                        );
                      }

                      return (
                        <button
                          key={uiAction}
                          type="button"
                          onClick={() => {
                            setNotice(null);
                            setEditor(createEditorForItem(item, uiAction));
                          }}
                          className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-white/80 hover:bg-white/10 transition-colors"
                        >
                          {uiAction}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </motion.div>
        )}
      </GlassPanel>

      <ActionEditorModal
        editor={editor}
        setEditor={setEditor}
        onSubmit={() => {
          if (editor) {
            setNotice(null);
            actionMutation.mutate(editor);
          }
        }}
        isLoading={actionMutation.isPending}
      />

      {actionMutation.isError && (
        <div className="fixed bottom-4 right-4 z-50 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {actionMutation.error instanceof Error ? actionMutation.error.message : 'Unable to complete that action.'}
        </div>
      )}
    </>
  );
}

export default PriorityPanel;

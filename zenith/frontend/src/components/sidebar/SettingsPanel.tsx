import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { GlassToggle } from '../ui/GlassToggle';
import { GlassButton } from '../ui/GlassButton';
import { GlassInput, GlassTextarea } from '../ui/GlassInput';
import { useAuth } from '../../contexts/AuthContext';
import { preferencesAPI, type UserPreferences } from '../../lib/api';
import {
  Settings,
  X,
  Moon,
  Sun,
  Volume2,
  RefreshCw,
  Bell,
  Clock3,
  Mail,
  Users,
  SlidersHorizontal,
} from 'lucide-react';

/** Workspace connection toggles (UI state; real OAuth is account-level). */
export interface Connection {
  id: string;
  name: string;
  icon: ReactNode;
  enabled: boolean;
}

export interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  isDarkMode: boolean;
  onThemeChange: (isDark: boolean) => void;
  speakMode: boolean;
  onSpeakModeChange: (enabled: boolean) => void;
  connections: Connection[];
  onConnectionToggle: (id: string, enabled: boolean) => void;
}

const DEFAULT_PREFERENCES: UserPreferences = {
  preferred_meeting_times: [],
  frequent_contacts: [],
  email_tone: 'professional',
  custom_rules: [],
  working_hours: {
    start: '09:00',
    end: '17:00',
    days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
  },
  timezone: 'Etc/UTC',
  notification_preferences: {
    daily_briefing: true,
    email_alerts: true,
    task_reminders: true,
  },
};

const EMAIL_TONE_OPTIONS = ['professional', 'formal', 'casual'] as const;
const MEETING_TIME_OPTIONS = [
  { label: 'Morning', value: '09:00-12:00' },
  { label: 'Midday', value: '12:00-14:00' },
  { label: 'Afternoon', value: '14:00-17:00' },
  { label: 'Evening', value: '17:00-19:00' },
];

function normalizePreferences(preferences?: Partial<UserPreferences>): UserPreferences {
  return {
    ...DEFAULT_PREFERENCES,
    ...preferences,
    preferred_meeting_times: preferences?.preferred_meeting_times ?? DEFAULT_PREFERENCES.preferred_meeting_times,
    frequent_contacts: preferences?.frequent_contacts ?? DEFAULT_PREFERENCES.frequent_contacts,
    custom_rules: preferences?.custom_rules ?? DEFAULT_PREFERENCES.custom_rules,
    working_hours: {
      ...DEFAULT_PREFERENCES.working_hours,
      ...preferences?.working_hours,
      days: preferences?.working_hours?.days ?? DEFAULT_PREFERENCES.working_hours.days,
    },
    notification_preferences: {
      ...DEFAULT_PREFERENCES.notification_preferences,
      ...preferences?.notification_preferences,
    },
  };
}

function parseListInput(value: string) {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

/**
 * Slide-over settings surface kept separate from `Sidebar` so the shell stays
 * focused on navigation and the drawer can evolve independently.
 */
export function SettingsPanel({
  isOpen,
  onClose,
  isDarkMode,
  onThemeChange,
  speakMode,
  onSpeakModeChange,
  connections,
  onConnectionToggle,
}: SettingsPanelProps) {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<UserPreferences>(DEFAULT_PREFERENCES);
  const [frequentContactsInput, setFrequentContactsInput] = useState('');
  const [customRulesInput, setCustomRulesInput] = useState('');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['preferences'],
    queryFn: () => preferencesAPI.getPreferences(),
    enabled: isOpen && isAuthenticated,
  });

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const hydrated = normalizePreferences(data?.preferences);
    setDraft(hydrated);
    setFrequentContactsInput(hydrated.frequent_contacts.join(', '));
    setCustomRulesInput(hydrated.custom_rules.join('\n'));
  }, [data?.preferences, isOpen]);

  const selectedMeetingSlots = useMemo(
    () => new Set(draft.preferred_meeting_times),
    [draft.preferred_meeting_times],
  );

  const updatePreferencesMutation = useMutation({
    mutationFn: async () => preferencesAPI.updatePreferences({
      email_tone: draft.email_tone,
      preferred_meeting_times: draft.preferred_meeting_times,
      frequent_contacts: parseListInput(frequentContactsInput),
      custom_rules: parseListInput(customRulesInput),
      working_hours: draft.working_hours,
      timezone: draft.timezone,
      notification_preferences: draft.notification_preferences,
    }),
    onSuccess: async (result) => {
      const normalized = normalizePreferences(result.preferences);
      setDraft(normalized);
      setFrequentContactsInput(normalized.frequent_contacts.join(', '));
      setCustomRulesInput(normalized.custom_rules.join('\n'));
      await queryClient.invalidateQueries({ queryKey: ['preferences'] });
      await queryClient.invalidateQueries({ queryKey: ['priority-feed'] });
    },
  });

  const toggleMeetingWindow = (value: string) => {
    setDraft((prev) => ({
      ...prev,
      preferred_meeting_times: prev.preferred_meeting_times.includes(value)
        ? prev.preferred_meeting_times.filter((slot) => slot !== value)
        : [...prev.preferred_meeting_times, value],
    }));
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
            aria-hidden
          />

          <motion.div
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -300, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed left-4 top-4 bottom-4 w-[24rem] z-50"
            role="dialog"
            aria-modal="true"
            aria-labelledby="settings-panel-title"
          >
            <GlassPanel variant="strong" className="h-full flex flex-col">
              <div className="p-4 border-b border-white/10 flex items-center justify-between">
                <h2 id="settings-panel-title" className="text-lg font-semibold text-white flex items-center gap-2">
                  <Settings className="w-5 h-5" aria-hidden />
                  Settings
                </h2>
                <button
                  type="button"
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400/60"
                  aria-label="Close settings"
                >
                  <X className="w-5 h-5 text-white/60" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-6">
                <div>
                  <h3 className="text-sm font-medium text-white/70 mb-3">Appearance</h3>
                  <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
                    <div className="flex items-center gap-3">
                      {isDarkMode ? (
                        <Moon className="w-5 h-5 text-neutral-400" aria-hidden />
                      ) : (
                        <Sun className="w-5 h-5 text-yellow-400" aria-hidden />
                      )}
                      <span className="text-sm text-white/80">
                        {isDarkMode ? 'Dark Mode' : 'Light Mode'}
                      </span>
                    </div>
                    <GlassToggle enabled={isDarkMode} onChange={onThemeChange} />
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-medium text-white/70 mb-3">Voice</h3>
                  <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
                    <div className="flex items-center gap-3">
                      <Volume2 className="w-5 h-5 text-neutral-400" aria-hidden />
                      <div>
                        <span className="text-sm text-white/80">Speak Mode</span>
                        <p className="text-xs text-white/40">AI reads messages aloud</p>
                      </div>
                    </div>
                    <GlassToggle enabled={speakMode} onChange={onSpeakModeChange} />
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-white/70">User Preferences</h3>
                      <p className="text-xs text-white/40 mt-1">These preferences shape briefing, planning, and the new priority area.</p>
                    </div>
                    {isAuthenticated && (
                      <motion.button
                        type="button"
                        whileHover={{ rotate: 180 }}
                        transition={{ duration: 0.3 }}
                        onClick={() => refetch()}
                        className="p-1 text-white/40 hover:text-white/70 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400/60 rounded"
                        title="Refresh preferences"
                        aria-label="Refresh preferences"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </motion.button>
                    )}
                  </div>

                  {!isAuthenticated && (
                    <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-sm text-white/60">
                      Sign in to edit and save your personal preferences.
                    </div>
                  )}

                  {isAuthenticated && (
                    <>
                      {isLoading && (
                        <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-sm text-white/50">
                          Loading saved preferences...
                        </div>
                      )}

                      {error && (
                        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-sm text-red-300">
                          Unable to load saved preferences right now.
                        </div>
                      )}

                      <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-3">
                        <div className="flex items-start gap-3">
                          <SlidersHorizontal className="w-5 h-5 text-neutral-400 mt-0.5" />
                          <div className="flex-1">
                            <p className="text-sm text-white/85 font-medium">Priority Focus</p>
                            <p className="text-xs text-white/40 mt-1">One rule per line for how Zenith should weigh your work.</p>
                          </div>
                        </div>
                        <GlassTextarea
                          rows={4}
                          value={customRulesInput}
                          onChange={(event) => setCustomRulesInput(event.target.value)}
                          placeholder="Keep deep work in the afternoon&#10;Flag anything blocking client delivery"
                        />
                      </div>

                      <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-3">
                        <div className="flex items-start gap-3">
                          <Mail className="w-5 h-5 text-neutral-400 mt-0.5" />
                          <div className="flex-1">
                            <p className="text-sm text-white/85 font-medium">Email Tone</p>
                            <p className="text-xs text-white/40 mt-1">Applies to reply drafting and communication suggestions.</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-2">
                          {EMAIL_TONE_OPTIONS.map((option) => {
                            const isSelected = draft.email_tone === option;
                            return (
                              <button
                                key={option}
                                type="button"
                                onClick={() => setDraft((prev) => ({ ...prev, email_tone: option }))}
                                className={`rounded-xl border px-3 py-2 text-sm capitalize transition-colors ${
                                  isSelected
                                    ? 'border-neutral-400/50 bg-neutral-500/20 text-white'
                                    : 'border-white/10 bg-white/5 text-white/60 hover:bg-white/10'
                                }`}
                              >
                                {option}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-3">
                        <div className="flex items-start gap-3">
                          <Clock3 className="w-5 h-5 text-neutral-400 mt-0.5" />
                          <div className="flex-1">
                            <p className="text-sm text-white/85 font-medium">Meeting Windows</p>
                            <p className="text-xs text-white/40 mt-1">Choose the time blocks Zenith should prefer when planning meetings.</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          {MEETING_TIME_OPTIONS.map((slot) => {
                            const isSelected = selectedMeetingSlots.has(slot.value);
                            return (
                              <button
                                key={slot.value}
                                type="button"
                                onClick={() => toggleMeetingWindow(slot.value)}
                                className={`rounded-xl border px-3 py-2 text-sm transition-colors ${
                                  isSelected
                                    ? 'border-neutral-400/50 bg-neutral-500/20 text-white'
                                    : 'border-white/10 bg-white/5 text-white/60 hover:bg-white/10'
                                }`}
                              >
                                {slot.label}
                              </button>
                            );
                          })}
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <GlassInput
                            label="Workday Start"
                            type="time"
                            value={draft.working_hours.start}
                            onChange={(event) => setDraft((prev) => ({
                              ...prev,
                              working_hours: {
                                ...prev.working_hours,
                                start: event.target.value,
                              },
                            }))}
                          />
                          <GlassInput
                            label="Workday End"
                            type="time"
                            value={draft.working_hours.end}
                            onChange={(event) => setDraft((prev) => ({
                              ...prev,
                              working_hours: {
                                ...prev.working_hours,
                                end: event.target.value,
                              },
                            }))}
                          />
                        </div>
                        <GlassInput
                          label="Timezone"
                          value={draft.timezone}
                          onChange={(event) => setDraft((prev) => ({ ...prev, timezone: event.target.value }))}
                          placeholder="Asia/Calcutta"
                        />
                      </div>

                      <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-3">
                        <div className="flex items-start gap-3">
                          <Users className="w-5 h-5 text-neutral-400 mt-0.5" />
                          <div className="flex-1">
                            <p className="text-sm text-white/85 font-medium">Frequent Contacts</p>
                            <p className="text-xs text-white/40 mt-1">Comma-separated addresses Zenith should recognize quickly.</p>
                          </div>
                        </div>
                        <GlassTextarea
                          rows={3}
                          value={frequentContactsInput}
                          onChange={(event) => setFrequentContactsInput(event.target.value)}
                          placeholder="manager@company.com, recruiter@example.com"
                        />
                      </div>

                      <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-3">
                        <div className="flex items-start gap-3">
                          <Bell className="w-5 h-5 text-neutral-400 mt-0.5" />
                          <div className="flex-1">
                            <p className="text-sm text-white/85 font-medium">Notification Preferences</p>
                            <p className="text-xs text-white/40 mt-1">Controls what Zenith treats as worth surfacing proactively.</p>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between rounded-xl bg-white/5 border border-white/10 p-3">
                            <div>
                              <p className="text-sm text-white/80">Daily Briefing</p>
                              <p className="text-xs text-white/40">Morning catch-up and proactive summary</p>
                            </div>
                            <GlassToggle
                              enabled={draft.notification_preferences.daily_briefing}
                              onChange={(enabled) => setDraft((prev) => ({
                                ...prev,
                                notification_preferences: {
                                  ...prev.notification_preferences,
                                  daily_briefing: enabled,
                                },
                              }))}
                            />
                          </div>
                          <div className="flex items-center justify-between rounded-xl bg-white/5 border border-white/10 p-3">
                            <div>
                              <p className="text-sm text-white/80">Email Alerts</p>
                              <p className="text-xs text-white/40">Highlight inbox items that need fast attention</p>
                            </div>
                            <GlassToggle
                              enabled={draft.notification_preferences.email_alerts}
                              onChange={(enabled) => setDraft((prev) => ({
                                ...prev,
                                notification_preferences: {
                                  ...prev.notification_preferences,
                                  email_alerts: enabled,
                                },
                              }))}
                            />
                          </div>
                          <div className="flex items-center justify-between rounded-xl bg-white/5 border border-white/10 p-3">
                            <div>
                              <p className="text-sm text-white/80">Task Reminders</p>
                              <p className="text-xs text-white/40">Bias planning toward deadlines and incomplete work</p>
                            </div>
                            <GlassToggle
                              enabled={draft.notification_preferences.task_reminders}
                              onChange={(enabled) => setDraft((prev) => ({
                                ...prev,
                                notification_preferences: {
                                  ...prev.notification_preferences,
                                  task_reminders: enabled,
                                },
                              }))}
                            />
                          </div>
                        </div>
                      </div>

                      <GlassButton
                        variant="primary"
                        size="md"
                        className="w-full"
                        isLoading={updatePreferencesMutation.isPending}
                        onClick={() => updatePreferencesMutation.mutate()}
                      >
                        Save Preferences
                      </GlassButton>

                      {updatePreferencesMutation.isSuccess && (
                        <div className="text-xs text-green-300 text-center">Preferences saved.</div>
                      )}
                      {updatePreferencesMutation.isError && (
                        <div className="text-xs text-red-300 text-center">Unable to save preferences right now.</div>
                      )}
                    </>
                  )}
                </div>

                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-medium text-white/70">Connections</h3>
                    <motion.button
                      type="button"
                      whileHover={{ rotate: 180 }}
                      transition={{ duration: 0.3 }}
                      className="p-1 text-white/40 hover:text-white/70 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400/60 rounded"
                      title="Refresh connections"
                      aria-label="Refresh connections"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </motion.button>
                  </div>

                  <div className="space-y-2">
                    {connections.map((connection, index) => (
                      <motion.div
                        key={connection.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={`
                            p-2 rounded-lg
                            ${isAuthenticated && connection.enabled
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-white/10 text-white/40'
                            }
                          `}
                          >
                            {connection.icon}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white/90">{connection.name}</p>
                            <p className="text-xs text-white/40">
                              {isAuthenticated
                                ? connection.enabled
                                  ? 'Enabled'
                                  : 'Disabled'
                                : 'Sign in to connect'}
                            </p>
                          </div>
                        </div>
                        <GlassToggle
                          enabled={connection.enabled}
                          onChange={(enabled) => onConnectionToggle(connection.id, enabled)}
                          disabled={!isAuthenticated}
                        />
                      </motion.div>
                    ))}
                  </div>
                </div>
              </div>
            </GlassPanel>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

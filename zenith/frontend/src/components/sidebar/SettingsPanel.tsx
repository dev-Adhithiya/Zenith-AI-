import type { ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { GlassToggle } from '../ui/GlassToggle';
import { useAuth } from '../../contexts/AuthContext';
import { Settings, X, Moon, Sun, Volume2, RefreshCw } from 'lucide-react';

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
            className="fixed left-4 top-4 bottom-4 w-80 z-50"
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

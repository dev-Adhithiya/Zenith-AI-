import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { GlassButton } from '../ui/GlassButton';
import { GlassToggle } from '../ui/GlassToggle';
import { useAuth } from '../../contexts/AuthContext';
import { useChat } from '../../contexts/ChatContext';
import { 
  Sparkles, 
  LogOut, 
  Settings, 
  MessageSquarePlus,
  Moon,
  Sun,
  User,
  X,
  Mail,
  Calendar,
  CheckSquare,
  StickyNote,
  RefreshCw,
  PanelLeftClose,
  PanelLeft
} from 'lucide-react';

interface Connection {
  id: string;
  name: string;
  icon: React.ReactNode;
  enabled: boolean;
}

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  isDarkMode: boolean;
  onThemeChange: (isDark: boolean) => void;
  connections: Connection[];
  onConnectionToggle: (id: string, enabled: boolean) => void;
}

function SettingsPanel({ isOpen, onClose, isDarkMode, onThemeChange, connections, onConnectionToggle }: SettingsPanelProps) {
  const { isAuthenticated } = useAuth();

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          />
          
          {/* Panel */}
          <motion.div
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -300, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed left-4 top-4 bottom-4 w-80 z-50"
          >
            <GlassPanel variant="strong" className="h-full flex flex-col">
              {/* Header */}
              <div className="p-4 border-b border-white/10 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  Settings
                </h2>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X className="w-5 h-5 text-white/60" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-6">
                {/* Theme Section */}
                <div>
                  <h3 className="text-sm font-medium text-white/70 mb-3">Appearance</h3>
                  <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
                    <div className="flex items-center gap-3">
                      {isDarkMode ? (
                        <Moon className="w-5 h-5 text-neutral-400" />
                      ) : (
                        <Sun className="w-5 h-5 text-yellow-400" />
                      )}
                      <span className="text-sm text-white/80">
                        {isDarkMode ? 'Dark Mode' : 'Light Mode'}
                      </span>
                    </div>
                    <GlassToggle
                      enabled={isDarkMode}
                      onChange={onThemeChange}
                    />
                  </div>
                </div>

                {/* Connections Section */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-medium text-white/70">Connections</h3>
                    <motion.button
                      whileHover={{ rotate: 180 }}
                      transition={{ duration: 0.3 }}
                      className="p-1 text-white/40 hover:text-white/70 transition-colors"
                      title="Refresh connections"
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
                          <div className={`
                            p-2 rounded-lg
                            ${isAuthenticated && connection.enabled
                              ? 'bg-green-500/20 text-green-400' 
                              : 'bg-white/10 text-white/40'
                            }
                          `}>
                            {connection.icon}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white/90">{connection.name}</p>
                            <p className="text-xs text-white/40">
                              {isAuthenticated 
                                ? (connection.enabled ? 'Enabled' : 'Disabled')
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

export function Sidebar() {
  const { user, isAuthenticated, logout } = useAuth();
  const { createNewSession } = useChat();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [connections, setConnections] = useState<Connection[]>([
    { id: 'gmail', name: 'Gmail', icon: <Mail className="w-4 h-4" />, enabled: true },
    { id: 'calendar', name: 'Calendar', icon: <Calendar className="w-4 h-4" />, enabled: true },
    { id: 'tasks', name: 'Tasks', icon: <CheckSquare className="w-4 h-4" />, enabled: true },
    { id: 'notes', name: 'Notes', icon: <StickyNote className="w-4 h-4" />, enabled: true },
  ]);

  // Apply theme changes
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.add('light');
    }
  }, [isDarkMode]);

  const handleConnectionToggle = (id: string, enabled: boolean) => {
    setConnections(prev => prev.map(conn =>
      conn.id === id ? { ...conn, enabled } : conn
    ));
  };

  if (isCollapsed) {
    return (
      <GlassPanel className="w-16 flex flex-col items-center py-4 gap-4">
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          title="Expand sidebar"
        >
          <PanelLeft className="w-5 h-5 text-white/60" />
        </button>
        
        {isAuthenticated && (
          <>
            <button
              onClick={() => {
                createNewSession();
                setIsCollapsed(false);
              }}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              title="New chat"
            >
              <MessageSquarePlus className="w-5 h-5 text-white/60" />
            </button>
            
            <button
              onClick={() => setShowSettings(true)}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              title="Settings"
            >
              <Settings className="w-5 h-5 text-white/60" />
            </button>
          </>
        )}
      </GlassPanel>
    );
  }

  return (
    <>
      <GlassPanel className="w-80 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neutral-500/30 to-neutral-400/30 border border-neutral-400/30 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-neutral-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold gradient-text">Zenith AI</h2>
                <p className="text-xs text-white/40">Personal Assistant</p>
              </div>
            </div>
            <button
              onClick={() => setIsCollapsed(true)}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              title="Collapse sidebar"
            >
              <PanelLeftClose className="w-5 h-5 text-white/60" />
            </button>
          </div>

          {/* User info */}
          {isAuthenticated && user && (
            <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
              {user.picture ? (
                <img src={user.picture} alt={user.name} className="w-10 h-10 rounded-full" />
              ) : (
                <div className="w-10 h-10 rounded-full bg-neutral-500/30 flex items-center justify-center">
                  <User className="w-5 h-5 text-neutral-400" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white/90 truncate">{user.name || user.email}</p>
                <p className="text-xs text-white/40 truncate">{user.email}</p>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="p-4 space-y-2">
          {isAuthenticated && (
            <GlassButton
              variant="primary"
              size="md"
              onClick={createNewSession}
              className="w-full"
            >
              <MessageSquarePlus className="w-4 h-4 mr-2" />
              New Chat
            </GlassButton>
          )}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Bottom actions */}
        <div className="p-4 space-y-2 border-t border-white/10">
          <GlassButton
            variant="ghost"
            size="md"
            onClick={() => setShowSettings(true)}
            className="w-full justify-start"
          >
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </GlassButton>
          
          {isAuthenticated && (
            <GlassButton
              variant="ghost"
              size="md"
              onClick={logout}
              className="w-full justify-start text-red-400 hover:text-red-300"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Sign Out
            </GlassButton>
          )}
        </div>
      </GlassPanel>

      {/* Settings Panel */}
      <SettingsPanel
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        isDarkMode={isDarkMode}
        onThemeChange={setIsDarkMode}
        connections={connections}
        onConnectionToggle={handleConnectionToggle}
      />
    </>
  );
}

export default Sidebar;

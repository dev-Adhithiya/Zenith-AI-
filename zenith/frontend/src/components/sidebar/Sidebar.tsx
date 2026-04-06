import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { GlassButton } from '../ui/GlassButton';
import { GlassToggle } from '../ui/GlassToggle';
import { useAuth } from '../../contexts/AuthContext';
import { useChat } from '../../contexts/ChatContext';
import { useSettings } from '../../contexts/SettingsContext';
import { chatAPI } from '../../lib/api';
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
  PanelLeft,
  MessageSquare,
  Clock,
  Trash2,
  Volume2
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
  speakMode: boolean;
  onSpeakModeChange: (enabled: boolean) => void;
  connections: Connection[];
  onConnectionToggle: (id: string, enabled: boolean) => void;
}

function SettingsPanel({ isOpen, onClose, isDarkMode, onThemeChange, speakMode, onSpeakModeChange, connections, onConnectionToggle }: SettingsPanelProps) {
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

                {/* Speak Mode Section */}
                <div>
                  <h3 className="text-sm font-medium text-white/70 mb-3">Voice</h3>
                  <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
                    <div className="flex items-center gap-3">
                      <Volume2 className="w-5 h-5 text-neutral-400" />
                      <div>
                        <span className="text-sm text-white/80">Speak Mode</span>
                        <p className="text-xs text-white/40">AI reads messages aloud</p>
                      </div>
                    </div>
                    <GlassToggle
                      enabled={speakMode}
                      onChange={onSpeakModeChange}
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
  const { createNewSession, sessionId, loadSession } = useChat();
  const { speakMode, setSpeakMode } = useSettings();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [profileImageFailed, setProfileImageFailed] = useState(false);
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

  // Load chat history when authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      setChatHistory([]);
      return;
    }

    const loadHistory = async () => {
      setIsLoadingHistory(true);
      try {
        const data = await chatAPI.getSessions(20);
        setChatHistory(data.sessions || []);
      } catch (err) {
        // Silently handle error - chat history will load when index is ready
        console.warn('Chat history unavailable:', err);
        setChatHistory([]);
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadHistory();
  }, [isAuthenticated, sessionId]);

  const handleConnectionToggle = (id: string, enabled: boolean) => {
    setConnections(prev => prev.map(conn =>
      conn.id === id ? { ...conn, enabled } : conn
    ));
  };

  const handleSelectSession = async (targetSessionId: string) => {
    if (targetSessionId !== sessionId) {
      await loadSession(targetSessionId);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setDeletingSessionId(id);
    setDeleteError(null);
    try {
      await chatAPI.deleteSession(id);
      if (id === sessionId) {
        createNewSession();
      }
      setIsLoadingHistory(true);
      const data = await chatAPI.getSessions(20);
      setChatHistory(data.sessions || []);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to delete session';
      console.error('Failed to delete session', error);
      setDeleteError(errorMsg);
      // Clear error after 3 seconds
      setTimeout(() => setDeleteError(null), 3000);
    } finally {
      setDeletingSessionId(null);
      setIsLoadingHistory(false);
    }
  };

  const formatSessionTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
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
              {user.picture && !profileImageFailed ? (
                <img 
                  src={user.picture} 
                  alt={user.name} 
                  className="w-10 h-10 rounded-full object-cover"
                  crossOrigin="anonymous"
                  onError={() => setProfileImageFailed(true)}
                />
              ) : (
                <div className="w-10 h-10 rounded-full bg-neutral-500/30 flex items-center justify-center flex-shrink-0">
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

        {/* Chat History */}
        {isAuthenticated && (
          <div className="flex-1 overflow-hidden flex flex-col px-4">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="w-4 h-4 text-white/50" />
              <span className="text-xs font-medium text-white/50 uppercase tracking-wide">Recent Chats</span>
            </div>
            
            {deleteError && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mb-2 p-2 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-400"
              >
                {deleteError}
              </motion.div>
            )}
            
            {isLoadingHistory ? (
              <div className="text-xs text-white/40 py-2">Loading history...</div>
            ) : chatHistory.length > 0 ? (
              <div className="flex-1 overflow-y-auto space-y-1 pr-1">
                {chatHistory.map((session) => (
                  <motion.button
                    key={session.session_id}
                    onClick={() => handleSelectSession(session.session_id)}
                    className={`
                      w-full text-left p-2.5 rounded-lg transition-all
                      ${session.session_id === sessionId 
                        ? 'bg-neutral-500/20 border border-neutral-400/30' 
                        : 'hover:bg-white/5 border border-transparent'
                      }
                    `}
                    whileHover={{ x: 2 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <div className="flex items-start gap-2">
                      <MessageSquare className="w-3.5 h-3.5 text-white/40 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-sm text-white/80 truncate">
                            {session.title || session.last_message || 'New conversation'}
                          </p>
                          <motion.button
                             className={`text-white/30 p-1 rounded transition-colors ${
                               deletingSessionId === session.session_id
                                 ? 'opacity-50 cursor-not-allowed'
                                 : 'hover:text-red-400 hover:bg-red-400/10'
                             }`}
                             onClick={(e) => handleDeleteSession(e, session.session_id)}
                             disabled={deletingSessionId === session.session_id}
                             whileHover={deletingSessionId !== session.session_id ? { scale: 1.1 } : {}}
                             whileTap={deletingSessionId !== session.session_id ? { scale: 0.95 } : {}}
                          >
                             {deletingSessionId === session.session_id ? (
                               <motion.div
                                 animate={{ rotate: 360 }}
                                 transition={{ duration: 0.8, loop: Infinity, ease: 'linear' }}
                                 className="inline-block"
                               >
                                 <Trash2 className="w-3.5 h-3.5" />
                               </motion.div>
                             ) : (
                               <Trash2 className="w-3.5 h-3.5" />
                             )}
                          </motion.button>
                        </div>
                        <div className="flex items-center gap-1 mt-0.5">
                          <Clock className="w-3 h-3 text-white/30" />
                          <span className="text-xs text-white/30">
                            {formatSessionTime(session.updated_at || session.created_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.button>
                ))}
              </div>
            ) : (
              <div className="text-xs text-white/40 py-4 text-center">
                No chat history yet
              </div>
            )}
          </div>
        )}

        {/* Spacer - only show if not authenticated */}
        {!isAuthenticated && <div className="flex-1" />}

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
        speakMode={speakMode}
        onSpeakModeChange={setSpeakMode}
        connections={connections}
        onConnectionToggle={handleConnectionToggle}
      />
    </>
  );
}

export default Sidebar;

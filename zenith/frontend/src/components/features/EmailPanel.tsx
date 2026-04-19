import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { Mail, ChevronRight, User, Clock, X } from 'lucide-react';
import { gmailAPI, type Email } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';
import { sanitizeEmailHtml } from '../../lib/sanitizeHtml';

interface EmailDetailModalProps {
  email: Email | null;
  onClose: () => void;
}

function EmailDetailModal({ email, onClose }: EmailDetailModalProps) {
  const { data: fullEmail, isLoading, error } = useQuery({
    queryKey: ['gmail', 'message', email?.id],
    queryFn: () => gmailAPI.getMessage(email!.id),
    enabled: !!email,
  });

  if (!email) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-2xl max-h-[90vh] flex flex-col"
        >
          <GlassPanel variant="strong" className="p-5 flex flex-col max-h-[90vh]">
            <div className="flex items-start justify-between mb-4 flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <Mail className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Email Summary</h3>
                  <p className="text-xs text-white/40">{formatTimeAgo(email.date)}</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"  
              >
                <X className="w-5 h-5 text-white/60" />
              </button>
            </div>

            <div className="space-y-4 overflow-y-auto pr-2 custom-scrollbar flex-1">
              <div>
                <p className="text-xs text-white/40 mb-1">From</p>
                <p className="text-sm text-white/90">{email.from}</p>
              </div>

              <div>
                <p className="text-xs text-white/40 mb-1">Subject</p>
                <p className="text-sm text-white/90 font-medium">{email.subject || '(No subject)'}</p>
              </div>

              <div>
                <p className="text-xs text-white/40 mb-1">Message</p>
                {isLoading ? (
                  <p className="text-sm text-white/50 animate-pulse">Loading message body...</p>
                ) : error ? (
                  <div className="text-sm text-red-400">
                    Failed to load full message.
                    <p className="text-white/70 mt-2">{email.snippet}</p>
                  </div>
                ) : fullEmail?.body_html ? (
                  <div className="bg-white rounded-lg p-2 overflow-hidden mt-2">
                    <iframe
                      srcDoc={sanitizeEmailHtml(fullEmail.body_html)}
                      title="Email HTML content"
                      className="w-full min-h-[500px] bg-white border-0"
                      sandbox=""
                      referrerPolicy="no-referrer"
                    />
                  </div>
                ) : (
                  <div className="text-sm text-white/80 leading-relaxed whitespace-pre-wrap select-text break-words">
                    {fullEmail?.body_text || fullEmail?.snippet || email.snippet}
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-white/10 flex-shrink-0">
              <p className="text-xs text-white/30 text-center">
                Click outside or the X to close
              </p>
            </div>
          </GlassPanel>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export function EmailPanel() {
  const { isAuthenticated } = useAuth();
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['gmail', 'messages'],
    queryFn: () => gmailAPI.searchMessages('is:unread', 10),
    enabled: isAuthenticated,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  if (!isAuthenticated) return null;

  const unreadCount = data?.count || 0;

  return (
    <GlassPanel className="p-4">
      <div 
        className="flex items-center justify-between mb-3 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <Mail className="w-5 h-5 text-neutral-400" />
          <h3 className="text-sm font-semibold text-white/90">Unread Emails</h3>
          {unreadCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 text-xs font-medium">
              {unreadCount}
            </span>
          )}
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronRight className="w-4 h-4 text-white/40" />
        </motion.div>
      </div>

      {isLoading && (
        <div className="text-sm text-white/50">Loading emails...</div>
      )}

      {error && (
        <div className="text-sm text-red-400">
          Failed to load emails
        </div>
      )}

      {isExpanded && data && data.emails && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="space-y-2 overflow-hidden max-h-80 overflow-y-auto"
        >
          {data.emails.slice(0, 5).map((email: Email) => (
            <div
              key={email.id}
              onClick={() => setSelectedEmail(email)}
              className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors cursor-pointer"
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-white/50" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-white/90 truncate">
                      {email.from.split('<')[0].trim() || email.from}
                    </p>
                    {email.is_unread && (
                      <span className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-xs text-white/70 font-medium truncate mt-0.5">
                    {email.subject || '(No subject)'}
                  </p>
                  <p className="text-xs text-white/40 line-clamp-2 mt-1">
                    {email.snippet}
                  </p>
                  <div className="flex items-center gap-1 mt-2 text-white/30">
                    <Clock className="w-3 h-3" />
                    <span className="text-xs">
                      {formatTimeAgo(email.date)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
          
          {data.emails.length === 0 && (
            <div className="text-sm text-white/50 text-center py-4">
              <Mail className="w-8 h-8 mx-auto mb-2 text-white/30" />
              No unread emails 🎉
            </div>
          )}
        </motion.div>
      )}

      {/* Email Detail Modal */}
      {selectedEmail && (
        <EmailDetailModal 
          email={selectedEmail} 
          onClose={() => setSelectedEmail(null)} 
        />
      )}
    </GlassPanel>
  );
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default EmailPanel;

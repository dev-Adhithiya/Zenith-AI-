import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { Mail, ChevronRight, User, Clock } from 'lucide-react';
import { gmailAPI, type Email } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';

export function EmailPanel() {
  const { isAuthenticated } = useAuth();
  const [isExpanded, setIsExpanded] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['gmail', 'messages'],
    queryFn: () => gmailAPI.searchMessages('is:unread', 10),
    enabled: isAuthenticated,
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
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
              className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
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
                      {formatTimeAgo(email.received_at)}
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

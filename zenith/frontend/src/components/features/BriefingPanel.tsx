import { motion } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { Sparkles, RefreshCw, MessageSquare, ChevronDown } from 'lucide-react';
import { useBriefing } from '../../hooks/useBriefing';
import { useChat } from '../../contexts/ChatContext';
import { useState } from 'react';

export function BriefingPanel() {
  const { briefing, isLoading, error, refetch } = useBriefing();
  const { sendMessage } = useChat();
  const [isMinimized, setIsMinimized] = useState(false);

  return (
    <GlassPanel variant="strong" className="p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3 flex-1">
          <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-purple-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-white">
              {briefing?.title || 'Your Executive Summary'}
            </h3>
            <p className="text-xs text-white/40">Daily Briefing</p>
          </div>
        </div>
        
        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {/* Minimize button */}
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors group"
            title={isMinimized ? 'Expand' : 'Minimize'}
          >
            <ChevronDown 
              className={`w-4 h-4 text-white/60 group-hover:text-white/90 transition-all duration-200 ${
                isMinimized ? '-rotate-90' : 'rotate-0'
              }`}
            />
          </button>

          {/* Refresh button */}
          {!isLoading && briefing && !isMinimized && (
            <button
              onClick={refetch}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors group"
              title="Refresh briefing"
            >
              <RefreshCw className="w-4 h-4 text-white/60 group-hover:text-white/90 transition-colors" />
            </button>
          )}
        </div>
      </div>

      {/* Content - with collapse animation */}
      <motion.div
        initial={{ height: 'auto' }}
        animate={{ height: isMinimized ? 0 : 'auto' }}
        transition={{ duration: 0.3 }}
        className="overflow-hidden"
      >
        <div className="space-y-3">
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-2"
            >
              {/* Liquid Glass Loading Animation */}
              <div className="animate-pulse space-y-2">
                <div className="h-4 rounded-lg w-3/4 overflow-hidden relative bg-white/10">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" style={{ backgroundSize: '200% 100%' }} />
                </div>
                <div className="h-4 rounded-lg w-full overflow-hidden relative bg-white/10">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" style={{ backgroundSize: '200% 100%' }} />
                </div>
                <div className="h-4 rounded-lg w-5/6 overflow-hidden relative bg-white/10">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" style={{ backgroundSize: '200% 100%' }} />
                </div>
                <div className="h-4 rounded-lg w-2/3 overflow-hidden relative bg-white/10">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" style={{ backgroundSize: '200% 100%' }} />
                </div>
              </div>
              <p className="text-xs text-white/50 text-center mt-4">
                Preparing your briefing...
              </p>
            </motion.div>
          )}

          {!isLoading && briefing && (
            <>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="text-white/80 text-sm leading-relaxed whitespace-pre-wrap"
              >
                {briefing.content}
              </motion.div>
              
              {/* Action button to open detailed chat */}
              <motion.button
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.1 }}
                onClick={() => {
                  sendMessage("Please provide more details about my schedule, emails, and tasks. Expand on the executive summary.");
                }}
                className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 hover:border-purple-500/50 transition-all duration-200 group"
              >
                <MessageSquare className="w-4 h-4 text-purple-400 group-hover:text-purple-300" />
                <span className="text-sm font-medium text-purple-300 group-hover:text-purple-200">
                  Get Detailed Breakdown
                </span>
              </motion.button>
            </>
          )}

          {!isLoading && error && !briefing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-white/60 text-sm"
            >
              <p>Welcome back! I'm ready to help with your calendar, emails, and tasks.</p>
            </motion.div>
          )}
        </div>

        {/* Error indicator (subtle) */}
        {briefing?.error && (
          <div className="mt-3 pt-3 border-t border-white/10">
            <p className="text-xs text-white/40 italic">
              Note: Some data may be unavailable
            </p>
          </div>
        )}
      </motion.div>
    </GlassPanel>
  );
}

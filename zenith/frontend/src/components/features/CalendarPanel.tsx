import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { Calendar as CalendarIcon, Clock, MapPin, Video, ChevronRight } from 'lucide-react';
import { calendarAPI, type CalendarEvent } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';

export function CalendarPanel() {
  const { isAuthenticated } = useAuth();
  const [isExpanded, setIsExpanded] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['calendar', 'events'],
    queryFn: () => calendarAPI.listEvents(10),
    enabled: isAuthenticated,
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
  });

  if (!isAuthenticated) return null;

  return (
    <GlassPanel className="p-4">
      <div 
        className="flex items-center justify-between mb-3 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <CalendarIcon className="w-5 h-5 text-neutral-400" />
          <h3 className="text-sm font-semibold text-white/90">Upcoming Events</h3>
          {data && (
            <span className="text-xs text-white/40">({data.count})</span>
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
        <div className="text-sm text-white/50">Loading events...</div>
      )}

      {error && (
        <div className="text-sm text-red-400">
          Failed to load events
        </div>
      )}

      {isExpanded && data && data.events && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="space-y-2 overflow-hidden"
        >
          {data.events.slice(0, 5).map((event: CalendarEvent) => (
            <div
              key={event.id}
              className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-white/90 truncate">
                    {event.summary}
                  </h4>
                  <div className="flex items-center gap-2 mt-1">
                    <Clock className="w-3 h-3 text-white/40" />
                    <span className="text-xs text-white/50">
                      {new Date(event.start).toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  {event.location && (
                    <div className="flex items-center gap-2 mt-1">
                      <MapPin className="w-3 h-3 text-white/40" />
                      <span className="text-xs text-white/50 truncate">
                        {event.location}
                      </span>
                    </div>
                  )}
                </div>
                {event.meet_link && (
                  <a
                    href={event.meet_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors"
                    title="Join Google Meet"
                  >
                    <Video className="w-4 h-4" />
                  </a>
                )}
              </div>
            </div>
          ))}
          
          {data.events.length === 0 && (
            <div className="text-sm text-white/50 text-center py-2">
              No upcoming events
            </div>
          )}
        </motion.div>
      )}
    </GlassPanel>
  );
}

export default CalendarPanel;

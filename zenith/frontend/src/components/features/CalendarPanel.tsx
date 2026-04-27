import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { Calendar as CalendarIcon, Clock, MapPin, Video, ChevronRight, X } from 'lucide-react';
import { calendarAPI, type CalendarEvent } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';

interface EventDetailModalProps {
  event: CalendarEvent | null;
  onClose: () => void;
}

function EventDetailModal({ event, onClose }: EventDetailModalProps) {
  if (!event) return null;

  const startDate = new Date(event.start);
  const endDate = new Date(event.end);
  const duration = Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60));

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
          className="w-full max-w-lg"
        >
          <GlassPanel variant="strong" className="p-5">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <CalendarIcon className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Event Details</h3>
                  <p className="text-xs text-white/40">{duration} minutes</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5 text-white/60" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-xs text-white/40 mb-1">Event</p>
                <p className="text-sm text-white/90 font-medium">{event.summary}</p>
              </div>
              
              <div>
                <p className="text-xs text-white/40 mb-1">When</p>
                <p className="text-sm text-white/90">
                  {startDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
                </p>
                <p className="text-sm text-white/70">
                  {startDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })} - {endDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                </p>
              </div>
              
              {event.location && (
                <div>
                  <p className="text-xs text-white/40 mb-1">Location</p>
                  <p className="text-sm text-white/70">{event.location}</p>
                </div>
              )}
              
              {event.description && (
                <div>
                  <p className="text-xs text-white/40 mb-1">Description</p>
                  <p className="text-sm text-white/70 leading-relaxed">{event.description}</p>
                </div>
              )}
              
              {event.attendees && event.attendees.length > 0 && (
                <div>
                  <p className="text-xs text-white/40 mb-1">Attendees</p>
                  <div className="flex flex-wrap gap-1">
                    {event.attendees.map((attendee, i) => (
                      <span key={i} className="text-xs bg-white/10 px-2 py-1 rounded-full text-white/70">
                        {attendee}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {event.meet_link && (
                <a
                  href={event.meet_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 p-3 mt-2 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors"
                >
                  <Video className="w-5 h-5" />
                  <span className="text-sm font-medium">Join Google Meet</span>
                </a>
              )}
            </div>

            <div className="mt-4 pt-4 border-t border-white/10">
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

export function CalendarPanel() {
  const { isAuthenticated } = useAuth();
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['calendar', 'events'],
    queryFn: () => calendarAPI.listEvents(10),
    enabled: isAuthenticated,
    refetchInterval: isExpanded ? 60000 : false,
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
              onClick={() => setSelectedEvent(event)}
              className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors cursor-pointer"
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
                    onClick={(e) => e.stopPropagation()}
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

      {/* Event Detail Modal */}
      {selectedEvent && (
        <EventDetailModal 
          event={selectedEvent} 
          onClose={() => setSelectedEvent(null)} 
        />
      )}
    </GlassPanel>
  );
}

export default CalendarPanel;

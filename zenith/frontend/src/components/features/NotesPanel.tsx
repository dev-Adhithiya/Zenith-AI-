import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { GlassButton } from '../ui/GlassButton';
import { GlassInput, GlassTextarea } from '../ui/GlassInput';
import { StickyNote, Plus, ChevronRight, Search, X, Tag } from 'lucide-react';
import { notesAPI, type Note } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';

interface NoteDetailModalProps {
  note: Note | null;
  onClose: () => void;
}

function NoteDetailModal({ note, onClose }: NoteDetailModalProps) {
  if (!note) return null;

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
          className="w-full max-w-lg max-h-[80vh] overflow-hidden"
        >
          <GlassPanel variant="strong" className="p-5 flex flex-col max-h-[80vh]">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center">
                  <StickyNote className="w-5 h-5 text-yellow-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Note</h3>
                  <p className="text-xs text-white/40">
                    {new Date(note.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric'
                    })}
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5 text-white/60" />
              </button>
            </div>

            <div className="space-y-3 flex-1 overflow-y-auto">
              <div>
                <p className="text-xs text-white/40 mb-1">Title</p>
                <p className="text-sm text-white/90 font-medium">{note.title}</p>
              </div>
              
              <div>
                <p className="text-xs text-white/40 mb-1">Content</p>
                <p className="text-sm text-white/70 leading-relaxed whitespace-pre-wrap">{note.content}</p>
              </div>
              
              {note.tags && note.tags.length > 0 && (
                <div>
                  <p className="text-xs text-white/40 mb-2">Tags</p>
                  <div className="flex flex-wrap gap-2">
                    {note.tags.map((tag, i) => (
                      <span
                        key={i}
                        className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/10 text-xs text-white/70"
                      >
                        <Tag className="w-3 h-3" />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {note.source && (
                <div>
                  <p className="text-xs text-white/40 mb-1">Source</p>
                  <p className="text-sm text-white/50">{note.source}</p>
                </div>
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

export function NotesPanel() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [isExpanded, setIsExpanded] = useState(false);
  const [showAddNote, setShowAddNote] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [newNote, setNewNote] = useState({ title: '', content: '', tags: '' });
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['notes'],
    queryFn: () => notesAPI.listNotes(20),
    enabled: isAuthenticated,
    refetchInterval: isExpanded ? 60000 : false,
  });

  const saveNoteMutation = useMutation({
    mutationFn: (note: { title: string; content: string; tags?: string[] }) => 
      notesAPI.saveNote(note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes'] });
      setNewNote({ title: '', content: '', tags: '' });
      setShowAddNote(false);
    },
  });

  const searchNotesQuery = useQuery({
    queryKey: ['notes', 'search', searchQuery],
    queryFn: () => notesAPI.searchNotes(searchQuery),
    enabled: !!searchQuery && searchQuery.length > 2,
  });

  const handleSaveNote = () => {
    if (newNote.title.trim() && newNote.content.trim()) {
      const tags = newNote.tags
        .split(',')
        .map(t => t.trim())
        .filter(Boolean);
      
      saveNoteMutation.mutate({
        title: newNote.title,
        content: newNote.content,
        tags: tags.length > 0 ? tags : undefined,
      });
    }
  };

  const displayNotes = searchQuery && searchNotesQuery.data 
    ? searchNotesQuery.data.notes 
    : data?.notes || [];

  if (!isAuthenticated) return null;

  return (
    <GlassPanel className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div 
          className="flex items-center gap-2 cursor-pointer flex-1"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <StickyNote className="w-5 h-5 text-neutral-400" />
          <h3 className="text-sm font-semibold text-white/90">Notes</h3>
          {data && (
            <span className="text-xs text-white/40">({data.count})</span>
          )}
          <motion.div
            animate={{ rotate: isExpanded ? 90 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronRight className="w-4 h-4 text-white/40" />
          </motion.div>
        </div>
        
        <GlassButton
          variant="ghost"
          size="sm"
          onClick={() => setShowAddNote(!showAddNote)}
          title="Add note"
        >
          <Plus className="w-4 h-4" />
        </GlassButton>
      </div>

      {showAddNote && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="mb-3 space-y-2"
        >
          <GlassInput
            placeholder="Note title..."
            value={newNote.title}
            onChange={(e) => setNewNote({ ...newNote, title: e.target.value })}
          />
          <GlassTextarea
            placeholder="Note content..."
            value={newNote.content}
            onChange={(e) => setNewNote({ ...newNote, content: e.target.value })}
            rows={3}
          />
          <GlassInput
            placeholder="Tags (comma separated)..."
            value={newNote.tags}
            onChange={(e) => setNewNote({ ...newNote, tags: e.target.value })}
          />
          <GlassButton
            variant="primary"
            size="sm"
            onClick={handleSaveNote}
            isLoading={saveNoteMutation.isPending}
            className="w-full"
          >
            Save Note
          </GlassButton>
        </motion.div>
      )}

      {isExpanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="space-y-2 overflow-hidden"
        >
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
            <GlassInput
              placeholder="Search notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          {isLoading && (
            <div className="text-sm text-white/50">Loading notes...</div>
          )}

          {error && (
            <div className="text-sm text-red-400">
              ⚠️ Failed to load notes. Make sure to create the Firestore index.
            </div>
          )}

          {/* Notes list */}
          {displayNotes.length > 0 ? (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {displayNotes.map((note: Note) => (
                <div
                  key={note.note_id}
                  onClick={() => setSelectedNote(note)}
                  className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors cursor-pointer"
                >
                  <h4 className="text-sm font-medium text-white/90 mb-1">
                    {note.title}
                  </h4>
                  <p className="text-xs text-white/60 line-clamp-2 mb-2">
                    {note.content}
                  </p>
                  {note.tags && note.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {note.tags.map((tag, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-full bg-white/10 text-xs text-white/50"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-white/30 mt-2">
                    {new Date(note.created_at).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-white/50 text-center py-2">
              {searchQuery ? 'No notes found' : 'No notes yet. Add one above!'}
            </div>
          )}
        </motion.div>
      )}

      {/* Note Detail Modal */}
      {selectedNote && (
        <NoteDetailModal 
          note={selectedNote} 
          onClose={() => setSelectedNote(null)} 
        />
      )}
    </GlassPanel>
  );
}

export default NotesPanel;

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { GlassButton } from '../ui/GlassButton';
import { GlassInput, GlassTextarea } from '../ui/GlassInput';
import { StickyNote, Plus, ChevronRight, Search } from 'lucide-react';
import { notesAPI, type Note } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';

export function NotesPanel() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [isExpanded, setIsExpanded] = useState(false);
  const [showAddNote, setShowAddNote] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [newNote, setNewNote] = useState({ title: '', content: '', tags: '' });

  const { data, isLoading, error } = useQuery({
    queryKey: ['notes'],
    queryFn: () => notesAPI.listNotes(20),
    enabled: isAuthenticated,
    refetchInterval: 3000,
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
                  className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
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
    </GlassPanel>
  );
}

export default NotesPanel;

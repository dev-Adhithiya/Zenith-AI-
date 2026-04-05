import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { GlassButton } from '../ui/GlassButton';
import { GlassInput } from '../ui/GlassInput';
import { CheckSquare, Square, Plus, ChevronRight } from 'lucide-react';
import { tasksAPI, type Task } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';

export function TasksPanel() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [isExpanded, setIsExpanded] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [showAddTask, setShowAddTask] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => tasksAPI.listTasks(false),
    enabled: isAuthenticated,
    refetchInterval: 3000,
  });

  const addTaskMutation = useMutation({
    mutationFn: (title: string) => tasksAPI.addTask({ title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setNewTaskTitle('');
      setShowAddTask(false);
    },
  });

  const handleAddTask = () => {
    if (newTaskTitle.trim()) {
      addTaskMutation.mutate(newTaskTitle);
    }
  };

  if (!isAuthenticated) return null;

  return (
    <GlassPanel className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div 
          className="flex items-center gap-2 cursor-pointer flex-1"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <CheckSquare className="w-5 h-5 text-neutral-400" />
          <h3 className="text-sm font-semibold text-white/90">Tasks</h3>
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
          onClick={() => setShowAddTask(!showAddTask)}
          title="Add task"
        >
          <Plus className="w-4 h-4" />
        </GlassButton>
      </div>

      {showAddTask && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="mb-3 flex gap-2"
        >
          <GlassInput
            placeholder="Task title..."
            value={newTaskTitle}
            onChange={(e) => setNewTaskTitle(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddTask()}
          />
          <GlassButton
            variant="primary"
            size="sm"
            onClick={handleAddTask}
            isLoading={addTaskMutation.isPending}
          >
            Add
          </GlassButton>
        </motion.div>
      )}

      {isLoading && (
        <div className="text-sm text-white/50">Loading tasks...</div>
      )}

      {error && (
        <div className="text-sm text-red-400">Failed to load tasks</div>
      )}

      {isExpanded && data && data.tasks && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="space-y-2 overflow-hidden"
        >
          {data.tasks.slice(0, 10).map((task: Task) => (
            <div
              key={task.id}
              className="flex items-start gap-2 p-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group"
            >
              <button
                className="mt-0.5 text-white/40 hover:text-white/70 transition-colors"
                title={task.is_completed ? 'Mark incomplete' : 'Mark complete'}
              >
                {task.is_completed ? (
                  <CheckSquare className="w-4 h-4 text-green-400" />
                ) : (
                  <Square className="w-4 h-4" />
                )}
              </button>
              <div className="flex-1 min-w-0">
                <p className={`text-sm ${task.is_completed ? 'line-through text-white/40' : 'text-white/90'}`}>
                  {task.title}
                </p>
                {task.notes && (
                  <p className="text-xs text-white/40 mt-0.5">{task.notes}</p>
                )}
                {task.due && (
                  <p className="text-xs text-white/40 mt-0.5">
                    Due: {new Date(task.due).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
          ))}

          {data.tasks.length === 0 && (
            <div className="text-sm text-white/50 text-center py-2">
              No tasks yet. Add one above!
            </div>
          )}
        </motion.div>
      )}
    </GlassPanel>
  );
}

export default TasksPanel;

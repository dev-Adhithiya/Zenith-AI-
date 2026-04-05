import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { GlassButton } from '../ui/GlassButton';
import { GlassInput } from '../ui/GlassInput';
import { CheckSquare, Square, Plus, ChevronRight, X, Calendar, Check, RotateCcw } from 'lucide-react';
import { tasksAPI, type Task } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';

interface TaskDetailModalProps {
  task: Task | null;
  onClose: () => void;
  onComplete: (taskId: string) => void;
  onUncomplete: (taskId: string) => void;
  isLoading: boolean;
}

function TaskDetailModal({ task, onClose, onComplete, onUncomplete, isLoading }: TaskDetailModalProps) {
  if (!task) return null;

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
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${task.is_completed ? 'bg-green-500/20' : 'bg-orange-500/20'}`}>
                  {task.is_completed ? (
                    <CheckSquare className="w-5 h-5 text-green-400" />
                  ) : (
                    <Square className="w-5 h-5 text-orange-400" />
                  )}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Task Details</h3>
                  <p className="text-xs text-white/40">{task.is_completed ? 'Completed' : 'Pending'}</p>
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
                <p className="text-xs text-white/40 mb-1">Task</p>
                <p className={`text-sm font-medium ${task.is_completed ? 'line-through text-white/50' : 'text-white/90'}`}>
                  {task.title}
                </p>
              </div>
              
              {task.notes && (
                <div>
                  <p className="text-xs text-white/40 mb-1">Notes</p>
                  <p className="text-sm text-white/70 leading-relaxed">{task.notes}</p>
                </div>
              )}
              
              {task.due && (
                <div>
                  <p className="text-xs text-white/40 mb-1">Due Date</p>
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-white/50" />
                    <p className="text-sm text-white/70">
                      {new Date(task.due).toLocaleDateString('en-US', {
                        weekday: 'long',
                        month: 'long',
                        day: 'numeric',
                        year: 'numeric'
                      })}
                    </p>
                  </div>
                </div>
              )}
              
              {task.created_at && (
                <div>
                  <p className="text-xs text-white/40 mb-1">Created</p>
                  <p className="text-sm text-white/50">
                    {new Date(task.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric'
                    })}
                  </p>
                </div>
              )}
            </div>

            {/* Action buttons */}
            <div className="mt-4 pt-4 border-t border-white/10 flex gap-2">
              {task.is_completed ? (
                <GlassButton
                  variant="ghost"
                  size="md"
                  onClick={() => onUncomplete(task.id)}
                  disabled={isLoading}
                  className="flex-1"
                >
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Mark Incomplete
                </GlassButton>
              ) : (
                <GlassButton
                  variant="primary"
                  size="md"
                  onClick={() => onComplete(task.id)}
                  disabled={isLoading}
                  className="flex-1"
                >
                  <Check className="w-4 h-4 mr-2" />
                  Mark Complete
                </GlassButton>
              )}
            </div>
          </GlassPanel>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export function TasksPanel() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [isExpanded, setIsExpanded] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [showAddTask, setShowAddTask] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

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

  const completeTaskMutation = useMutation({
    mutationFn: (taskId: string) => tasksAPI.completeTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setSelectedTask(null);
    },
  });

  const uncompleteTaskMutation = useMutation({
    mutationFn: (taskId: string) => tasksAPI.uncompleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setSelectedTask(null);
    },
  });

  const handleAddTask = () => {
    if (newTaskTitle.trim()) {
      addTaskMutation.mutate(newTaskTitle);
    }
  };

  const handleCompleteTask = (taskId: string) => {
    completeTaskMutation.mutate(taskId);
  };

  const handleUncompleteTask = (taskId: string) => {
    uncompleteTaskMutation.mutate(taskId);
  };

  const handleToggleComplete = (e: React.MouseEvent, task: Task) => {
    e.stopPropagation();
    if (task.is_completed) {
      uncompleteTaskMutation.mutate(task.id);
    } else {
      completeTaskMutation.mutate(task.id);
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
              onClick={() => setSelectedTask(task)}
              className="flex items-start gap-2 p-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group cursor-pointer"
            >
              <button
                onClick={(e) => handleToggleComplete(e, task)}
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
                  <p className="text-xs text-white/40 mt-0.5 truncate">{task.notes}</p>
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

      {/* Task Detail Modal */}
      {selectedTask && (
        <TaskDetailModal 
          task={selectedTask} 
          onClose={() => setSelectedTask(null)}
          onComplete={handleCompleteTask}
          onUncomplete={handleUncompleteTask}
          isLoading={completeTaskMutation.isPending || uncompleteTaskMutation.isPending}
        />
      )}
    </GlassPanel>
  );
}

export default TasksPanel;

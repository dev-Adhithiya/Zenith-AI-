import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChat } from '../../contexts/ChatContext';
import { useVoice } from '../../contexts/VoiceContext';
import { User, Sparkles, Volume2, Mail, Calendar, CheckSquare, StickyNote } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

interface QuickActionProps {
  icon: React.ReactNode;
  label: string;
  example: string;
  onClick: () => void;
}

function QuickAction({ icon, label, example, onClick }: QuickActionProps) {
  return (
    <motion.button
      onClick={onClick}
      className="p-4 rounded-xl bg-white/5 border border-white/10 text-left hover:bg-white/10 hover:border-white/20 transition-all duration-200 group cursor-pointer"
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-neutral-400 group-hover:text-neutral-300 transition-colors">
          {icon}
        </span>
        <p className="text-sm font-medium text-white/70 group-hover:text-white/90 transition-colors">{label}</p>
      </div>
      <p className="text-xs text-white/40 group-hover:text-white/60 transition-colors">"{example}"</p>
    </motion.button>
  );
}

export function MessageList() {
  const { messages, isLoading, error, sendMessage } = useChat();
  const { speak } = useVoice();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const quickActions = [
    {
      icon: <Mail className="w-4 h-4" />,
      label: 'Email',
      example: 'Show my unread emails from today',
    },
    {
      icon: <Calendar className="w-4 h-4" />,
      label: 'Calendar',
      example: 'What meetings do I have tomorrow?',
    },
    {
      icon: <CheckSquare className="w-4 h-4" />,
      label: 'Tasks',
      example: 'Add a task to review the Q4 report',
    },
    {
      icon: <StickyNote className="w-4 h-4" />,
      label: 'Notes',
      example: 'Save this meeting summary to my notes',
    },
  ];

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-2xl">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-neutral-500/20 to-neutral-400/20 border border-neutral-400/20 flex items-center justify-center">
            <Sparkles className="w-8 h-8 text-neutral-400" />
          </div>
          <h3 className="text-xl font-semibold text-white/80 mb-2">
            How can I help you today?
          </h3>
          <p className="text-sm text-white/50 mb-6">
            I can help you manage your emails, calendar, tasks, and notes. Just ask!
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {quickActions.map((action) => (
              <QuickAction
                key={action.label}
                icon={action.icon}
                label={action.label}
                example={action.example}
                onClick={() => sendMessage(action.example)}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <AnimatePresence mode="popLayout">
        {messages.map((message, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.3 }}
            className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'assistant' && (
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neutral-500/30 to-neutral-400/30 border border-neutral-400/30 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-4 h-4 text-neutral-400" />
              </div>
            )}

            <div
              className={`
                max-w-[70%] px-4 py-3 rounded-2xl
                ${message.role === 'user'
                  ? 'bg-gradient-to-r from-neutral-600/80 to-neutral-500/80 border border-neutral-400/30 text-white'
                  : 'bg-white/5 border border-white/10 text-white/90'
                }
              `}
            >
              {/* Images section */}
              {message.images && message.images.length > 0 && (
                <div className="mb-3 grid grid-cols-2 gap-2">
                  {message.images.map((image) => (
                    <motion.div
                      key={image.id}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="rounded-lg overflow-hidden border border-white/10"
                    >
                      <img
                        src={image.src}
                        alt={image.filename || 'Attached image'}
                        className="w-full h-auto max-h-64 object-cover hover:opacity-75 transition-opacity cursor-pointer"
                        onClick={() => {
                          // Open image in new tab on click
                          const newTab = window.open(image.src, '_blank');
                          if (newTab) newTab.focus();
                        }}
                      />
                    </motion.div>
                  ))}
                </div>
              )}

              <div className="message-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {message.content}
                </ReactMarkdown>
              </div>

              {message.role === 'assistant' && message.metadata && message.metadata.requires_confirmation && index === messages.length - 1 && (
                <div className="mt-4 p-4 rounded-xl bg-white/10 border border-white/20">
                  <p className="text-sm font-medium mb-3 text-white/90">Confirmation Required</p>
                  <div className="flex gap-2 text-sm justify-start">
                    <button
                      onClick={() => sendMessage("Approve")}
                      className="px-4 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg border border-green-500/30 transition-colors"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => sendMessage("Edit")}
                      className="px-4 py-2 bg-neutral-500/20 hover:bg-neutral-500/30 text-neutral-300 rounded-lg border border-neutral-500/30 transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => sendMessage("Cancel")}
                      className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg border border-red-500/30 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {message.role === 'assistant' && (
                <button
                  onClick={() => speak(message.content)}
                  className="mt-2 p-1 text-white/40 hover:text-white/70 transition-colors"
                  title="Read aloud"
                >
                  <Volume2 className="w-4 h-4" />
                </button>
              )}
            </div>

            {message.role === 'user' && (
              <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-white/60" />
              </div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      {isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex gap-3"
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neutral-500/30 to-neutral-400/30 border border-neutral-400/30 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-neutral-400" />
          </div>
          <div className="bg-white/5 border border-white/10 px-4 py-3 rounded-2xl">
            <div className="flex gap-1">
              <motion.div
                className="w-2 h-2 bg-white/40 rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
              />
              <motion.div
                className="w-2 h-2 bg-white/40 rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
              />
              <motion.div
                className="w-2 h-2 bg-white/40 rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
              />
            </div>
          </div>
        </motion.div>
      )}

      {error && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3 rounded-xl bg-red-500/10 border border-red-400/30 text-red-400 text-sm"
        >
          ⚠️ {error}
        </motion.div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}

export default MessageList;

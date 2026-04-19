import { useEffect, useRef, useMemo, type ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useChat } from '../../contexts/ChatContext';
import { useVoice } from '../../contexts/VoiceContext';
import { User, Sparkles, Volume2, Mail, Calendar, CheckSquare, StickyNote } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeSanitize from 'rehype-sanitize';
import type { ChatMessage } from '../../lib/api';
import 'katex/dist/katex.min.css';

interface QuickActionProps {
  icon: ReactNode;
  label: string;
  example: string;
  onClick: () => void;
}

function QuickAction({ icon, label, example, onClick }: QuickActionProps) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      className="p-4 rounded-xl bg-white/5 border border-white/10 text-left hover:bg-white/10 hover:border-white/20 transition-all duration-200 group cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400/60"
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

const remarkPlugins = [remarkGfm, remarkMath];
const rehypePlugins = [rehypeKatex, rehypeSanitize];

interface MessageBubbleProps {
  message: ChatMessage;
  index: number;
  total: number;
  sendMessage: (msg: string) => void;
  speak: (text: string) => void;
}

function MessageBubble({ message, index, total, sendMessage, speak }: MessageBubbleProps) {
  return (
    <div
      className={`flex gap-3 pb-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
    >
      {message.role === 'assistant' && (
        <div
          className="w-8 h-8 rounded-lg bg-gradient-to-br from-neutral-500/30 to-neutral-400/30 border border-neutral-400/30 flex items-center justify-center flex-shrink-0"
          aria-hidden
        >
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
        {message.images && message.images.length > 0 && (
          <div className="mb-3 grid grid-cols-2 gap-2">
            {message.images.map((image) => (
              <div
                key={image.id}
                className="rounded-lg overflow-hidden border border-white/10"
              >
                <img
                  src={image.src}
                  alt={image.filename ? `Attached: ${image.filename}` : 'Attached image'}
                  className="w-full h-auto max-h-64 object-cover hover:opacity-75 transition-opacity cursor-pointer"
                  onClick={() => {
                    const newTab = window.open(image.src, '_blank');
                    if (newTab) newTab.focus();
                  }}
                />
              </div>
            ))}
          </div>
        )}

        <div className="message-content max-w-none text-sm leading-relaxed">
          <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}>
            {message.content}
          </ReactMarkdown>
        </div>

        {message.role === 'assistant' && message.metadata?.requires_confirmation && index === total - 1 && (
          <div className="mt-4 p-4 rounded-xl bg-white/10 border border-white/20">
            <p className="text-sm font-medium mb-3 text-white/90">Confirmation Required</p>
            <div className="flex gap-2 text-sm justify-start flex-wrap">
              <button
                type="button"
                onClick={() => sendMessage('Approve')}
                className="px-4 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg border border-green-500/30 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-green-400/50"
              >
                Approve
              </button>
              <button
                type="button"
                onClick={() => sendMessage('Edit')}
                className="px-4 py-2 bg-neutral-500/20 hover:bg-neutral-500/30 text-neutral-300 rounded-lg border border-neutral-500/30 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400/50"
              >
                Edit
              </button>
              <button
                type="button"
                onClick={() => sendMessage('Cancel')}
                className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg border border-red-500/30 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400/50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {message.role === 'assistant' && (
          <button
            type="button"
            onClick={() => speak(message.content)}
            className="mt-2 p-1 text-white/40 hover:text-white/70 transition-colors rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400/50"
            title="Read aloud"
            aria-label="Read this message aloud"
          >
            <Volume2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {message.role === 'user' && (
        <div
          className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center flex-shrink-0"
          aria-hidden
        >
          <User className="w-4 h-4 text-white/60" />
        </div>
      )}
    </div>
  );
}

export function MessageList() {
  const { messages, isLoading, error, sendMessage } = useChat();
  const { speak } = useVoice();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 168,
    overscan: 10,
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const quickActions = useMemo(
    () => [
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
    ],
    [],
  );

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8" role="region" aria-label="Chat suggestions">
        <div className="text-center max-w-2xl">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-neutral-500/20 to-neutral-400/20 border border-neutral-400/20 flex items-center justify-center">
            <Sparkles className="w-8 h-8 text-neutral-400" aria-hidden />
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
    <div
      ref={parentRef}
      className="flex-1 overflow-y-auto p-4"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((vi) => {
          const message = messages[vi.index];
          return (
            <div
              key={`${vi.index}-${message.timestamp ?? ''}`}
              data-index={vi.index}
              ref={virtualizer.measureElement}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${vi.start}px)`,
              }}
            >
              <MessageBubble
                message={message}
                index={vi.index}
                total={messages.length}
                sendMessage={sendMessage}
                speak={speak}
              />
            </div>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        {isLoading && (
          <motion.div
            key="typing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex gap-3"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neutral-500/30 to-neutral-400/30 border border-neutral-400/30 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-neutral-400" aria-hidden />
            </div>
            <div className="bg-white/5 border border-white/10 px-4 py-3 rounded-2xl">
              <div className="flex gap-1" aria-label="Assistant is typing">
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
      </AnimatePresence>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3 rounded-xl bg-red-500/10 border border-red-400/30 text-red-400 text-sm"
          role="alert"
        >
          {error}
        </motion.div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}

export default MessageList;

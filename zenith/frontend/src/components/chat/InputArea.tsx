import { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChat } from '../../contexts/ChatContext';
import { useVoice } from '../../contexts/VoiceContext';
import { Send, Mic, Square, Sparkles } from 'lucide-react';

export function InputArea() {
  const { sendMessage, isLoading } = useChat();
  const { isListening, transcript, toggleListening, isSupported, stopListening, clearTranscript } = useVoice();
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Update input when transcript changes (voice input)
  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  // Auto-focus input on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSend = () => {
    const messageToSend = input.trim();
    if (!messageToSend || isLoading) return;
    
    // Stop listening if active
    if (isListening) {
      stopListening();
    }
    
    sendMessage(messageToSend);
    setInput('');
    clearTranscript();
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoiceClick = () => {
    if (isListening) {
      // If listening, stop and send the message
      stopListening();
      if (input.trim()) {
        setTimeout(() => {
          handleSend();
        }, 100);
      }
    } else {
      // Start listening and clear input
      setInput('');
      clearTranscript();
      toggleListening();
    }
  };

  return (
    <div className="p-4 border-t border-white/10">
      {/* Voice listening indicator */}
      <AnimatePresence>
        {isListening && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="mb-3 flex items-center justify-center gap-3"
          >
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-red-500/20 to-orange-500/20 border border-red-400/30">
              <motion.div
                className="w-3 h-3 rounded-full bg-red-500"
                animate={{ scale: [1, 1.3, 1], opacity: [1, 0.7, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
              <span className="text-sm text-white/70">Listening...</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main input container - Modern chat style */}
      <div className="relative">
        <div className={`
          flex items-end gap-3 p-3 rounded-2xl
          bg-white/5 border transition-all duration-300
          ${isListening 
            ? 'border-red-400/50 ring-2 ring-red-400/20' 
            : 'border-white/10 hover:border-white/20 focus-within:border-neutral-400/50 focus-within:ring-2 focus-within:ring-neutral-400/20'
          }
        `}>
          {/* Sparkles icon - Gemini style */}
          <div className="flex-shrink-0 pb-2">
            <motion.div
              animate={isLoading ? { rotate: 360 } : { rotate: 0 }}
              transition={{ duration: 2, repeat: isLoading ? Infinity : 0, ease: 'linear' }}
            >
              <Sparkles className={`w-5 h-5 ${isLoading ? 'text-neutral-400' : 'text-white/30'}`} />
            </motion.div>
          </div>

          {/* Text input */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isListening ? "Speak now..." : "Ask Zenith anything..."}
            disabled={isLoading}
            className={`
              flex-1 bg-transparent resize-none
              text-white placeholder-white/40
              focus:outline-none
              disabled:opacity-50 disabled:cursor-not-allowed
              max-h-32 min-h-[28px]
              text-base leading-7
              scrollbar-thin scrollbar-thumb-white/20
            `}
            rows={1}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = Math.min(target.scrollHeight, 128) + 'px';
            }}
          />

          {/* Action buttons */}
          <div className="flex items-center gap-1 flex-shrink-0 pb-1">
            {/* Voice button */}
            {isSupported && (
              <motion.button
                onClick={handleVoiceClick}
                disabled={isLoading}
                className={`
                  p-2.5 rounded-xl transition-all duration-200
                  ${isListening 
                    ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 ring-2 ring-red-500/30' 
                    : 'text-white/50 hover:text-white/80 hover:bg-white/10'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                title={isListening ? 'Stop & send' : 'Voice input'}
              >
                {isListening ? (
                  <Square className="w-5 h-5" fill="currentColor" />
                ) : (
                  <Mic className="w-5 h-5" />
                )}
              </motion.button>
            )}

            {/* Send button */}
            <motion.button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className={`
                p-2.5 rounded-xl transition-all duration-200
                ${input.trim() && !isLoading
                  ? 'bg-gradient-to-r from-neutral-600 to-neutral-500 text-white hover:from-neutral-500 hover:to-neutral-400 shadow-lg shadow-neutral-500/20'
                  : 'bg-white/5 text-white/30 cursor-not-allowed'
                }
              `}
              whileHover={input.trim() && !isLoading ? { scale: 1.05 } : {}}
              whileTap={input.trim() && !isLoading ? { scale: 0.95 } : {}}
              title="Send message"
            >
              {isLoading ? (
                <motion.div
                  className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </motion.button>
          </div>
        </div>
      </div>

      {/* Helper text */}
      <p className="mt-2 text-xs text-white/30 text-center">
        {isListening 
          ? 'Click the stop button to send your message'
          : 'Press Enter to send • Shift+Enter for new line'
        }
      </p>
    </div>
  );
}

export default InputArea;

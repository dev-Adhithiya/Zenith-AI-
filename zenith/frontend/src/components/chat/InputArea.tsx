import { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChat } from '../../contexts/ChatContext';
import { useVoice } from '../../contexts/VoiceContext';
import { Send, Mic, Square, Sparkles, Upload, Plus, SlidersHorizontal, Mail, X, Check, Calendar, CheckSquare, FileText } from 'lucide-react';
import { InputAreaAttachments } from './InputAreaAttachments';

export function InputArea() {
  const { sendMessage, isLoading, activeTool, setActiveTool, stopMessage } = useChat();
  const { isListening, transcript, toggleListening, isSupported, stopListening, clearTranscript } = useVoice();
  const [input, setInput] = useState('');
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [showToolsDropdown, setShowToolsDropdown] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleImageSelect = (files: FileList | null | File[]) => {
    const fileArray = files instanceof FileList ? Array.from(files) : Array.isArray(files) ? files : [];
    if (!fileArray.length) return;

    const validImages: File[] = [];
    const newPreviews: string[] = [];

    for (const file of fileArray) {
      // Allow all file types up to 10MB
      if (file.size > 10 * 1024 * 1024) continue;
      validImages.push(file);
      
      // Still create an object URL (the preview component will need to handle non-images gracefully)
      newPreviews.push(URL.createObjectURL(file));
    }

    setSelectedImages(prev => [...prev, ...validImages]);
    setImagePreviews(prev => [...prev, ...newPreviews]);
  };

  const removeImage = (index: number) => {
    setSelectedImages(prev => prev.filter((_, i) => i !== index));
    setImagePreviews(prev => {
      const newPreviews = prev.filter((_, i) => i !== index);
      URL.revokeObjectURL(prev[index]);
      return newPreviews;
    });
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    handleImageSelect(e.dataTransfer.files);
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const pastedFiles: File[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === 'file') {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) pastedFiles.push(file);
      }
    }
    if (pastedFiles.length > 0) handleImageSelect(pastedFiles);
  };

  const handleSend = () => {
    const messageToSend = input.trim();
    if (!messageToSend || isLoading) return;
    
    if (isListening) stopListening();
    
    sendMessage(messageToSend, selectedImages.length > 0 ? selectedImages : undefined);
    setInput('');
    setSelectedImages([]);
    setImagePreviews(prev => {
      prev.forEach(preview => URL.revokeObjectURL(preview));
      return [];
    });
    clearTranscript();
    
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoiceClick = () => {
    if (isListening) {
      stopListening();
      if (input.trim()) setTimeout(() => handleSend(), 100);
    } else {
      setInput('');
      clearTranscript();
      toggleListening();
    }
  };

  return (
    <div className="p-4 relative">
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

      <InputAreaAttachments selectedFiles={selectedImages} imagePreviews={imagePreviews} onRemove={removeImage} />

      {/* Main input container - Dark rounded style */}
      <div
        className={`
          relative flex flex-col gap-3 p-4 rounded-[32px]
          bg-[#212121] border border-white/5 transition-all duration-300 shadow-lg
          ${dragActive ? 'border-blue-400/50 ring-2 ring-blue-400/20 bg-[#2a2a2a]' : ''}
          ${isListening ? 'border-red-400/50 ring-2 ring-red-400/20' : ''}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        {/* Top Row: Sparkle + Textarea */}
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-1">
            <motion.div animate={isLoading ? { rotate: 360 } : { rotate: 0 }} transition={{ duration: 2, repeat: isLoading ? Infinity : 0, ease: 'linear' }}>
              <Sparkles className={`w-5 h-5 ${isLoading ? 'text-neutral-400' : 'text-white/60'}`} />
            </motion.div>
          </div>

          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            onPaste={handlePaste}
            placeholder={isListening ? "Speak now..." : "Ask Zenith anything..."}
            disabled={isLoading}
            className="flex-1 bg-transparent resize-none text-white/90 placeholder-white/40 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed max-h-32 text-lg py-0.5 leading-snug scrollbar-thin scrollbar-thumb-white/20"
            rows={1}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = Math.min(target.scrollHeight, 128) + 'px';
            }}
          />
        </div>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="*"
          onChange={(e) => handleImageSelect(e.target.files)}
          className="hidden"
        />

        {/* Bottom Row */}
        <div className="flex items-center justify-between mt-1 relative">
          
          {/* Left Actions */}
          <div className="flex items-center gap-2">
            {/* Add Files */}
            <motion.button
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className="p-2 rounded-full text-white/50 hover:text-white/90 hover:bg-white/10 transition-colors relative group"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Plus className="w-5 h-5" />
              {/* Tooltip */}
              <div className="absolute -top-10 left-1/2 -translate-x-1/2 px-2 py-1 bg-neutral-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                Add files
              </div>
            </motion.button>

            {/* Tools Button & Dropdown Container */}
            <div className="relative">
              <motion.button
                onClick={() => setShowToolsDropdown(!showToolsDropdown)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors text-sm font-medium ${showToolsDropdown ? 'bg-white/15 text-white/90' : 'text-white/50 hover:text-white/90 hover:bg-white/10'}`}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <SlidersHorizontal className="w-4 h-4" />
                Tools
              </motion.button>

              {/* Tools Dropdown */}
              <AnimatePresence>
                {showToolsDropdown && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute bottom-full left-0 mb-2 w-48 rounded-2xl bg-[#2a2a2a] border border-white/10 shadow-xl overflow-hidden z-50"
                  >
                    <div className="p-2 space-y-1">
                      <div className="px-3 py-1.5 text-xs text-white/40 font-medium">Tools</div>
                      <button
                        className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm text-white/90 hover:bg-white/10 transition-colors"
                        onClick={() => {
                          setActiveTool(activeTool === 'email' ? null : 'email');
                          setShowToolsDropdown(false);
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <Mail className="w-4 h-4 text-blue-400" />
                          Email
                        </div>
                        {activeTool === 'email' && <Check className="w-4 h-4 text-blue-400" />}
                      </button>

                      <button
                        className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm text-white/90 hover:bg-white/10 transition-colors"
                        onClick={() => {
                          setActiveTool(activeTool === 'meeting' ? null : 'meeting');
                          setShowToolsDropdown(false);
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-emerald-400" />
                          Meeting
                        </div>
                        {activeTool === 'meeting' && <Check className="w-4 h-4 text-emerald-400" />}
                      </button>

                      <button
                        className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm text-white/90 hover:bg-white/10 transition-colors"
                        onClick={() => {
                          setActiveTool(activeTool === 'task' ? null : 'task');
                          setShowToolsDropdown(false);
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <CheckSquare className="w-4 h-4 text-purple-400" />
                          Task
                        </div>
                        {activeTool === 'task' && <Check className="w-4 h-4 text-purple-400" />}
                      </button>

                      <button
                        className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm text-white/90 hover:bg-white/10 transition-colors"
                        onClick={() => {
                          setActiveTool(activeTool === 'notes' ? null : 'notes');
                          setShowToolsDropdown(false);
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-amber-400" />
                          Notes
                        </div>
                        {activeTool === 'notes' && <Check className="w-4 h-4 text-amber-400" />}
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Active Tool Pill */}
            <AnimatePresence>
              {activeTool && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8, x: -10 }}
                  animate={{ opacity: 1, scale: 1, x: 0 }}
                  exit={{ opacity: 0, scale: 0.8, x: -10 }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ml-1 border ${
                    activeTool === 'email' ? 'bg-blue-500/20 border-blue-500/30 text-blue-300' :
                    activeTool === 'meeting' ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300' :
                    activeTool === 'task' ? 'bg-purple-500/20 border-purple-500/30 text-purple-300' :
                    'bg-amber-500/20 border-amber-500/30 text-amber-300'
                  }`}
                >
                  {activeTool === 'email' && <Mail className="w-4 h-4" />}
                  {activeTool === 'meeting' && <Calendar className="w-4 h-4" />}
                  {activeTool === 'task' && <CheckSquare className="w-4 h-4" />}
                  {activeTool === 'notes' && <FileText className="w-4 h-4" />}
                  
                  {activeTool === 'email' ? 'Email' :
                   activeTool === 'meeting' ? 'Meeting' :
                   activeTool === 'task' ? 'Task' : 'Notes'}
                  
                  <button
                    onClick={() => setActiveTool(null)}
                    className="ml-1 p-0.5 rounded-full hover:bg-white/10 transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            {isSupported && (
              <motion.button
                onClick={handleVoiceClick}
                disabled={isLoading}
                className={`p-2 rounded-full transition-colors ${isListening ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 ring-2 ring-red-500/30' : 'text-white/50 hover:text-white/90 hover:bg-white/10'}`}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                title={isListening ? 'Stop & send' : 'Voice input'}
              >
                {isListening ? <Square className="w-5 h-5" fill="currentColor" /> : <Mic className="w-5 h-5" />}
              </motion.button>
            )}

            {/* Send or Stop Button */}
            <AnimatePresence mode="wait">
              {isLoading ? (
                <motion.button
                  key="stop-btn"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  onClick={stopMessage}
                  className="p-2 rounded-full bg-red-500/20 text-red-400 hover:bg-red-500/30 ring-2 ring-red-500/30 transition-colors ml-1 shadow-md"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  title="Stop generating"
                >
                  <Square className="w-5 h-5" fill="currentColor" />
                </motion.button>
              ) : (input.trim() || selectedImages.length > 0) ? (
                <motion.button
                  key="send-btn"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  onClick={handleSend}
                  className="p-2 rounded-full bg-white text-black hover:bg-neutral-200 transition-colors ml-1 shadow-md"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  title="Send message"
                >
                  <Send className="w-5 h-5" />
                </motion.button>
              ) : null}
            </AnimatePresence>
          </div>
        </div>

        {/* Drag over hint */}
        <AnimatePresence>
          {dragActive && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 bg-blue-500/10 rounded-[32px] flex items-center justify-center pointer-events-none">
              <div className="flex flex-col items-center gap-2 text-blue-300">
                <Upload className="w-6 h-6" />
                <p className="text-sm font-medium">Drop files here</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <p className="mt-2 text-xs text-white/30 text-center">
        Press Enter to send • Shift+Enter for new line
      </p>
    </div>
  );
}

export default InputArea;


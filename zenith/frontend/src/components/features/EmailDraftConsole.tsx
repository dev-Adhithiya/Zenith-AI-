import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useChat } from '../../contexts/ChatContext';
import { gmailAPI } from '../../lib/api';
import { sanitizeEmailHtml } from '../../lib/sanitizeHtml';
import { GlassPanel } from '../ui/GlassPanel';
import { GlassButton } from '../ui/GlassButton';
import { 
  X, 
  Undo, 
  Redo, 
  Type, 
  Bold, 
  Italic, 
  Underline, 
  Baseline, 
  AlignLeft, 
  ListOrdered, 
  List, 
  IndentDecrease, 
  IndentIncrease,
  ChevronDown,
  Paperclip,
  Link2,
  Smile,
  Image as ImageIcon,
  Lock,
  PenTool,
  MoreVertical,
  Trash2,
  Edit3
} from 'lucide-react';

export function EmailDraftConsole() {
  const { setIsEmailModeActive, emailDraft, setEmailDraft, sendMessage } = useChat();

  const [to, setTo] = useState(emailDraft?.to || '');
  const [subject, setSubject] = useState(emailDraft?.subject || '');
  const [body, setBody] = useState(emailDraft?.body || '');
  const [isSending, setIsSending] = useState(false);

  // Keep internal state synced if draft changes externally (e.g. AI updates it)
  useEffect(() => {
    if (emailDraft) {
      if (emailDraft.to !== to) setTo(emailDraft.to);
      if (emailDraft.subject !== subject) setSubject(emailDraft.subject);
      if (emailDraft.body !== body) setBody(emailDraft.body);
    }
  }, [emailDraft?.to, emailDraft?.subject, emailDraft?.body]);

  const updateDraft = (updates: Partial<typeof emailDraft>) => {
    const base = emailDraft || { to: '', subject: '', body: '' };
    setEmailDraft({ ...base, ...updates });
  };

  const { data: originalEmail, isLoading: isLoadingOriginal } = useQuery({
    queryKey: ['gmail', 'message', emailDraft?.originalMessageId],
    queryFn: () => gmailAPI.getMessage(emailDraft!.originalMessageId!),
    enabled: !!emailDraft?.originalMessageId,
  });

  const handleClose = () => {
    setIsEmailModeActive(false);
  };

  const handleDiscard = () => {
    setEmailDraft(null);
    setTo('');
    setSubject('');
    setBody('');
  };

  const handleSend = async () => {
    if (!to || (!subject && !body)) return;
    setIsSending(true);
    try {
      await gmailAPI.sendEmail({
        to: to.split(',').map(s => s.trim()).filter(Boolean),
        subject: subject || '(No Subject)',
        body,
        html_body: body.replace(/\n/g, '<br/>'),
        reply_to_thread_id: emailDraft?.originalMessageId
      });
      handleDiscard();
      handleClose();
    } catch (e) {
      console.error("Failed to send email", e);
      alert("Failed to send email. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  const handleGenerateSubject = () => {
    sendMessage("Please generate a catchy and appropriate subject for my current email draft. Update the draft state directly.");
  };

  const handleGenerateBody = () => {
    sendMessage("Please generate or refine the body of my current email draft based on our recent context and the original email. Update the draft state directly.");
  };

  return (
    <GlassPanel className="flex-1 flex flex-col h-full overflow-hidden bg-[#1e1e1e]/90">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-black/20">
        <h2 className="text-sm font-medium text-white/90">
          Zenith AI • Email Drafting Console
        </h2>
        <button 
          onClick={handleClose}
          className="flex items-center gap-1 px-2 py-1 rounded-md text-xs text-white/60 hover:bg-white/10 hover:text-white/90 transition-colors"
        >
          Close <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col p-4 gap-4">
        {/* Original Email Context (if replying) */}
        {emailDraft?.originalMessageId && (
          <div className="rounded-xl border border-white/10 bg-black/20 overflow-hidden flex flex-col max-h-[300px] flex-shrink-0">
            <div className="px-3 py-2 border-b border-white/10 bg-white/5 text-xs text-white/50 font-medium flex justify-between">
              <span>Original Message</span>
              {isLoadingOriginal && <span className="animate-pulse">Loading...</span>}
            </div>
            <div className="p-3 overflow-y-auto custom-scrollbar flex-1">
              {originalEmail?.body_html ? (
                <div className="bg-white rounded-lg p-2">
                  <iframe
                    srcDoc={sanitizeEmailHtml(originalEmail.body_html)}
                    title="Original Email HTML content"
                    className="w-full min-h-[200px] bg-white border-0"
                    sandbox=""
                    referrerPolicy="no-referrer"
                  />
                </div>
              ) : (
                <div className="text-sm text-white/80 whitespace-pre-wrap">
                  {originalEmail?.body_text || originalEmail?.snippet || 'No context loaded.'}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Email Form */}
        <div className="flex flex-col gap-3 flex-1 min-h-[400px]">
          {/* To Row */}
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-black/20 border border-white/5">
            <span className="text-sm text-white/40 font-medium w-12">To</span>
            <input 
              type="text" 
              value={to}
              onChange={(e) => {
                setTo(e.target.value);
                updateDraft({ to: e.target.value });
              }}
              className="flex-1 bg-transparent border-none outline-none text-sm text-white/90"
              placeholder="recipient@example.com"
            />
          </div>

          {/* Subject Row */}
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-black/20 border border-white/5">
            <span className="text-sm text-white/40 font-medium w-12">Subject</span>
            <input 
              type="text" 
              value={subject}
              onChange={(e) => {
                setSubject(e.target.value);
                updateDraft({ subject: e.target.value });
              }}
              className="flex-1 bg-transparent border-none outline-none text-sm text-white/90"
            />
            <GlassButton variant="ghost" size="sm" className="text-xs py-1 h-auto" onClick={handleGenerateSubject}>
              Generate Subject
            </GlassButton>
          </div>

          {/* Message Area */}
          <div className="flex-1 flex flex-col rounded-xl border border-white/10 bg-black/20 overflow-hidden">
            <textarea 
              value={body}
              onChange={(e) => {
                setBody(e.target.value);
                updateDraft({ body: e.target.value });
              }}
              className="flex-1 bg-transparent border-none outline-none text-sm text-white/90 p-4 resize-none custom-scrollbar min-h-[200px]"
              placeholder="Write your email here..."
            />
            
            {/* Message Actions */}
            <div className="flex items-center gap-2 px-4 py-3 bg-black/10">
              <GlassButton variant="ghost" size="sm" className="text-xs bg-white/5 hover:bg-white/10" onClick={handleGenerateBody}>
                [Generate Message]
              </GlassButton>
              <GlassButton variant="ghost" size="sm" className="text-xs bg-white/5 hover:bg-white/10">
                <Edit3 className="w-3.5 h-3.5 mr-1" /> Edit
              </GlassButton>
            </div>

            {/* Rich Text Toolbar */}
            <div className="px-3 py-2 m-2 rounded-full bg-[#f2f6fc] text-neutral-600 flex items-center justify-between shadow-sm overflow-x-auto custom-scrollbar flex-shrink-0">
              <div className="flex items-center gap-1 shrink-0">
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors"><Undo className="w-4 h-4" /></button>
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors"><Redo className="w-4 h-4" /></button>
                <div className="w-px h-4 bg-neutral-300 mx-1" />
                <button className="px-2 py-1.5 hover:bg-neutral-200 rounded transition-colors text-sm font-medium flex items-center gap-1">
                  Sans Serif <ChevronDown className="w-3 h-3" />
                </button>
                <div className="w-px h-4 bg-neutral-300 mx-1" />
                <button className="px-2 py-1.5 hover:bg-neutral-200 rounded transition-colors flex items-center gap-1">
                  <Type className="w-4 h-4" /> <ChevronDown className="w-3 h-3" />
                </button>
                <div className="w-px h-4 bg-neutral-300 mx-1" />
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors"><Bold className="w-4 h-4" /></button>
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors"><Italic className="w-4 h-4 italic" /></button>
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors"><Underline className="w-4 h-4" /></button>
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors flex items-center gap-0.5"><Baseline className="w-4 h-4" /> <ChevronDown className="w-3 h-3" /></button>
                <div className="w-px h-4 bg-neutral-300 mx-1" />
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors flex items-center gap-0.5"><AlignLeft className="w-4 h-4" /> <ChevronDown className="w-3 h-3" /></button>
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors"><ListOrdered className="w-4 h-4" /></button>
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors"><List className="w-4 h-4" /></button>
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors"><IndentDecrease className="w-4 h-4" /></button>
                <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors"><IndentIncrease className="w-4 h-4" /></button>
              </div>
              <button className="p-1.5 hover:bg-neutral-200 rounded transition-colors shrink-0">
                <ChevronDown className="w-4 h-4" />
              </button>
            </div>
            
            {/* Bottom Action Bar */}
            <div className="px-4 py-3 bg-[#212121] flex items-center justify-between border-t border-white/5 flex-shrink-0">
              <div className="flex items-center gap-3">
                {/* Send Button Group */}
                <div className="flex items-center rounded-full bg-[#0b57d0] hover:bg-[#0b57d0]/90 transition-colors shadow-md">
                  <button 
                    onClick={handleSend}
                    disabled={isSending || !to}
                    className="px-5 py-2 text-white text-sm font-medium rounded-l-full disabled:opacity-50"
                  >
                    {isSending ? 'Sending...' : 'Send'}
                  </button>
                  <div className="w-px h-6 bg-white/20" />
                  <button className="px-2 py-2 text-white rounded-r-full hover:bg-white/10">
                    <ChevronDown className="w-4 h-4" />
                  </button>
                </div>
                
                {/* Primary Actions */}
                <div className="flex items-center gap-1 text-white/60">
                  <button className="p-2 rounded-full bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors" title="Formatting options">
                    <Type className="w-5 h-5" />
                  </button>
                  <button className="p-2 rounded-full hover:bg-white/10 transition-colors"><Paperclip className="w-5 h-5" /></button>
                  <button className="p-2 rounded-full hover:bg-white/10 transition-colors"><Link2 className="w-5 h-5" /></button>
                  <button className="p-2 rounded-full hover:bg-white/10 transition-colors"><Smile className="w-5 h-5" /></button>
                  <button className="p-2 rounded-full hover:bg-white/10 transition-colors"><ImageIcon className="w-5 h-5" /></button>
                  <button className="p-2 rounded-full hover:bg-white/10 transition-colors"><Lock className="w-5 h-5" /></button>
                  <button className="p-2 rounded-full hover:bg-white/10 transition-colors"><PenTool className="w-5 h-5" /></button>
                  <button className="p-2 rounded-full hover:bg-white/10 transition-colors"><MoreVertical className="w-5 h-5" /></button>
                </div>
              </div>

              {/* Right Aligned Trash */}
              <button 
                onClick={handleDiscard}
                className="p-2 rounded-full text-white/40 hover:text-red-400 hover:bg-red-500/10 transition-colors" 
                title="Discard draft"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </GlassPanel>
  );
}

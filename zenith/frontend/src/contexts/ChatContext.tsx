import { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from 'react';
import { chatAPI, type ChatMessage, type ChatResponse } from '../lib/api';
import { useAuth } from './AuthContext';

export interface EmailDraft {
  to: string;
  subject: string;
  body: string;
  originalMessageId?: string;
}

interface ChatContextType {
  messages: ChatMessage[];
  sessionId: string | null;
  isLoading: boolean;
  error: string | null;
  isEmailModeActive: boolean;
  setIsEmailModeActive: (active: boolean) => void;
  emailDraft: EmailDraft | null;
  setEmailDraft: (draft: EmailDraft | null) => void;
  sendMessage: (content: string, images?: File[]) => Promise<void>;
  addLocalMessage: (message: Omit<ChatMessage, 'timestamp'>) => void;
  createNewSession: () => void;
  clearMessages: () => void;
  loadSession: (sessionId: string) => Promise<void>;
  stopMessage: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

function revokeMessageImageUrls(messages: ChatMessage[]) {
  messages.forEach((message) => {
    message.images?.forEach((image) => {
      if (image.src.startsWith('blob:')) {
        URL.revokeObjectURL(image.src);
      }
    });
  });
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isEmailModeActive, setIsEmailModeActive] = useState(false);
  const [emailDraft, setEmailDraft] = useState<EmailDraft | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Create initial session when authenticated
  useEffect(() => {
    if (!isAuthenticated) return;
    
    const initSession = async () => {
      try {
        const { session_id } = await chatAPI.createSession();
        setSessionId(session_id);
      } catch (err) {
        console.error('Failed to create session:', err);
      }
    };

    initSession();
  }, [isAuthenticated]);

  const loadSession = useCallback(async (targetSessionId: string) => {
    try {
      setIsLoading(true);
      setError(null);

      const data = await chatAPI.getSessionMessages(targetSessionId);
      const sessionMessages = data.messages || [];
      
      // Convert to ChatMessage format
      const formattedMessages: ChatMessage[] = sessionMessages.map((msg: any) => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp,
        metadata: msg.metadata
      }));
      
      setMessages((prev) => {
        revokeMessageImageUrls(prev);
        return formattedMessages;
      });
      setSessionId(targetSessionId);
    } catch (err) {
      console.error('Failed to load session:', err);
      setError('Failed to load conversation history');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sendMessage = useCallback(async (content: string, images?: File[]) => {
    if (!content.trim() || isLoading) return;

    setError(null);
    setIsLoading(true);

    // Add user message with images
    const userMessage: ChatMessage = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      images: images
        ? images.map((file, index) => ({
            id: `${Date.now()}-${index}`,
            src: URL.createObjectURL(file),
            filename: file.name,
          }))
        : undefined,
    };
    setMessages(prev => [...prev, userMessage]);

    abortControllerRef.current = new AbortController();

    try {
      // Send to backend, including emailDraft if we are in email mode
      const payloadDraft = isEmailModeActive && emailDraft ? emailDraft : undefined;
      const response: ChatResponse = await chatAPI.sendMessage(
        content, 
        sessionId || undefined, 
        images, 
        payloadDraft, 
        abortControllerRef.current.signal
      );

      // Auto-trigger email mode if intent is email-related
      const emailIntents = ['send_email', 'compose_email', 'draft_email'];
      if (emailIntents.includes(response.intent?.intent)) {
        setIsEmailModeActive(true);
        // Initialize a blank draft if none exists yet
        if (!emailDraft) {
          setEmailDraft({ to: '', subject: '', body: '' });
        }
      }

      // Update session ID if new
      if (response.session_id && response.session_id !== sessionId) {
        setSessionId(response.session_id);
      }

      // Intercept <email_draft> XML blocks
      let responseContent = response.response;
      const draftMatch = responseContent.match(/<email_draft>([\s\S]*?)<\/email_draft>/);
      if (draftMatch) {
        try {
          let jsonString = draftMatch[1].trim();
          if (jsonString.startsWith('```json')) {
            jsonString = jsonString.replace(/^```json\n?/, '').replace(/\n?```$/, '').trim();
          } else if (jsonString.startsWith('```')) {
            jsonString = jsonString.replace(/^```\n?/, '').replace(/\n?```$/, '').trim();
          }
          const draftUpdates = JSON.parse(jsonString);
          setEmailDraft(prev => prev ? { ...prev, ...draftUpdates } : draftUpdates);
          setIsEmailModeActive(true); // Ensure mode is active if we receive draft updates
        } catch (e) {
          console.error("Failed to parse email_draft from response", e);
        }
        // Remove the block from the visible message
        responseContent = responseContent.replace(/<email_draft>[\s\S]*?<\/email_draft>/g, '').trim();
      }

      // Add assistant response
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: responseContent,
        timestamp: new Date().toISOString(),
        metadata: {
          suggestions: response.suggestions,
          intent: response.intent,
          execution_success: response.execution_success,
          requires_confirmation: response.requires_confirmation,
          pending_plan: response.pending_plan
        },
      };
      setMessages(prev => [...prev, assistantMessage]);

      // Note: We don't set error here even if response.error exists
      // because the response already contains the error message in content
      
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('[Chat] Message generation stopped by user');
        return;
      }
      
      const raw = err instanceof Error ? err.message : String(err);
      const errorMsg =
        raw.length > 200 ? 'Unable to reach the server. Please try again.' : raw || 'Failed to send message';
      setError(errorMsg);
      
      // Add error message
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: `Sorry, I couldn't process your request. Please check your connection and try again.`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [sessionId, isLoading, isEmailModeActive, emailDraft]);

  const addLocalMessage = useCallback((message: Omit<ChatMessage, 'timestamp'>) => {
    setMessages(prev => [...prev, { ...message, timestamp: new Date().toISOString() }]);
  }, []);

  const createNewSession = useCallback(() => {
    setMessages((prev) => {
      revokeMessageImageUrls(prev);
      return [];
    });
    setSessionId(null);
    setError(null);

    // Create new session
    chatAPI.createSession().then(({ session_id }) => {
      setSessionId(session_id);
    }).catch(err => {
      console.error('Failed to create new session:', err);
    });
  }, []);

  const clearMessages = useCallback(() => {
    setMessages((prev) => {
      revokeMessageImageUrls(prev);
      return [];
    });
    setError(null);
  }, []);

  const stopMessage = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  }, []);

  const value = {
    messages,
    sessionId,
    isLoading,
    error,
    isEmailModeActive,
    setIsEmailModeActive,
    emailDraft,
    setEmailDraft,
    sendMessage,
    addLocalMessage,
    createNewSession,
    clearMessages,
    loadSession,
    stopMessage,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}

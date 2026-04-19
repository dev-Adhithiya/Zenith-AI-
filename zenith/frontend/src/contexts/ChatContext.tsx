import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { chatAPI, type ChatMessage, type ChatResponse } from '../lib/api';
import { useAuth } from './AuthContext';

interface ChatContextType {
  messages: ChatMessage[];
  sessionId: string | null;
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string, images?: File[]) => Promise<void>;
  createNewSession: () => void;
  clearMessages: () => void;
  loadSession: (sessionId: string) => Promise<void>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      
      // Fetch messages for this session from backend
      const response = await fetch(`/chat/sessions/${targetSessionId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to load session');
      
      const data = await response.json();
      const sessionMessages = data.messages || [];
      
      // Convert to ChatMessage format
      const formattedMessages: ChatMessage[] = sessionMessages.map((msg: any) => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp,
        metadata: msg.metadata
      }));
      
      setMessages(formattedMessages);
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

    try {
      // Send to backend
      const response: ChatResponse = await chatAPI.sendMessage(content, sessionId || undefined, images);

      // Update session ID if new
      if (response.session_id && response.session_id !== sessionId) {
        setSessionId(response.session_id);
      }

      // Add assistant response
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
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
      
    } catch (err: unknown) {
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
    }
  }, [sessionId, isLoading]);

  const createNewSession = useCallback(() => {
    setMessages([]);
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
    setMessages([]);
    setError(null);
  }, []);

  const value = {
    messages,
    sessionId,
    isLoading,
    error,
    sendMessage,
    createNewSession,
    clearMessages,
    loadSession,
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

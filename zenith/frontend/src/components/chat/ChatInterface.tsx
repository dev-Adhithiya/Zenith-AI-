import { GlassPanel } from '../ui/GlassPanel';
import { MessageList } from './MessageList';
import { InputArea } from './InputArea';
import { useAuth } from '../../contexts/AuthContext';
import { GlassButton } from '../ui/GlassButton';
import { Sparkles } from 'lucide-react';

export function ChatInterface() {
  const { isAuthenticated, login, isLoading: authLoading } = useAuth();

  if (!isAuthenticated) {
    return (
      <GlassPanel className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-neutral-500/30 to-neutral-400/30 border border-neutral-400/30 flex items-center justify-center">
            <Sparkles className="w-10 h-10 text-neutral-400" />
          </div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-neutral-400 to-neutral-300 bg-clip-text text-transparent mb-3">
            Welcome to Zenith
          </h2>
          <p className="text-white/60 mb-6">
            Your intelligent AI assistant powered by Gemini 2.5 Flash. Connect your Google account to manage
            emails, calendar, tasks, notes, and more. Ask me anything!
          </p>
          <GlassButton
            variant="primary"
            size="lg"
            onClick={login}
            isLoading={authLoading}
            className="w-full"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Sign in with Google
          </GlassButton>
          
          <div className="mt-8 p-4 rounded-xl bg-white/5 border border-white/10">
            <p className="text-xs text-white/50 mb-2">✨ Features:</p>
            <div className="grid grid-cols-2 gap-2 text-xs text-white/40">
              <div>• Smart calendar management</div>
              <div>• Email automation</div>
              <div>• Task organization</div>
              <div>• Knowledge base</div>
            </div>
          </div>
        </div>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel className="flex-1 flex flex-col overflow-hidden">
      {/* Chat Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-neutral-500/30 to-neutral-400/30 border border-neutral-400/30 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-neutral-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold bg-gradient-to-r from-neutral-400 to-neutral-300 bg-clip-text text-transparent">
              Zenith AI
            </h1>
            <p className="text-xs text-white/40">
              Powered by Gemini 2.5 Flash
            </p>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <MessageList />

      {/* Input Area */}
      <InputArea />
    </GlassPanel>
  );
}

export default ChatInterface;

import { useState } from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { ChatProvider } from './contexts/ChatContext';
import { VoiceProvider } from './contexts/VoiceContext';
import { SettingsProvider } from './contexts/SettingsContext';
import { MeshGradient } from './components/background/MeshGradient';
import { Sidebar } from './components/sidebar/Sidebar';
import { ChatInterface } from './components/chat/ChatInterface';
import { BriefingPanel } from './components/features/BriefingPanel';
import { EmailPanel } from './components/features/EmailPanel';
import { CalendarPanel } from './components/features/CalendarPanel';
import { TasksPanel } from './components/features/TasksPanel';
import { NotesPanel } from './components/features/NotesPanel';
import { GlassPanel } from './components/ui/GlassPanel';
import { PanelRight, PanelRightClose } from 'lucide-react';

function AppContent() {
  const [isRightSidebarCollapsed, setIsRightSidebarCollapsed] = useState(false);

  return (
    <div className="relative h-screen w-screen overflow-hidden">
      {/* Animated background */}
      <MeshGradient />

      {/* Main layout */}
      <div className="relative z-10 flex h-full p-4 gap-4">
        {/* Sidebar */}
        <Sidebar />

        {/* Chat area */}
        <div className="flex-1 flex gap-4">
          <ChatInterface />
          
          {/* Feature panels (right side) - Collapsible */}
          {isRightSidebarCollapsed ? (
            <GlassPanel className="w-12 flex flex-col items-center py-4">
              <button
                onClick={() => setIsRightSidebarCollapsed(false)}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                title="Expand panel"
              >
                <PanelRight className="w-5 h-5 text-white/60" />
              </button>
            </GlassPanel>
          ) : (
            <div className="w-80 flex flex-col gap-4 overflow-y-auto">
              {/* Collapse button */}
              <div className="flex justify-end">
                <button
                  onClick={() => setIsRightSidebarCollapsed(true)}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                  title="Collapse panel"
                >
                  <PanelRightClose className="w-5 h-5 text-white/60" />
                </button>
              </div>
              <BriefingPanel />
              <EmailPanel />
              <CalendarPanel />
              <TasksPanel />
              <NotesPanel />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <ChatProvider>
        <VoiceProvider>
          <SettingsProvider>
            <AppContent />
          </SettingsProvider>
        </VoiceProvider>
      </ChatProvider>
    </AuthProvider>
  );
}

export default App;

import { AuthProvider } from './contexts/AuthContext';
import { ChatProvider } from './contexts/ChatContext';
import { VoiceProvider } from './contexts/VoiceContext';
import { MeshGradient } from './components/background/MeshGradient';
import { Sidebar } from './components/sidebar/Sidebar';
import { ChatInterface } from './components/chat/ChatInterface';
import { EmailPanel } from './components/features/EmailPanel';
import { CalendarPanel } from './components/features/CalendarPanel';
import { TasksPanel } from './components/features/TasksPanel';
import { NotesPanel } from './components/features/NotesPanel';

function App() {
  return (
    <AuthProvider>
      <ChatProvider>
        <VoiceProvider>
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
                
                {/* Feature panels (right side) */}
                <div className="w-80 flex flex-col gap-4 overflow-y-auto">
                  <EmailPanel />
                  <CalendarPanel />
                  <TasksPanel />
                  <NotesPanel />
                </div>
              </div>
            </div>
          </div>
        </VoiceProvider>
      </ChatProvider>
    </AuthProvider>
  );
}

export default App;

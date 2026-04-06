import { createContext, useContext, useState, ReactNode } from 'react';

interface SettingsContextType {
  speakMode: boolean;
  setSpeakMode: (enabled: boolean) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [speakMode, setSpeakMode] = useState(false);

  const value = {
    speakMode,
    setSpeakMode,
  };

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}

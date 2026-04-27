import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

interface SettingsContextType {
  speakMode: boolean;
  setSpeakMode: (enabled: boolean) => void;
  isDarkMode: boolean;
  setIsDarkMode: (enabled: boolean) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

const SPEAK_MODE_STORAGE_KEY = 'zenith:speak-mode';
const THEME_STORAGE_KEY = 'zenith:dark-mode';

function readStoredBoolean(key: string, fallback: boolean): boolean {
  const stored = localStorage.getItem(key);
  if (stored === null) {
    return fallback;
  }
  return stored === 'true';
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [speakMode, setSpeakMode] = useState(() => readStoredBoolean(SPEAK_MODE_STORAGE_KEY, false));
  const [isDarkMode, setIsDarkMode] = useState(() => readStoredBoolean(THEME_STORAGE_KEY, true));

  useEffect(() => {
    localStorage.setItem(SPEAK_MODE_STORAGE_KEY, String(speakMode));
  }, [speakMode]);

  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, String(isDarkMode));
    document.documentElement.classList.toggle('light', !isDarkMode);
  }, [isDarkMode]);

  return (
    <SettingsContext.Provider
      value={{
        speakMode,
        setSpeakMode,
        isDarkMode,
        setIsDarkMode,
      }}
    >
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

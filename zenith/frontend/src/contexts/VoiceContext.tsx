import { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from 'react';

interface VoiceContextType {
  isListening: boolean;
  isSpeaking: boolean;
  isSupported: boolean;
  transcript: string;
  startListening: () => void;
  stopListening: () => void;
  speak: (text: string) => void;
  stopSpeaking: () => void;
  toggleListening: () => void;
  clearTranscript: () => void;
}

const VoiceContext = createContext<VoiceContextType | undefined>(undefined);

export function VoiceProvider({ children }: { children: ReactNode }) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [recognition, setRecognition] = useState<any>(null);
  const finalizedTextRef = useRef('');
  const [synthesis] = useState<SpeechSynthesis>(window.speechSynthesis);

  // Check browser support
  const isSupported = 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;

  // Initialize speech recognition
  useEffect(() => {
    if (!isSupported) return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognitionInstance = new SpeechRecognition();

    recognitionInstance.continuous = true;  // Keep listening until stopped
    recognitionInstance.interimResults = true;
    recognitionInstance.lang = 'en-US';

    recognitionInstance.onresult = (event: any) => {
      let currentFinal = '';
      let currentInterim = '';

      // Process only new chunks so old transcript doesn't repeat.
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          currentFinal += ` ${result[0].transcript}`;
        } else {
          currentInterim += ` ${result[0].transcript}`;
        }
      }

      if (currentFinal.trim()) {
        finalizedTextRef.current = `${finalizedTextRef.current} ${currentFinal}`.trim();
      }

      const displayText = `${finalizedTextRef.current} ${currentInterim}`.trim();
      setTranscript(displayText);
    };

    recognitionInstance.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      if (event.error !== 'aborted') {
        setIsListening(false);
      }
    };

    recognitionInstance.onend = () => {
      // Only stop if we're not supposed to be listening
      // This prevents auto-stop on pause
    };

    setRecognition(recognitionInstance);

    return () => {
      if (recognitionInstance) {
        try {
          recognitionInstance.stop();
        } catch (e) {
          // Ignore errors on cleanup
        }
      }
    };
  }, [isSupported]);

  const startListening = useCallback(() => {
    if (!recognition || isListening) return;

    try {
      // Reset per-session transcript state.
      finalizedTextRef.current = '';
      setTranscript('');
      recognition.start();
      setIsListening(true);
    } catch (error) {
      console.error('Failed to start listening:', error);
    }
  }, [recognition, isListening]);

  const stopListening = useCallback(() => {
    if (!recognition || !isListening) return;

    try {
      recognition.stop();
      setIsListening(false);
    } catch (error) {
      console.error('Failed to stop listening:', error);
    }
  }, [recognition, isListening]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  const speak = useCallback((text: string) => {
    if (!synthesis) return;

    // Cancel any ongoing speech
    synthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    synthesis.speak(utterance);
  }, [synthesis]);

  const stopSpeaking = useCallback(() => {
    if (!synthesis) return;
    synthesis.cancel();
    setIsSpeaking(false);
  }, [synthesis]);

  const clearTranscript = useCallback(() => {
    finalizedTextRef.current = '';
    setTranscript('');
  }, []);

  const value = {
    isListening,
    isSpeaking,
    isSupported,
    transcript,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
    toggleListening,
    clearTranscript,
  };

  return <VoiceContext.Provider value={value}>{children}</VoiceContext.Provider>;
}

export function useVoice() {
  const context = useContext(VoiceContext);
  if (context === undefined) {
    throw new Error('useVoice must be used within a VoiceProvider');
  }
  return context;
}

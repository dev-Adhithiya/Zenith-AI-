import { useState, useEffect } from 'react';
import { briefingAPI, type Briefing } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

interface UseBriefingReturn {
  briefing: Briefing | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Custom hook to fetch and manage login briefing.
 * 
 * Fetches briefing once when user is authenticated.
 * Manual refresh only via refetch button.
 * Provides loading state, error handling, and manual refetch capability.
 */
export function useBriefing(): UseBriefingReturn {
  const { isAuthenticated } = useAuth();
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasFetched, setHasFetched] = useState(false);

  const fetchBriefing = async () => {
    if (!isAuthenticated) return;

    try {
      setIsLoading(true);
      setError(null);
      
      const data = await briefingAPI.getBriefing();
      setBriefing(data);
      setHasFetched(true);
    } catch (err) {
      console.error('Failed to fetch briefing:', err);
      setError(err instanceof Error ? err.message : 'Failed to load briefing');
      
      // Set a fallback briefing so UI doesn't break
      setBriefing({
        status: 'error',
        title: 'Your Executive Summary',
        content: 'Welcome back! I\'m ready to help with your calendar, emails, and tasks.',
        error: err instanceof Error ? err.message : 'Unknown error'
      });
      setHasFetched(true);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch briefing once on login/authentication
  useEffect(() => {
    if (isAuthenticated && !hasFetched) {
      fetchBriefing();
    }
  }, [isAuthenticated, hasFetched]);

  return {
    briefing,
    isLoading,
    error,
    refetch: fetchBriefing
  };
}

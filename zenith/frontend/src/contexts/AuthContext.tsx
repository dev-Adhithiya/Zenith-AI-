import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authAPI, type User } from '../lib/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Handle OAuth callback - parse auth data from URL fragment
  useEffect(() => {
    const handleAuthCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      const authSuccess = params.get('auth_success');
      const authError = params.get('auth_error');

      if (authError) {
        console.error('Authentication error:', decodeURIComponent(authError));
        setIsLoading(false);
        // Clean URL
        window.history.replaceState({}, document.title, '/');
        return;
      }

      if (authSuccess === 'true') {
        // Parse auth data from URL fragment
        const hash = window.location.hash.substring(1); // Remove the #
        if (hash) {
          const hashParams = new URLSearchParams(hash);
          const accessToken = hashParams.get('access_token');
          const userJson = hashParams.get('user');

          if (accessToken && userJson) {
            try {
              // Store token
              localStorage.setItem('access_token', accessToken);
              
              // Parse user data
              const userData = JSON.parse(userJson);
              localStorage.setItem('user', JSON.stringify(userData));
              setUser(userData as User);
              
              console.log('Authentication successful!');
            } catch (error) {
              console.error('Failed to parse auth data:', error);
            }
          }
        }
        
        // Clean URL
        window.history.replaceState({}, document.title, '/');
        setIsLoading(false);
        return;
      }

      // Check if user is already logged in
      try {
        const token = localStorage.getItem('access_token');
        if (token) {
          // Try to get current user from API
          try {
            const currentUser = await authAPI.getCurrentUser();
            setUser(currentUser);
          } catch (error) {
            // If API fails, try to use cached user data
            const cachedUser = localStorage.getItem('user');
            if (cachedUser) {
              setUser(JSON.parse(cachedUser));
            } else {
              // Token invalid, clear storage
              localStorage.removeItem('access_token');
              localStorage.removeItem('user');
            }
          }
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
      } finally {
        setIsLoading(false);
      }
    };

    handleAuthCallback();
  }, []);

  const login = async () => {
    try {
      const { authorization_url } = await authAPI.login();
      window.location.href = authorization_url;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = () => {
    authAPI.logout();
    setUser(null);
    window.location.reload();
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

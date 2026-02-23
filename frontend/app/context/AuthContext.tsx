'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { UserResponse } from '@/types/api';
import { login as apiLogin, getMe, setToken, clearToken, getToken } from '@/lib/api';

interface AuthState {
  user: UserResponse | null;
  loading: boolean;
  error: string | null;
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    error: null,
  });

  // On mount: if a token exists, try to fetch the current user
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setState({ user: null, loading: false, error: null });
      return;
    }

    getMe()
      .then((user) => setState({ user, loading: false, error: null }))
      .catch(() => {
        clearToken();
        setState({ user: null, loading: false, error: null });
      });
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const token = await apiLogin({ username, password });
      setToken(token.access_token);
      const user = await getMe();
      setState({ user, loading: false, error: null });
    } catch (err) {
      clearToken();
      const message = err instanceof Error ? err.message : 'Login failed';
      setState({ user: null, loading: false, error: message });
      throw err;
    }
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setState({ user: null, loading: false, error: null });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
}

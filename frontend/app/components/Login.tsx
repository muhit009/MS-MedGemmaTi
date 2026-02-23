'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Activity, ChevronLeft } from 'lucide-react';
import { useAuth } from '@/app/context/AuthContext';

interface LoginProps {
  onBack?: () => void;
}

export default function Login({ onBack }: LoginProps) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
    } catch {
      setError('Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen w-full flex items-center justify-center bg-background font-sans">
      <div className="w-full max-w-sm space-y-8">
        {/* Back link */}
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className="h-3 w-3" /> Back
          </button>
        )}

        {/* Logo */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 text-2xl font-semibold tracking-tight text-primary">
            <Activity className="h-7 w-7" />
            MedGemma
          </div>
          <span className="block text-[10px] uppercase font-medium text-muted-foreground tracking-widest">
            Clinical Suite
          </span>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="med-panel p-6 space-y-5">
          <div className="space-y-1.5">
            <label htmlFor="username" className="text-xs font-medium text-foreground">
              Username
            </label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="dr.smith"
              className="h-10"
              autoFocus
              required
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="text-xs font-medium text-foreground">
              Password
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="h-10"
              required
            />
          </div>

          {error && (
            <p className="text-xs text-destructive text-center">{error}</p>
          )}

          <Button type="submit" className="w-full h-11" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </Button>
        </form>

        <p className="text-[10px] text-center text-muted-foreground leading-tight">
          Authorized personnel only. All access is logged for HIPAA compliance.
        </p>
      </div>
    </div>
  );
}

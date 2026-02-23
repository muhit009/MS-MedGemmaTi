'use client';

import { useState } from 'react';
import { useAuth } from '@/app/context/AuthContext';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import IntroPage from './components/IntroPage';
import { Activity } from 'lucide-react';

export default function Home() {
  const { user, loading } = useAuth();
  const [showManualLogin, setShowManualLogin] = useState(false);

  if (loading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-background">
        <Activity className="h-8 w-8 text-primary animate-pulse" />
      </div>
    );
  }

  if (!user) {
    return showManualLogin
      ? <Login onBack={() => setShowManualLogin(false)} />
      : <IntroPage onStaffLogin={() => setShowManualLogin(true)} />;
  }

  return <Dashboard />;
}

'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Activity, Loader2, ChevronRight } from 'lucide-react';
import { useAuth } from '@/app/context/AuthContext';

interface IntroPageProps {
  onStaffLogin: () => void;
}

export default function IntroPage({ onStaffLogin }: IntroPageProps) {
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleContinue = async () => {
    setLoading(true);
    setError('');
    try {
      await login('dr.smith', 'password');
    } catch {
      setError('Could not connect. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen w-full flex items-center justify-center bg-background font-sans">
      <div className="w-full max-w-md space-y-8">
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

        {/* Card */}
        <div className="med-panel p-6 space-y-5">
          {/* Badge */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] uppercase font-bold tracking-widest text-primary px-2 py-0.5 border border-primary/30 rounded-full bg-primary/5">
              Live Demo
            </span>
            <span className="text-[10px] text-muted-foreground">Google MedGemma Impact Challenge</span>
          </div>

          <ul className="space-y-3 text-sm text-foreground/80">
            <li className="flex gap-2">
              <span className="text-primary shrink-0 font-medium">1.</span>
              <span>
                We fine-tuned <strong>MedGemma-4B</strong> to reason temporally across sequential
                chest X-rays, catching deterioration that the base model misses.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-primary shrink-0 font-medium">2.</span>
              <span>
                Pre-loaded demo patients showcase key cases: dangerous misses caught, temporal
                coherence, hallucination prevention.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-primary shrink-0 font-medium">3.</span>
              <span>
                <strong>Analysis mode</strong> runs a structured PRIOR→CURRENT comparison.{' '}
                <strong>Discussion mode</strong> answers follow-up questions conversationally. Both
                auto-switch and can be manually pinned.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-amber-500 shrink-0">⚠</span>
              <span>
                <strong>Backend cold start:</strong> first page load may take ~30s while the API server wakes up.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-amber-500 shrink-0">⚠</span>
              <span>
                <strong>Model cold start:</strong> first AI response may take ~1 minute — the model runs on a serverless GPU to minimize cost.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-primary shrink-0 font-medium">4.</span>
              <span>Browse existing demo patients or create a new one to try your own queries.</span>
            </li>
          </ul>

          {error && <p className="text-xs text-destructive text-center">{error}</p>}

          <Button className="w-full h-11" onClick={handleContinue} disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Connecting...
              </>
            ) : (
              <>
                Continue <ChevronRight className="ml-1 h-4 w-4" />
              </>
            )}
          </Button>
        </div>

        <p className="text-center">
          <button
            onClick={onStaffLogin}
            className="text-[10px] text-muted-foreground hover:text-foreground transition-colors underline-offset-2 hover:underline"
          >
            Staff sign-in
          </button>
        </p>
      </div>
    </div>
  );
}

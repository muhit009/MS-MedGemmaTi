'use client';

import React, { useState, useLayoutEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';

interface TutorialStep {
  dataTutorial?: string;
  title: string;
  description: string;
}

const STEPS: TutorialStep[] = [
  {
    title: 'Welcome to MedGemma Clinical Suite',
    description:
      'This quick tour walks you through the key features of the interface. You can skip at any time.',
  },
  {
    dataTutorial: 'find-patient',
    title: 'Find a Patient',
    description:
      'Search by name or ID to load a patient record. We have pre-loaded demo patients showcasing key clinical scenarios — start with patient 17523 for the "dangerous miss" case.',
  },
  {
    dataTutorial: 'clinical-context',
    title: 'Clinical Context',
    description:
      'View and edit the clinical alert, vitals, and patient notes here. Attach any of these to your AI query for richer, context-aware analysis.',
  },
  {
    dataTutorial: 'imaging-history',
    title: 'Imaging History',
    description:
      'Select one or more studies to include in the analysis. Image order matters — MedGemma-TI tracks interval changes across time.',
  },
  {
    dataTutorial: 'chat-panel',
    title: 'AI Consultation',
    description:
      'Type your clinical query here and send. The AI response streams in real time. Attach images and context before sending for the best results.',
  },
  {
    dataTutorial: 'mode-pill',
    title: 'Analysis vs Discussion',
    description:
      'Auto-switches between structured Analysis mode (PRIOR→CURRENT comparison) and conversational Discussion mode. Click the pill to manually lock the mode.',
  },
  {
    dataTutorial: 'attach-button',
    title: 'Attach Context',
    description:
      'Pin images, notes, or the clinical alert to your query. Everything attached here is sent to the model alongside your prompt.',
  },
];

interface SpotlightRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

interface TutorialOverlayProps {
  onDone: () => void;
}

export default function TutorialOverlay({ onDone }: TutorialOverlayProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [spotlightRect, setSpotlightRect] = useState<SpotlightRect | null>(null);

  const step = STEPS[currentStep];
  const isFirst = currentStep === 0;
  const isLast = currentStep === STEPS.length - 1;

  useLayoutEffect(() => {
    if (!step.dataTutorial) {
      setSpotlightRect(null);
      return;
    }
    const el = document.querySelector(`[data-tutorial="${step.dataTutorial}"]`);
    if (!el) {
      setSpotlightRect(null);
      return;
    }
    const rect = el.getBoundingClientRect();
    const padding = 8;
    setSpotlightRect({
      top: rect.top - padding,
      left: rect.left - padding,
      width: rect.width + padding * 2,
      height: rect.height + padding * 2,
    });
  }, [currentStep, step.dataTutorial]);

  const handleNext = () => {
    if (isLast) {
      onDone();
    } else {
      setCurrentStep((s) => s + 1);
    }
  };

  const handlePrev = () => {
    if (!isFirst) setCurrentStep((s) => s - 1);
  };

  // Tooltip positioning: prefer below the spotlight, flip above if it would overflow bottom
  const viewportHeight = typeof window !== 'undefined' ? window.innerHeight : 800;
  const viewportWidth = typeof window !== 'undefined' ? window.innerWidth : 1280;
  const TOOLTIP_HEIGHT = 170;
  const TOOLTIP_WIDTH = 300;

  const tooltipLeft = spotlightRect
    ? Math.max(12, Math.min(spotlightRect.left, viewportWidth - TOOLTIP_WIDTH - 12))
    : undefined;

  let clampedTop: number | undefined;
  if (spotlightRect) {
    const below = spotlightRect.top + spotlightRect.height + 12;
    const above = spotlightRect.top - TOOLTIP_HEIGHT - 12;
    if (below + TOOLTIP_HEIGHT > viewportHeight - 12) {
      // Flip above — clamp so it never goes off the top either
      clampedTop = Math.max(12, above);
    } else {
      clampedTop = below;
    }
  }

  return (
    <div className="fixed inset-0 z-[100]" style={{ pointerEvents: 'auto' }}>
      {/* Step 0: Welcome — centered dark overlay, no spotlight */}
      {!spotlightRect && (
        <div className="absolute inset-0 bg-black/72 flex items-center justify-center">
          <div className="bg-card border border-border rounded-xl shadow-2xl p-6 max-w-sm w-full mx-4 space-y-4 animate-in zoom-in-95 duration-200">
            <div className="flex items-start justify-between">
              <h2 className="text-base font-semibold text-foreground">{step.title}</h2>
              <button
                onClick={onDone}
                className="text-muted-foreground hover:text-foreground transition-colors ml-2 shrink-0"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-muted-foreground">
                {currentStep + 1} / {STEPS.length}
              </span>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={onDone} className="h-8 text-xs">
                  Skip
                </Button>
                <Button size="sm" onClick={handleNext} className="h-8 text-xs">
                  Next <ChevronRight className="ml-1 h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Spotlight steps */}
      {spotlightRect && (
        <>
          {/* Spotlight hole via box-shadow */}
          <div
            style={{
              position: 'fixed',
              top: spotlightRect.top,
              left: spotlightRect.left,
              width: spotlightRect.width,
              height: spotlightRect.height,
              boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.72)',
              borderRadius: '6px',
              pointerEvents: 'none',
              zIndex: 101,
            }}
          />

          {/* Tooltip card */}
          <div
            className="fixed bg-card border border-border rounded-xl shadow-2xl p-4 space-y-3 animate-in fade-in zoom-in-95 duration-150"
            style={{
              top: clampedTop,
              left: tooltipLeft,
              maxWidth: 300,
              zIndex: 102,
              pointerEvents: 'auto',
            }}
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold text-foreground leading-snug">{step.title}</h3>
              <button
                onClick={onDone}
                className="text-muted-foreground hover:text-foreground transition-colors shrink-0"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">{step.description}</p>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground">
                {currentStep + 1} / {STEPS.length}
              </span>
              <div className="flex gap-1.5">
                {!isFirst && (
                  <Button variant="ghost" size="sm" onClick={handlePrev} className="h-7 text-[11px] px-2">
                    <ChevronLeft className="h-3 w-3 mr-0.5" /> Prev
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onDone}
                  className="h-7 text-[11px] px-2 text-muted-foreground"
                >
                  Skip
                </Button>
                <Button size="sm" onClick={handleNext} className="h-7 text-[11px] px-2">
                  {isLast ? 'Done' : 'Next'}
                  {!isLast && <ChevronRight className="ml-0.5 h-3 w-3" />}
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

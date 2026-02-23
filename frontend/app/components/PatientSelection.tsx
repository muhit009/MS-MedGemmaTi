'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { FileText, Search, Loader2 } from 'lucide-react';
import { searchPatients, getPatient } from '@/lib/api';
import type { PatientSearchResponse, PatientResponse } from '@/types/api';

interface PatientSelectionProps {
  onPatientSelect: (patient: PatientResponse) => void;
}

const PatientSelection: React.FC<PatientSelectionProps> = ({ onPatientSelect }) => {
  const [patientId, setPatientId] = useState('');
  const [patientName, setPatientName] = useState('');
  const [results, setResults] = useState<PatientSearchResponse[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!patientId.trim() && !patientName.trim()) return;
    setError('');
    setSearching(true);
    setResults([]);
    try {
      const data = await searchPatients({
        patientId: patientId.trim() || undefined,
        name: patientName.trim() || undefined,
      });
      setResults(data);
      if (data.length === 0) setError('No patients found.');
    } catch {
      setError('Search failed. Check your connection.');
    } finally {
      setSearching(false);
    }
  };

  const handleSelect = async (result: PatientSearchResponse) => {
    setLoading(true);
    setError('');
    try {
      const full = await getPatient(result.id);
      onPatientSelect(full);
    } catch {
      setError('Failed to load patient details.');
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-4 py-4 font-sans">
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground bg-secondary/30 p-2 rounded">
          <FileText className="h-4 w-4" />
          <span>Enter patient details to access secure records.</span>
        </div>

        <div className="space-y-2">
          <label htmlFor="patient-id" className="text-xs font-medium text-foreground">Patient ID</label>
          <Input
            id="patient-id"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="e.g. 8492-A"
            className="font-mono h-10"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="patient-name" className="text-xs font-medium text-foreground">Legal Name</label>
          <Input
            id="patient-name"
            value={patientName}
            onChange={(e) => setPatientName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Last, First"
            className="h-10"
          />
        </div>
      </div>

      <Button onClick={handleSearch} className="w-full h-11" disabled={searching || loading}>
        {searching ? (
          <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Searching...</>
        ) : (
          <><Search className="mr-2 h-4 w-4" /> Search</>
        )}
      </Button>

      {error && <p className="text-xs text-destructive text-center">{error}</p>}

      {/* Results list */}
      {results.length > 0 && (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => handleSelect(r)}
              disabled={loading}
              className="w-full text-left med-panel p-3 cursor-pointer hover:border-primary/40 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-full bg-gradient-to-br from-primary/20 to-secondary flex items-center justify-center text-primary font-bold text-sm border border-white/10">
                  {r.name.charAt(0)}
                </div>
                <div className="flex-grow min-w-0">
                  <div className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors truncate">
                    {r.name}
                  </div>
                  <div className="text-[10px] text-muted-foreground font-mono">
                    ID: {r.id} &middot; DOB: {r.dob} &middot; {r.sex}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      <p className="text-[10px] text-center text-muted-foreground leading-tight">
        Access logged for auditing purposes.<br />
        Ensure HIPAA compliance protocols are followed.
      </p>
    </div>
  );
};

export default PatientSelection;

'use client';
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Search, Paperclip, Send, Activity, ShieldAlert, ChevronLeft, ChevronRight, FileText, Calendar, CheckCircle2, X, MessageSquare, ChevronDown, StickyNote, Plus, Trash2, Save, Pencil, PlusCircle, Loader2, LogOut, UserPlus, ImageIcon, ScanLine, MessageCircle, Lock, Upload } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import PatientSelection from './PatientSelection';
import TutorialOverlay from './TutorialOverlay';

import { useAuth } from '@/app/context/AuthContext';
import {
  getLatestVitals,
  getActiveAlert,
  updateAlert as apiUpdateAlert,
  getNotes,
  createNote as apiCreateNote,
  updateNote as apiUpdateNote,
  deleteNote as apiDeleteNote,
  getImaging,
  uploadImage as apiUploadImage,
  deleteImage as apiDeleteImage,
  getConsultations,
  streamAnalysis,
  createPatient as apiCreatePatient,
  getPatient,
} from '@/lib/api';
import type {
  PatientResponse,
  AlertResponse,
  NoteResponse,
  ImageResponse,
  ConsultationListResponse,
  PatientCreateRequest,
  InlineImage,
} from '@/types/api';

// ─── Local types for chat messages ──────────────────────────────
interface Message {
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  imageCount?: number;
  noteCount?: number;
}

// Demo patients — interactions work locally but never persist to DB.
// On reload, loadPatientData() fetches fresh seed data from Supabase.
const DEMO_PATIENT_IDS = new Set(['13011', '16997', '17523', '24163', '40207', '44669']);

const Dashboard = () => {
  const { user, logout } = useAuth();

  // Patient
  const [patient, setPatient] = useState<PatientResponse | null>(null);
  const [isPatientSelectionOpen, setIsPatientSelectionOpen] = useState(false);
  const isDemoPatient = patient ? DEMO_PATIENT_IDS.has(patient.id) : false;

  // Pane State
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);

  // Collapsible Sections State
  const [isChatHistoryOpen, setIsChatHistoryOpen] = useState(false);
  const [isNotesOpen, setIsNotesOpen] = useState(true);
  const [isImagingHistoryOpen, setIsImagingHistoryOpen] = useState(true);

  // API-backed state
  const [vitals, setVitals] = useState({ hr: '', spo2: '', bp: '' });
  const [editingVital, setEditingVital] = useState<string | null>(null);
  const [tempVital, setTempVital] = useState('');
  const [alert, setAlert] = useState<AlertResponse | null>(null);
  const [notes, setNotes] = useState<NoteResponse[]>([]);
  const [images, setImages] = useState<ImageResponse[]>([]);
  const [consultations, setConsultations] = useState<ConsultationListResponse[]>([]);
  const [dataLoading, setDataLoading] = useState(false);

  // Selections for AI context
  const [selectedImages, setSelectedImages] = useState<ImageResponse[]>([]);
  const [selectedNotes, setSelectedNotes] = useState<NoteResponse[]>([]);

  // Notes editing
  const [editingNote, setEditingNote] = useState<NoteResponse | 'new' | null>(null);
  const [noteEditorContent, setNoteEditorContent] = useState('');

  // Alert editing
  const [isEditingAlert, setIsEditingAlert] = useState(false);
  const [tempAlertContent, setTempAlertContent] = useState('');
  const [isAlertAttached, setIsAlertAttached] = useState(false);

  // Add Patient Dialog
  const [isAddPatientOpen, setIsAddPatientOpen] = useState(false);
  const [newPatientForm, setNewPatientForm] = useState<PatientCreateRequest>({
    businessId: '',
    fullName: '',
    dob: '',
    sex: undefined,
    weightKg: undefined,
    heightCm: undefined,
  });
  const [addPatientLoading, setAddPatientLoading] = useState(false);
  const [addPatientError, setAddPatientError] = useState('');

  // Chat
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [lockedMode, setLockedMode] = useState<'analysis' | 'discussion' | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // Stores base64 payload for ephemeral demo images so they can be sent inline to the backend
  const demoImageDataRef = useRef<Map<string, { base64: string; mimeType: string; visitDate: string }>>(new Map());

  // Tutorial overlay
  const [showTutorial, setShowTutorial] = useState(true);

  // Derived effective mode (not state — recalculated on render)
  const effectiveMode: 'analysis' | 'discussion' =
    lockedMode ?? (messages.length === 0 ? 'analysis' : 'discussion');

  // ─── Fetch all patient data ───────────────────────────────────
  const loadPatientData = useCallback(async (pid: string) => {
    setDataLoading(true);
    try {
      const [v, a, n, img, cons] = await Promise.allSettled([
        getLatestVitals(pid),
        getActiveAlert(pid),
        getNotes(pid),
        getImaging(pid),
        getConsultations(pid),
      ]);
      if (v.status === 'fulfilled') {
        const vr = v.value;
        setVitals({
          hr: vr.heartRate.status !== 'unknown' ? String(vr.heartRate.value) : '',
          spo2: vr.spO2.status !== 'unknown' ? String(vr.spO2.value) : '',
          bp: vr.bloodPressure.status !== 'unknown' ? String(vr.bloodPressure.value) : '',
        });
      }
      if (a.status === 'fulfilled') setAlert(a.value);
      if (n.status === 'fulfilled') setNotes(n.value);
      if (img.status === 'fulfilled') setImages(img.value);
      if (cons.status === 'fulfilled') setConsultations(cons.value);
    } finally {
      setDataLoading(false);
    }
  }, []);

  useEffect(() => {
    if (patient) {
      // Reset state on patient change
      setVitals({ hr: '', spo2: '', bp: '' });
      setSelectedImages([]);
      setSelectedNotes([]);
      setMessages([]);
      setLockedMode(null);
      setIsAlertAttached(false);
      demoImageDataRef.current.clear();
      loadPatientData(patient.id);
    }
  }, [patient, loadPatientData]);

  // Restore last selected patient on mount
  useEffect(() => {
    const savedId = localStorage.getItem('selectedPatientId');
    if (savedId && !patient) {
      getPatient(savedId).then(p => setPatient(p)).catch(() => localStorage.removeItem('selectedPatientId'));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Patient selection ────────────────────────────────────────
  const handlePatientSelect = (selectedPatient: PatientResponse) => {
    setPatient(selectedPatient);
    localStorage.setItem('selectedPatientId', selectedPatient.id);
    setIsPatientSelectionOpen(false);
  };

  // ─── Add patient ─────────────────────────────────────────────
  const handleAddPatient = async () => {
    if (!newPatientForm.businessId.trim() || !newPatientForm.fullName.trim() || !newPatientForm.dob.trim()) return;
    setAddPatientLoading(true);
    setAddPatientError('');
    try {
      const created = await apiCreatePatient({
        businessId: newPatientForm.businessId.trim(),
        fullName: newPatientForm.fullName.trim(),
        dob: newPatientForm.dob,
        sex: newPatientForm.sex || undefined,
        weightKg: newPatientForm.weightKg || undefined,
        heightCm: newPatientForm.heightCm || undefined,
      });
      setPatient(created);
      localStorage.setItem('selectedPatientId', created.id);
      setIsAddPatientOpen(false);
      setNewPatientForm({ businessId: '', fullName: '', dob: '', sex: undefined, weightKg: undefined, heightCm: undefined });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create patient.';
      setAddPatientError(message);
    } finally {
      setAddPatientLoading(false);
    }
  };

  // ─── Vitals editing ────────────────────────────────────────────
  const handleSaveVital = () => {
    if (!editingVital) return;
    let val = tempVital.trim();
    if (editingVital === 'hr' || editingVital === 'spo2') {
      const num = parseInt(val);
      if (isNaN(num)) val = '';
      else if (editingVital === 'spo2' && num > 100) val = '100';
    }
    setVitals(prev => ({ ...prev, [editingVital]: val }));
    setEditingVital(null);
    setTempVital('');
  };

  // ─── Notes CRUD ───────────────────────────────────────────────
  const handleAddNote = () => {
    setEditingNote('new');
    setNoteEditorContent('');
  };

  const handleSaveNote = async () => {
    if (!noteEditorContent.trim() || !patient) return;
    if (isDemoPatient) {
      // Demo patient: update local state only, skip API
      if (editingNote === 'new') {
        const fakeNote: NoteResponse = {
          id: `demo-${Date.now()}`,
          date: new Date().toISOString().slice(0, 10),
          content: noteEditorContent,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        setNotes((prev) => [fakeNote, ...prev]);
      } else if (editingNote && editingNote !== 'new') {
        setNotes((prev) => prev.map((n) => n.id === editingNote.id ? { ...n, content: noteEditorContent, updatedAt: new Date().toISOString() } : n));
      }
    } else {
      try {
        if (editingNote === 'new') {
          const created = await apiCreateNote(patient.id, { content: noteEditorContent });
          setNotes((prev) => [created, ...prev]);
        } else if (editingNote) {
          const updated = await apiUpdateNote(editingNote.id, { content: noteEditorContent });
          setNotes((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
        }
      } catch {
        // silently fail for now
      }
    }
    setEditingNote(null);
    setNoteEditorContent('');
  };

  const handleDeleteNote = async (id: string) => {
    if (!isDemoPatient) {
      try {
        await apiDeleteNote(id);
      } catch {
        // silently fail
      }
    }
    setNotes((prev) => prev.filter((n) => n.id !== id));
    setSelectedNotes((prev) => prev.filter((n) => n.id !== id));
    setEditingNote(null);
  };

  const toggleNoteSelection = (note: NoteResponse) => {
    setSelectedNotes(prev =>
      prev.find(n => n.id === note.id)
        ? prev.filter(n => n.id !== note.id)
        : [...prev, note]
    );
  };

  // ─── Alert save ───────────────────────────────────────────────
  const handleSaveAlert = async () => {
    if (!patient) return;
    if (isDemoPatient) {
      // Demo patient: update local state only
      setAlert({
        id: alert?.id ?? `demo-alert-${Date.now()}`,
        content: tempAlertContent,
        severity: tempAlertContent.trim() ? 'warning' : 'nominal',
        updatedAt: new Date().toISOString(),
      });
    } else {
      try {
        const updated = await apiUpdateAlert(patient.id, { content: tempAlertContent });
        setAlert(updated);
      } catch {
        // silently fail
      }
    }
    setIsEditingAlert(false);
  };

  // ─── Image selection ──────────────────────────────────────────
  const toggleImageSelection = (image: ImageResponse) => {
    setSelectedImages((prev) =>
      prev.find((img) => img.id === image.id)
        ? prev.filter((img) => img.id !== image.id)
        : [...prev, image]
    );
  };

  // ─── Attach menu ───────────────────────────────────────────────
  const [isAttachMenuOpen, setIsAttachMenuOpen] = useState(false);
  const attachMenuRef = useRef<HTMLDivElement>(null);

  // Close attach menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (attachMenuRef.current && !attachMenuRef.current.contains(e.target as Node)) {
        setIsAttachMenuOpen(false);
      }
    };
    if (isAttachMenuOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isAttachMenuOpen]);

  // ─── Image upload / delete ─────────────────────────────────────
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatFileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  // Universal upload modal state
  const [pendingUpload, setPendingUpload] = useState<{ file: File; autoSelect: boolean } | null>(null);
  const [uploadDateTime, setUploadDateTime] = useState('');
  const [uploadPreviewUrl, setUploadPreviewUrl] = useState<string | null>(null);

  // Create / revoke preview URL whenever a file is staged
  useEffect(() => {
    if (pendingUpload) {
      const url = URL.createObjectURL(pendingUpload.file);
      setUploadPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setUploadPreviewUrl(null);
    }
  }, [pendingUpload]);

  const nowDateTimeLocal = () => {
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
  };

  // Step 1: file picker onChange — just stage the file and open modal
  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>, autoSelect = false) => {
    const file = e.target.files?.[0];
    // Reset inputs immediately so re-selecting the same file works next time
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (chatFileInputRef.current) chatFileInputRef.current.value = '';
    if (!file || !patient) return;
    setUploadError('');
    if (images.length >= 5) {
      setUploadError('Maximum 5 images per patient. Delete an existing image first.');
      return;
    }
    setUploadDateTime(nowDateTimeLocal());
    setPendingUpload({ file, autoSelect });
  };

  // Step 2: user confirms date in modal — do the actual upload
  const handleConfirmUpload = async () => {
    if (!pendingUpload || !patient) return;
    const { file, autoSelect } = pendingUpload;

    // Convert datetime-local "YYYY-MM-DDTHH:mm" → "MM/DD/YYYY" for the API
    const [datePart, timePart = '00:00'] = uploadDateTime.split('T');
    const [year, month, day] = datePart.split('-');
    const uploadDateForApi = `${month}/${day}/${year}`;
    const dateDisplay = `${datePart} ${timePart}`;

    setPendingUpload(null);
    setIsUploading(true);
    try {
      if (isDemoPatient) {
        const localUrl = URL.createObjectURL(file);
        const fakeImage: ImageResponse = {
          id: `demo-img-${Date.now()}`,
          src: localUrl,
          modality: 'X-Ray',
          date: dateDisplay,
          reading: null,
          confidence: 'Low',
        };
        try {
          const base64 = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve((reader.result as string).split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
          });
          demoImageDataRef.current.set(fakeImage.id, {
            base64,
            mimeType: file.type || 'image/jpeg',
            visitDate: dateDisplay,
          });
        } catch { /* image shows but won't be sent inline */ }
        setImages((prev) => [fakeImage, ...prev]);
        if (autoSelect) setSelectedImages((prev) => [...prev, fakeImage]);
      } else {
        const uploaded = await apiUploadImage(patient.id, file, uploadDateForApi);
        setImages((prev) => [uploaded, ...prev]);
        if (autoSelect) setSelectedImages((prev) => [...prev, uploaded]);
      }
    } catch {
      setUploadError('Failed to upload image. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    if (!patient) return;
    if (!isDemoPatient) {
      try {
        await apiDeleteImage(patient.id, imageId);
      } catch (err) {
        console.error('Failed to delete image:', err);
        setUploadError('Failed to delete image. Please try again.');
        return; // Don't remove from UI if backend delete failed
      }
    }
    demoImageDataRef.current.delete(imageId);
    setImages((prev) => prev.filter((img) => img.id !== imageId));
    setSelectedImages((prev) => prev.filter((img) => img.id !== imageId));
    setUploadError('');
  };

  // ─── Chat / AI analysis ───────────────────────────────────────
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, rightOpen]);

  const handleSubmit = async () => {
    if (!patient) return;
    if (!prompt.trim() && selectedImages.length === 0 && selectedNotes.length === 0 && !isAlertAttached) return;

    if (!rightOpen) setRightOpen(true);

    const userMsg: Message = {
      text: prompt,
      sender: 'user',
      timestamp: new Date(),
      imageCount: selectedImages.length,
      noteCount: selectedNotes.length + (isAlertAttached ? 1 : 0)
    };
    setMessages((prev) => [...prev, userMsg]);

    const currentPrompt = prompt;
    // Separate real Supabase images from ephemeral demo images.
    // Non-UUID "demo-img-*" IDs cannot be queried from the DB; send them inline as base64.
    const currentImageIds = selectedImages
      .map((i) => i.id)
      .filter((id) => !String(id).startsWith('demo-'));
    const inlineImages: InlineImage[] = selectedImages
      .filter((img) => String(img.id).startsWith('demo-'))
      .map((img) => demoImageDataRef.current.get(img.id))
      .filter((d): d is { base64: string; mimeType: string; visitDate: string } => Boolean(d))
      .map((d) => ({ base64: d.base64, mimeType: d.mimeType, visitDate: d.visitDate }));
    const currentNoteIds = selectedNotes.map((n) => n.id);
    const currentAlertContent = isAlertAttached && alertContent ? alertContent : undefined;

    setPrompt('');
    setSelectedNotes([]);
    setIsAlertAttached(false);

    // Add blank AI message for streaming
    const aiMsg: Message = { text: '', sender: 'ai', timestamp: new Date() };
    setMessages((prev) => [...prev, aiMsg]);
    setIsStreaming(true);

    try {
      const stream = streamAnalysis({
        patientId: patient.id,
        prompt: currentPrompt,
        mode: effectiveMode,
        inlineImages: inlineImages.length > 0 ? inlineImages : undefined,
        context: {
          imageIds: currentImageIds.length > 0 ? currentImageIds : undefined,
          noteIds: currentNoteIds.length > 0 ? currentNoteIds : undefined,
          alertContent: currentAlertContent,
        },
        modelConfig: { stream: true },
      });

      for await (const chunk of stream) {
        if (chunk.text) {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.sender === 'ai') {
              updated[updated.length - 1] = { ...last, text: last.text + chunk.text };
            }
            return updated;
          });
        }
        if (chunk.done) break;
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last.sender === 'ai' && !last.text) {
          updated[updated.length - 1] = { ...last, text: 'Failed to generate analysis. Please try again.' };
        }
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  // ─── Pane toggles ─────────────────────────────────────────────
  const toggleLeftPane = () => {
    if (leftOpen && !rightOpen) return;
    setLeftOpen(!leftOpen);
  };

  const toggleRightPane = () => {
    if (rightOpen && !leftOpen) return;
    setRightOpen(!rightOpen);
  };

  // ─── Time-ago helper ──────────────────────────────────────────
  const getTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffTime = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays < 0) return 'Future';
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 30) return `${diffDays}d ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
    return `${Math.floor(diffDays / 365)}y ago`;
  };

  // ─── Attachment tray ──────────────────────────────────────────
  const alertContent = alert?.severity !== 'nominal' ? alert?.content ?? '' : '';

  const allAttachments = [
    ...(isAlertAttached && alertContent ? [{ id: 'alert-attachment', date: '0000-00-00', type: 'alert' as const, modality: 'Clinical Alert', content: alertContent }] : []),
    ...selectedImages.map(img => ({ ...img, type: 'image' as const })),
    ...selectedNotes.map(note => ({ ...note, type: 'note' as const, modality: 'Note' }))
  ].sort((a: any, b: any) => {
    if (a.type === 'alert') return -1;
    if (b.type === 'alert') return 1;
    return new Date(a.date).getTime() - new Date(b.date).getTime();
  });

  // (vitals are edited locally via inline inputs)

  return (
    <div className="h-screen w-full bg-background text-foreground overflow-hidden font-sans flex flex-col">

      {/* Global Header */}
      <header className="h-14 shrink-0 px-4 flex justify-between items-center border-b border-border bg-background/50 backdrop-blur-sm z-20">
        <div className="flex items-center gap-4">
          <div className="text-lg font-semibold tracking-tight text-primary flex items-center gap-2">
            MedGemma <span className="text-[10px] uppercase font-medium text-muted-foreground px-1.5 py-0.5 border border-border rounded-md">Clinical Suite</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
           <div className="flex items-center gap-2 text-[10px] font-medium text-muted-foreground bg-secondary/30 px-2 py-1 rounded border border-border">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {user?.full_name ?? user?.username ?? 'ONLINE'}
           </div>
          <Dialog
            open={isPatientSelectionOpen}
            onOpenChange={setIsPatientSelectionOpen}
          >
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 text-xs border-primary/20 hover:bg-primary/5" data-tutorial="find-patient">
                <Search className="mr-2 h-3 w-3" />
                Find Patient
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Select Patient</DialogTitle>
              </DialogHeader>
              <PatientSelection onPatientSelect={handlePatientSelect} />
            </DialogContent>
          </Dialog>

          <Dialog open={isAddPatientOpen} onOpenChange={(open) => { setIsAddPatientOpen(open); if (!open) setAddPatientError(''); }}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 text-xs border-primary/20 hover:bg-primary/5">
                <UserPlus className="mr-2 h-3 w-3" />
                Add Patient
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[450px]">
              <DialogHeader>
                <DialogTitle>Add New Patient</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4 font-sans">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label htmlFor="new-patient-id" className="text-xs font-medium text-foreground">Patient ID *</label>
                    <Input
                      id="new-patient-id"
                      value={newPatientForm.businessId}
                      onChange={(e) => setNewPatientForm(prev => ({ ...prev, businessId: e.target.value }))}
                      placeholder="e.g. 8492-A"
                      className="font-mono h-10"
                    />
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="new-patient-dob" className="text-xs font-medium text-foreground">Date of Birth *</label>
                    <Input
                      id="new-patient-dob"
                      type="date"
                      value={newPatientForm.dob}
                      onChange={(e) => setNewPatientForm(prev => ({ ...prev, dob: e.target.value }))}
                      className="h-10"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label htmlFor="new-patient-name" className="text-xs font-medium text-foreground">Full Name *</label>
                  <Input
                    id="new-patient-name"
                    value={newPatientForm.fullName}
                    onChange={(e) => setNewPatientForm(prev => ({ ...prev, fullName: e.target.value }))}
                    placeholder="Last, First"
                    className="h-10"
                  />
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <label htmlFor="new-patient-sex" className="text-xs font-medium text-foreground">Sex</label>
                    <select
                      id="new-patient-sex"
                      value={newPatientForm.sex ?? ''}
                      onChange={(e) => setNewPatientForm(prev => ({ ...prev, sex: e.target.value || undefined }))}
                      className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    >
                      <option value="">--</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="new-patient-weight" className="text-xs font-medium text-foreground">Weight (kg)</label>
                    <Input
                      id="new-patient-weight"
                      type="number"
                      value={newPatientForm.weightKg ?? ''}
                      onChange={(e) => setNewPatientForm(prev => ({ ...prev, weightKg: e.target.value ? parseFloat(e.target.value) : undefined }))}
                      placeholder="kg"
                      className="h-10"
                    />
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="new-patient-height" className="text-xs font-medium text-foreground">Height (cm)</label>
                    <Input
                      id="new-patient-height"
                      type="number"
                      value={newPatientForm.heightCm ?? ''}
                      onChange={(e) => setNewPatientForm(prev => ({ ...prev, heightCm: e.target.value ? parseFloat(e.target.value) : undefined }))}
                      placeholder="cm"
                      className="h-10"
                    />
                  </div>
                </div>
                {addPatientError && <p className="text-xs text-destructive text-center">{addPatientError}</p>}
                <Button onClick={handleAddPatient} className="w-full h-11" disabled={addPatientLoading || !newPatientForm.businessId.trim() || !newPatientForm.fullName.trim() || !newPatientForm.dob.trim()}>
                  {addPatientLoading ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating...</>
                  ) : (
                    <><UserPlus className="mr-2 h-4 w-4" /> Create Patient</>
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          <Button variant="ghost" size="sm" className="h-8 text-xs text-muted-foreground hover:text-destructive" onClick={logout}>
            <LogOut className="h-3 w-3" />
          </Button>
        </div>
      </header>

      {/* No patient selected state */}
      {!patient && (
        <div className="flex-grow flex flex-col items-center justify-center opacity-40 select-none">
          <FileText className="h-16 w-16 text-muted-foreground mb-4" />
          <p className="text-sm text-muted-foreground">Select a patient to begin</p>
        </div>
      )}

      {/* Main Dual-Pane Layout */}
      {patient && (
      <div className="flex-grow flex overflow-hidden">

        {/* LEFT PANE: Information */}
        <div
          className={`flex flex-col border-r border-border bg-card/30 backdrop-blur-sm transition-all duration-500 ease-[cubic-bezier(0.25,1,0.5,1)] overflow-hidden relative ${
            !leftOpen ? 'w-12 cursor-pointer hover:bg-secondary/10' : (!rightOpen ? 'flex-1' : 'w-[40%]')
          }`}
          onClick={() => !leftOpen && toggleLeftPane()}
        >
          {/* Collapsed Header (Vertical) */}
          <div className={`absolute inset-0 flex items-center justify-center transition-opacity duration-300 ${!leftOpen ? 'opacity-100 delay-200' : 'opacity-0 pointer-events-none'}`}>
             <div className="rotate-180 [writing-mode:vertical-rl] text-xs font-bold text-muted-foreground tracking-widest whitespace-nowrap flex items-center gap-3">
                <FileText className="h-4 w-4 rotate-90" /> PATIENT RECORD
             </div>
          </div>

          <div className={`h-full flex flex-col min-w-[350px] min-h-0 transition-opacity duration-300 ${!leftOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>

             {/* Pane Header */}
             <div
               className="h-12 px-4 flex items-center justify-between border-b border-border/50 bg-secondary/5 shrink-0 cursor-pointer group select-none"
               onClick={(e) => { e.stopPropagation(); toggleLeftPane(); }}
             >
                <h3 className="font-medium text-sm flex items-center gap-2 text-foreground/80 group-hover:text-primary transition-colors">
                   <FileText className="h-4 w-4 text-primary" /> Patient Record
                   <ChevronLeft className={`h-4 w-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300 text-muted-foreground ${!rightOpen ? 'hidden' : ''}`} />
                </h3>
             </div>

             <ScrollArea className="flex-grow min-h-0">
                 <div className="p-4 space-y-6">

                   {/* Loading overlay */}
                   {dataLoading && (
                     <div className="flex items-center justify-center py-8">
                       <Loader2 className="h-6 w-6 text-primary animate-spin" />
                     </div>
                   )}

                   {!dataLoading && (
                   <>
                   {/* 1. Personal Details */}
                 <div className="med-panel p-4 space-y-4">
                    <div className="flex items-center gap-4">
                       <div className="h-14 w-14 rounded-full bg-gradient-to-br from-primary/20 to-secondary flex items-center justify-center text-primary font-bold text-xl shadow-inner border border-white/10">
                         {patient.name.charAt(0)}
                       </div>
                       <div>
                         <div className="font-bold text-xl leading-tight text-foreground">{patient.name}</div>
                         <div className="text-xs font-mono text-muted-foreground mt-0.5">ID: {patient.id} &middot; DOB: {patient.dob}</div>
                       </div>
                    </div>
                    <div className="grid grid-cols-4 gap-2 pt-2 border-t border-border/40">
                       <div className="text-center p-2 bg-background/50 rounded border border-border/50">
                          <div className="text-[10px] uppercase text-muted-foreground font-semibold">Age</div>
                          <div className="text-sm font-medium">{patient.age}</div>
                       </div>
                       <div className="text-center p-2 bg-background/50 rounded border border-border/50">
                          <div className="text-[10px] uppercase text-muted-foreground font-semibold">Sex</div>
                          <div className="text-sm font-medium">{patient.sex?.charAt(0) ?? '—'}</div>
                       </div>
                       <div className="text-center p-2 bg-background/50 rounded border border-border/50">
                          <div className="text-[10px] uppercase text-muted-foreground font-semibold">Wgt</div>
                          <div className="text-sm font-medium">{patient.weight ?? '—'}</div>
                       </div>
                       <div className="text-center p-2 bg-background/50 rounded border border-border/50">
                          <div className="text-[10px] uppercase text-muted-foreground font-semibold">Hgt</div>
                          <div className="text-sm font-medium">{patient.height ?? '—'}</div>
                       </div>
                    </div>
                 </div>

                 {/* 2. Alerts (Editable) */}
                 <div data-tutorial="clinical-context" className={`med-panel transition-colors group relative overflow-hidden ${
                    isEditingAlert ? 'border-primary ring-1 ring-primary bg-background' :
                    alertContent ? 'bg-amber-950/10 border-amber-900/20' :
                    'bg-emerald-950/10 border-emerald-900/20'
                 }`}>
                    {isEditingAlert ? (
                       <div className="space-y-2 p-3">
                          <div className="flex items-center justify-between">
                             <div className="text-xs font-bold text-primary uppercase tracking-wide flex items-center gap-2">
                                <ShieldAlert className="h-3.5 w-3.5" /> Edit Alert
                             </div>
                             <span className={`text-[9px] ${tempAlertContent.length > 200 ? 'text-destructive' : 'text-muted-foreground'}`}>
                                {tempAlertContent.length}/200
                             </span>
                          </div>
                          <textarea
                             value={tempAlertContent}
                             onChange={(e) => setTempAlertContent(e.target.value)}
                             onKeyDown={(e) => {
                                if (e.key === 'Escape') {
                                   setIsEditingAlert(false);
                                }
                             }}
                             className="w-full bg-secondary/20 rounded p-2 text-xs focus:outline-none resize-none min-h-[60px]"
                             maxLength={200}
                             autoFocus
                          />
                          <div className="flex justify-end gap-2">
                             <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={(e) => { e.stopPropagation(); setIsEditingAlert(false); }}>Cancel</Button>
                             <Button size="sm" className="h-6 text-[10px]" onClick={(e) => { e.stopPropagation(); handleSaveAlert(); }}>Save</Button>
                          </div>
                       </div>
                    ) : (
                       <div className="flex items-stretch min-h-[60px]">
                          {alertContent.trim() ? (
                             <>
                                <div className="flex gap-3 p-3 flex-grow">
                                   <ShieldAlert className="h-5 w-5 text-amber-500 shrink-0 mt-0.5 animate-pulse" />
                                   <div className="flex-grow">
                                      <div className="text-xs font-bold text-amber-500 uppercase tracking-wide mb-1">Clinical Alert</div>
                                      <p className="text-xs text-amber-200/80 leading-relaxed">{alertContent}</p>
                                   </div>
                                </div>
                                <div className="flex items-center border-l border-border/30 bg-secondary/5">
                                   <button
                                      onClick={() => { setTempAlertContent(alertContent); setIsEditingAlert(true); }}
                                      className="h-full w-8 flex items-center justify-center text-muted-foreground hover:text-amber-500 hover:bg-amber-500/10 transition-colors"
                                      title="Edit Alert"
                                   >
                                      <Pencil className="h-4 w-4" />
                                   </button>
                                   <button
                                      onClick={() => setIsAlertAttached(!isAlertAttached)}
                                      className={`h-full w-8 flex items-center justify-center transition-colors ${
                                         isAlertAttached ? 'bg-amber-500/20 text-amber-500' : 'text-muted-foreground hover:text-amber-500 hover:bg-amber-500/10'
                                      }`}
                                      title={isAlertAttached ? "Detach from prompt" : "Attach to prompt"}
                                   >
                                      <PlusCircle className={`h-4 w-4 ${isAlertAttached ? 'rotate-45' : ''} transition-transform`} />
                                   </button>
                                </div>
                             </>
                          ) : (
                             <>
                                <div className="flex gap-3 p-3 flex-grow">
                                   <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                                   <div className="flex-grow">
                                      <div className="text-xs font-bold text-emerald-500 uppercase tracking-wide mb-1">Status Nominal</div>
                                      <p className="text-xs text-emerald-200/80 leading-relaxed">No active warnings. Patient condition stable.</p>
                                   </div>
                                </div>
                                <div className="flex items-center border-l border-border/30 bg-secondary/5">
                                   <button
                                      onClick={() => { setTempAlertContent(''); setIsEditingAlert(true); }}
                                      className="h-full w-8 flex items-center justify-center text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                                      title="Add Alert"
                                   >
                                      <Pencil className="h-4 w-4" />
                                   </button>
                                </div>
                             </>
                          )}
                       </div>
                    )}
                 </div>

                 {/* 3. Vitals (Editable) */}
                 <div className="med-panel p-4 space-y-4">
                    <div className="text-xs font-bold text-muted-foreground uppercase tracking-wide flex items-center gap-2">
                       <Activity className="h-3.5 w-3.5" /> Recorded Vitals
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                       {[
                         { key: 'hr', label: 'HR', unit: 'bpm', color: 'text-emerald-500', placeholder: '72' },
                         { key: 'spo2', label: 'SpO2', unit: '%', color: 'text-blue-500', placeholder: '98' },
                         { key: 'bp', label: 'BP', unit: '', color: 'text-rose-500', placeholder: '120/80' },
                       ].map((v) => (
                         <div
                           key={v.key}
                           className="group cursor-pointer p-1 -m-1 rounded hover:bg-secondary/10 transition-colors"
                           onClick={() => {
                              if (editingVital !== v.key) {
                                 setEditingVital(v.key);
                                 setTempVital(vitals[v.key as keyof typeof vitals]);
                              }
                           }}
                         >
                            <div className="flex justify-between items-baseline mb-1 h-7">
                               {editingVital === v.key ? (
                                  <Input
                                     value={tempVital}
                                     onChange={(e) => setTempVital(e.target.value)}
                                     onKeyDown={(e) => {
                                        if (e.key === 'Enter') handleSaveVital();
                                        if (e.key === 'Escape') setEditingVital(null);
                                     }}
                                     onBlur={handleSaveVital}
                                     onClick={(e) => e.stopPropagation()}
                                     className="h-7 text-lg font-mono font-bold px-1 py-0 border-primary/30 bg-background"
                                     autoFocus
                                     placeholder={v.placeholder}
                                  />
                               ) : (
                                  <div className={`text-xl font-mono font-bold ${vitals[v.key as keyof typeof vitals] ? v.color : 'text-muted-foreground/30'}`}>
                                     {vitals[v.key as keyof typeof vitals] || '--'}
                                     <span className="text-[10px] text-muted-foreground ml-0.5">{v.unit}</span>
                                  </div>
                               )}
                            </div>
                            <div className="text-[10px] text-muted-foreground font-medium flex items-center justify-between">
                               {v.label}
                               {editingVital !== v.key && (
                                  <Pencil className="h-2.5 w-2.5 opacity-0 group-hover:opacity-50 transition-opacity" />
                               )}
                            </div>
                         </div>
                       ))}
                    </div>
                 </div>

                 {/* 4. Chat History (Collapsible) */}
                 {consultations.length > 0 && (
                 <Collapsible open={isChatHistoryOpen} onOpenChange={setIsChatHistoryOpen} className="space-y-2">
                    <div className="flex items-center justify-between">
                       <CollapsibleTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-6 p-0 hover:bg-transparent text-xs font-bold text-muted-foreground uppercase tracking-wide flex items-center gap-2 w-full justify-start">
                             <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-200 ${isChatHistoryOpen ? '' : '-rotate-90'}`} />
                             <MessageSquare className="h-3.5 w-3.5" /> Past Consultations
                          </Button>
                       </CollapsibleTrigger>
                    </div>

                    <CollapsibleContent className="collapsible-content space-y-2">
                       {consultations.map((chat) => (
                          <div key={chat.id} className="med-panel p-3 cursor-pointer hover:border-primary/40 transition-colors group">
                             <div className="flex justify-between items-start mb-1">
                                <span className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors">{chat.title}</span>
                                <span className="text-[9px] text-muted-foreground">{chat.date}</span>
                             </div>
                             <p className="text-[10px] text-muted-foreground line-clamp-1">{chat.snippet}</p>
                          </div>
                       ))}
                    </CollapsibleContent>
                 </Collapsible>
                 )}

                 {/* 5. Patient Notes (Collapsible) */}
                 <Collapsible open={isNotesOpen} onOpenChange={setIsNotesOpen} className="space-y-2">
                    <div className="flex items-center justify-between gap-2 pr-1">
                       <CollapsibleTrigger asChild>
                          <Button variant="ghost" size="sm" className="flex-grow h-8 p-0 hover:bg-transparent text-xs font-bold text-muted-foreground uppercase tracking-wide flex items-center gap-2 justify-start">
                             <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-200 ${isNotesOpen ? '' : '-rotate-90'}`} />
                             <StickyNote className="h-3.5 w-3.5" /> Patient Notes
                          </Button>
                       </CollapsibleTrigger>
                       <Button
                         variant="ghost"
                         size="sm"
                         className="h-8 w-8 p-0 hover:bg-secondary/50 text-muted-foreground hover:text-primary rounded-md"
                         onClick={(e) => { e.stopPropagation(); handleAddNote(); }}
                       >
                          <Plus className="h-4 w-4" />
                       </Button>
                    </div>

                    <CollapsibleContent className="collapsible-content space-y-2">
                       {notes.map((note) => (
                          <div key={note.id} className="med-panel group flex items-stretch p-0 overflow-hidden hover:border-primary/40 transition-colors min-h-[60px]">
                             <div className="flex-grow p-3">
                               <div className="flex justify-between items-start mb-1">
                                  <span className="text-[9px] text-muted-foreground font-mono">{note.date}</span>
                               </div>
                               <p className="text-[11px] text-foreground/80 line-clamp-2 leading-relaxed">{note.content}</p>
                             </div>

                             <div className="flex items-center border-l border-border/30 bg-secondary/5">
                               <button
                                 onClick={() => { setEditingNote(note); setNoteEditorContent(note.content); }}
                                 className="h-full w-8 flex items-center justify-center text-muted-foreground hover:text-primary hover:bg-secondary/20 transition-colors"
                                 title="Edit Note"
                               >
                                 <Pencil className="h-4 w-4" />
                               </button>
                               <div className="w-px h-1/2 bg-border/30"></div>
                               <button
                                 onClick={(e) => { e.stopPropagation(); toggleNoteSelection(note); }}
                                 className={`h-full w-8 flex items-center justify-center transition-colors ${
                                   selectedNotes.find(n => n.id === note.id)
                                     ? 'bg-primary/10 text-primary'
                                     : 'text-muted-foreground hover:text-primary hover:bg-secondary/20'
                                 }`}
                                 title="Attach to prompt"
                               >
                                 <PlusCircle className={`h-4 w-4 ${selectedNotes.find(n => n.id === note.id) ? 'rotate-45' : ''} transition-transform`} />
                               </button>
                             </div>
                          </div>
                       ))}
                       {notes.length === 0 && (
                         <p className="text-[10px] text-muted-foreground text-center py-3">No notes yet.</p>
                       )}
                    </CollapsibleContent>
                 </Collapsible>

                 {/* 6. Imaging History (Collapsible) */}
                 <Collapsible open={isImagingHistoryOpen} onOpenChange={setIsImagingHistoryOpen} className="space-y-2" data-tutorial="imaging-history">
                    <div className="flex items-center justify-between gap-2 pr-1">
                       <CollapsibleTrigger asChild>
                          <Button variant="ghost" size="sm" className="flex-grow h-8 p-0 hover:bg-transparent text-xs font-bold text-muted-foreground uppercase tracking-wide flex items-center gap-2 justify-start">
                             <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-200 ${isImagingHistoryOpen ? '' : '-rotate-90'}`} />
                             <Calendar className="h-3.5 w-3.5" /> Imaging History
                          </Button>
                       </CollapsibleTrigger>
                       <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 hover:bg-secondary/50 text-muted-foreground hover:text-primary rounded-md"
                            onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                            disabled={isUploading || !!pendingUpload}
                          >
                            {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                          </Button>
                          <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/jpeg,image/png,.jpg,.jpeg,.png,.dcm,application/dicom"
                            className="hidden"
                            onChange={handleFileSelected}
                          />
                       </div>
                    </div>

                    <CollapsibleContent className="collapsible-content space-y-3">
                       {uploadError && (
                         <p className="text-xs text-destructive text-center py-1">{uploadError}</p>
                       )}
                       {images.map((item) => (
                          <div
                             key={item.id}
                             className={`group med-panel p-3 cursor-pointer transition-all hover:border-primary/40 relative ${
                               selectedImages.find((img) => img.id === item.id) ? 'ring-1 ring-primary border-primary bg-primary/5' : ''
                             }`}
                          >
                             <div className="flex gap-4" onClick={() => toggleImageSelection(item)}>
                                {/* Thumbnail */}
                                <div className="h-20 w-20 shrink-0 rounded overflow-hidden bg-black border border-border relative">
                                   {/* eslint-disable-next-line @next/next/no-img-element */}
                                   {item.src ? (
                                     <img
                                       src={item.src}
                                       alt="scan"
                                       className="h-full w-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                                       onError={(e) => {
                                         const target = e.currentTarget;
                                         target.style.display = 'none';
                                         target.parentElement?.classList.add('flex', 'items-center', 'justify-center');
                                         const fallback = document.createElement('div');
                                         fallback.className = 'flex flex-col items-center justify-center text-muted-foreground/50';
                                         fallback.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>';
                                         target.parentElement?.appendChild(fallback);
                                       }}
                                     />
                                   ) : (
                                     <div className="h-full w-full flex items-center justify-center text-muted-foreground/50">
                                       <ImageIcon className="h-6 w-6" />
                                     </div>
                                   )}
                                   {selectedImages.find((img) => img.id === item.id) && (
                                      <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
                                         <CheckCircle2 className="h-6 w-6 text-primary drop-shadow-md" />
                                      </div>
                                   )}
                                </div>

                                {/* Info */}
                                <div className="flex-grow min-w-0">
                                   <div className="flex justify-between items-start">
                                      <span className="text-sm font-semibold text-foreground truncate">{item.modality}</span>
                                      <span className="text-[10px] text-muted-foreground whitespace-nowrap bg-background px-1.5 py-0.5 rounded border border-border">{item.date}</span>
                                   </div>

                                   <div className="mt-2 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                                      <span className="font-medium text-primary/80">Reading: </span>
                                      {item.reading}
                                   </div>

                                </div>
                             </div>
                             {/* Delete button */}
                             <button
                               onClick={(e) => { e.stopPropagation(); handleDeleteImage(item.id); }}
                               className="absolute top-2 right-2 h-6 w-6 bg-destructive/80 text-destructive-foreground rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive"
                               title="Delete image"
                             >
                               <Trash2 className="h-3 w-3" />
                             </button>
                          </div>
                       ))}
                       {images.length === 0 && (
                         <p className="text-[10px] text-muted-foreground text-center py-3">No imaging records.</p>
                       )}
                    </CollapsibleContent>
                 </Collapsible>

                 </>
                 )}

               </div>
             </ScrollArea>

             {/* Note Editor Overlay */}
             {editingNote && (
               <div className="absolute inset-4 z-50 bg-background/95 backdrop-blur-xl border border-primary/20 rounded-xl shadow-2xl flex flex-col p-4 animate-in zoom-in-95 duration-200">
                  <div className="flex justify-between items-center mb-4">
                     <h3 className="font-semibold text-sm flex items-center gap-2">
                        <StickyNote className="h-4 w-4 text-primary" />
                        {editingNote === 'new' ? 'New Note' : 'Edit Note'}
                     </h3>
                     <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setEditingNote(null)}>
                        <X className="h-4 w-4" />
                     </Button>
                  </div>

                  <textarea
                    value={noteEditorContent}
                    onChange={(e) => setNoteEditorContent(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') {
                        setEditingNote(null);
                        setNoteEditorContent('');
                      }
                    }}
                    placeholder="Enter clinical observations..."
                    className="flex-grow bg-secondary/20 border border-border rounded-md p-3 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary/50 mb-4"
                    autoFocus
                  />

                  <div className="flex justify-between items-center">
                     {editingNote !== 'new' && typeof editingNote !== 'string' ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:bg-destructive/10 hover:text-destructive h-8"
                          onClick={() => handleDeleteNote(editingNote.id)}
                        >
                           <Trash2 className="h-3.5 w-3.5 mr-2" /> Delete
                        </Button>
                     ) : <div />}

                     <div className="flex gap-2">
                        <Button variant="outline" size="sm" className="h-8" onClick={() => setEditingNote(null)}>Cancel</Button>
                        <Button size="sm" className="h-8" onClick={handleSaveNote}>
                           <Save className="h-3.5 w-3.5 mr-2" /> Save
                        </Button>
                     </div>
                  </div>
               </div>
             )}
          </div>
        </div>

        {/* RIGHT PANE: Chat & Visualization */}
        <div
           className={`flex flex-col bg-background/50 relative transition-all duration-500 ease-[cubic-bezier(0.25,1,0.5,1)] overflow-hidden ${
             !rightOpen ? 'w-12 cursor-pointer hover:bg-secondary/10' : (!leftOpen ? 'flex-1' : 'w-[60%]')
           }`}
           onClick={() => !rightOpen && toggleRightPane()}
        >
           {/* Collapsed Header (Vertical) */}
           <div className={`absolute inset-0 flex items-center justify-center transition-opacity duration-300 ${!rightOpen ? 'opacity-100 delay-200' : 'opacity-0 pointer-events-none'}`}>
             <div className="rotate-180 [writing-mode:vertical-rl] text-xs font-bold text-muted-foreground tracking-widest whitespace-nowrap flex items-center gap-3">
                <Activity className="h-4 w-4 rotate-90" /> AI ANALYSIS
             </div>
           </div>

           {/* Center Content */}
           <div data-tutorial="chat-panel" className={`flex-grow flex flex-col relative min-w-[400px] min-h-0 transition-opacity duration-300 ${!rightOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}>

              {/* Chat Header */}
              <div
                className="h-12 px-6 flex items-center justify-between border-b border-border/50 bg-secondary/5 shrink-0 cursor-pointer group select-none"
                onClick={(e) => { e.stopPropagation(); toggleRightPane(); }}
              >
                <h3 className="font-medium text-sm flex items-center gap-2 text-primary group-hover:text-foreground transition-colors">
                   <Activity className="h-4 w-4" /> AI Analysis & Visualization
                   <ChevronRight className={`h-4 w-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300 text-muted-foreground ${!leftOpen ? 'hidden' : ''}`} />
                </h3>
              </div>

              {/* Chat Area */}
              <ScrollArea className="flex-grow min-h-0">
                    <div className="p-6 flex flex-col gap-6 min-h-full">

                       {/* Initial State / Welcome */}
                       {messages.length === 0 && (
                          <div className="flex-grow flex flex-col items-center justify-center opacity-40 mt-20 select-none pointer-events-none">
                             <div className="h-40 w-40 rounded-full border border-primary/20 flex items-center justify-center relative">
                                <div className="absolute inset-0 border border-primary/10 rounded-full animate-ping opacity-20" />
                                <Activity className="h-16 w-16 text-primary/30" />
                             </div>
                             <p className="mt-6 text-sm font-light tracking-wide text-muted-foreground">Select images from history to analyze</p>
                          </div>
                       )}

                       {/* Messages */}
                       {messages.map((msg, i) => (
                         <div key={i} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2`}>
                            <div className={`max-w-[85%] rounded-2xl px-5 py-4 shadow-sm ${
                               msg.sender === 'user'
                                 ? 'bg-primary text-primary-foreground rounded-br-sm'
                                 : 'bg-card border border-border text-foreground rounded-bl-sm'
                            }`}>
                               {msg.text && (
                                 msg.sender === 'ai' ? (
                                   <div className="text-sm leading-relaxed prose prose-sm prose-invert max-w-none prose-headings:text-foreground prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1 prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0 prose-strong:text-foreground">
                                     <ReactMarkdown>{msg.text}</ReactMarkdown>
                                   </div>
                                 ) : (
                                   <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                                 )
                               )}

                               {/* Streaming indicator */}
                               {msg.sender === 'ai' && !msg.text && isStreaming && (
                                 <Loader2 className="h-4 w-4 animate-spin text-primary" />
                               )}

                               {(msg.imageCount || 0) > 0 || (msg.noteCount || 0) > 0 ? (
                                  <div className={`flex flex-wrap items-center gap-2 mt-2 text-[10px] font-medium ${msg.sender === 'user' ? 'text-primary-foreground/90' : 'text-muted-foreground'}`}>
                                     {(msg.imageCount || 0) > 0 && (
                                        <span className="flex items-center gap-1 bg-black/10 px-2 py-0.5 rounded-full">
                                           <Paperclip className="h-3 w-3" /> +{msg.imageCount} Images
                                        </span>
                                     )}
                                     {(msg.noteCount || 0) > 0 && (
                                        <span className="flex items-center gap-1 bg-black/10 px-2 py-0.5 rounded-full">
                                           <StickyNote className="h-3 w-3" /> +{msg.noteCount} Notes
                                        </span>
                                     )}
                                  </div>
                               ) : null}

                               <div className={`text-[10px] mt-1 opacity-60 font-mono ${msg.sender === 'user' ? 'text-primary-foreground' : 'text-muted-foreground'}`}>
                                 {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                               </div>
                            </div>
                         </div>
                       ))}
                       <div ref={messagesEndRef} className="h-4" />
                    </div>
                 </ScrollArea>

              {/* Input Area (Docked to bottom of Right Pane) */}
              <div className="p-4 bg-background/80 backdrop-blur-xl border-t border-border">
                 <div className="relative max-w-4xl mx-auto w-full">
                    {/* Selected Attachments Cards (Chronological) */}
                    {allAttachments.length > 0 && (
                       <>
                         <div className="absolute -top-36 left-0 right-0 flex items-end gap-3 overflow-x-auto px-1 pb-4 scrollbar-none">
                            {allAttachments.map((item: any) => (
                               <div key={`${item.type}-${item.id}`} className={`group relative w-24 h-28 shrink-0 rounded-lg border overflow-hidden shadow-xl animate-in fade-in slide-in-from-bottom-4 hover:ring-2 transition-all ${
                                  item.type === 'alert' ? 'border-amber-500/30 hover:ring-amber-500/50' : 'border-primary/30 hover:ring-primary/50'
                               }`}>
                                  {item.type === 'image' ? (
                                    /* eslint-disable-next-line @next/next/no-img-element */
                                    <img src={item.src} alt="thumb" className="h-full w-full object-cover" />
                                  ) : item.type === 'alert' ? (
                                    <div className="h-full w-full bg-amber-500/10 p-2 flex flex-col items-center justify-center pt-4 pb-8">
                                       <ShieldAlert className="h-8 w-8 text-amber-500/40 mb-2 animate-pulse" />
                                       <div className="text-[7px] text-amber-200/60 line-clamp-4 text-center leading-tight">{item.content}</div>
                                    </div>
                                  ) : (
                                    <div className="h-full w-full bg-secondary/10 p-2 flex flex-col items-center justify-center pt-4 pb-8">
                                       <StickyNote className="h-8 w-8 text-primary/40 mb-2" />
                                       <div className="text-[7px] text-muted-foreground line-clamp-4 text-center leading-tight">{item.content}</div>
                                    </div>
                                  )}

                                  {/* Info Badge */}
                                  <div className="absolute bottom-0 inset-x-0 bg-background/95 backdrop-blur-md py-1.5 px-1 border-t border-primary/20">
                                     <div className="text-[9px] font-bold text-foreground truncate text-center">{item.modality?.split('(')[0]?.trim() ?? 'Note'}</div>
                                     <div className="text-[8px] text-primary/80 font-mono text-center mt-0.5">{item.type === 'alert' ? 'CRITICAL' : getTimeAgo(item.date)}</div>
                                  </div>

                                  {/* Remove Button */}
                                  <button
                                    onClick={() => {
                                       if (item.type === 'image') toggleImageSelection(item);
                                       else if (item.type === 'alert') setIsAlertAttached(false);
                                       else toggleNoteSelection(item);
                                    }}
                                    className="absolute top-1.5 right-1.5 h-5 w-5 bg-destructive text-destructive-foreground rounded-full flex items-center justify-center shadow-sm opacity-0 group-hover:opacity-100 transition-all hover:scale-110"
                                    title="Remove"
                                  >
                                    <X className="h-3 w-3" />
                                  </button>
                               </div>
                            ))}
                         </div>

                         {/* Clear All Action */}
                         <div className="absolute -top-8 right-0">
                           <button
                             onClick={() => { setSelectedImages([]); setSelectedNotes([]); setIsAlertAttached(false); }}
                             className="text-[10px] font-medium text-muted-foreground hover:text-destructive transition-colors flex items-center gap-1.5 bg-background/80 px-2.5 py-1 rounded-full backdrop-blur-sm border border-border hover:border-destructive/30 shadow-sm"
                           >
                             <X className="h-3 w-3" /> Remove All
                           </button>
                         </div>
                       </>
                    )}

                    {/* Input Bar */}
                    <div className="flex items-center gap-2 bg-card border border-primary/20 p-1.5 rounded-full shadow-lg transition-all focus-within:ring-1 focus-within:ring-primary/30">
                       <div className="relative" ref={attachMenuRef}>
                         <Button
                           variant="ghost"
                           size="icon"
                           data-tutorial="attach-button"
                           className={`h-9 w-9 rounded-full transition-colors ${isAttachMenuOpen ? 'text-primary bg-primary/10' : 'text-muted-foreground hover:text-primary'}`}
                           onClick={() => setIsAttachMenuOpen(!isAttachMenuOpen)}
                         >
                           <Paperclip className="h-4 w-4" />
                         </Button>
                         {isAttachMenuOpen && (
                           <div className="absolute bottom-12 left-0 w-56 bg-card border border-border rounded-xl shadow-xl p-2 space-y-1 z-50 animate-in slide-in-from-bottom-2 duration-150">
                             <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider px-2 py-1">Attach to prompt</p>
                             {/* Attach all images */}
                             <button
                               onClick={() => { setSelectedImages(images); setIsAttachMenuOpen(false); }}
                               disabled={images.length === 0}
                               className="w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg hover:bg-primary/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                             >
                               <Calendar className="h-3.5 w-3.5 text-primary" />
                               <span>All images ({images.length})</span>
                               {selectedImages.length === images.length && images.length > 0 && <CheckCircle2 className="h-3 w-3 text-primary ml-auto" />}
                             </button>
                             {/* Attach individual images */}
                             {images.map((img) => (
                               <button
                                 key={img.id}
                                 onClick={() => { toggleImageSelection(img); }}
                                 className="w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg hover:bg-primary/5 transition-colors pl-7"
                               >
                                 <span className="truncate">{img.modality} — {img.date}</span>
                                 {selectedImages.find(i => i.id === img.id) && <CheckCircle2 className="h-3 w-3 text-primary ml-auto shrink-0" />}
                               </button>
                             ))}
                             <div className="border-t border-border my-1" />
                             {/* Attach notes */}
                             <button
                               onClick={() => { setSelectedNotes(notes); setIsAttachMenuOpen(false); }}
                               disabled={notes.length === 0}
                               className="w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg hover:bg-primary/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                             >
                               <StickyNote className="h-3.5 w-3.5 text-primary" />
                               <span>All notes ({notes.length})</span>
                               {selectedNotes.length === notes.length && notes.length > 0 && <CheckCircle2 className="h-3 w-3 text-primary ml-auto" />}
                             </button>
                             {/* Attach alert */}
                             {alertContent && (
                               <button
                                 onClick={() => { setIsAlertAttached(!isAlertAttached); setIsAttachMenuOpen(false); }}
                                 className="w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg hover:bg-primary/5 transition-colors"
                               >
                                 <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
                                 <span>Clinical Alert</span>
                                 {isAlertAttached && <CheckCircle2 className="h-3 w-3 text-primary ml-auto" />}
                               </button>
                             )}
                             <div className="border-t border-border my-1" />
                             {/* Upload new image */}
                             <button
                               onClick={() => { chatFileInputRef.current?.click(); setIsAttachMenuOpen(false); }}
                               disabled={isUploading || !!pendingUpload || images.length >= 5}
                               className="w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg hover:bg-primary/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                             >
                               <PlusCircle className="h-3.5 w-3.5 text-emerald-500" />
                               <span>{isUploading ? 'Uploading...' : 'Upload new image'}</span>
                             </button>
                           </div>
                         )}
                         {/* Hidden file input lives outside the menu so it persists after menu closes */}
                         <input
                           ref={chatFileInputRef}
                           type="file"
                           accept="image/jpeg,image/png,.jpg,.jpeg,.png,.dcm,application/dicom"
                           className="hidden"
                           onChange={(e) => handleFileSelected(e, true)}
                         />
                       </div>
                       <Input
                          value={prompt}
                          onChange={(e) => setPrompt(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && !isStreaming && handleSubmit()}
                          placeholder="Type your clinical query here..."
                          className="border-none shadow-none focus-visible:ring-0 bg-transparent text-sm h-10 px-2"
                          disabled={isStreaming}
                       />
                       <button
                          data-tutorial="mode-pill"
                          onClick={() => setLockedMode(m =>
                            m === null ? 'analysis'
                            : m === 'analysis' ? 'discussion'
                            : null
                          )}
                          title={
                            lockedMode === null
                              ? `Auto: ${effectiveMode} (click to lock to Analysis)`
                              : lockedMode === 'analysis'
                              ? `Locked: Analysis (click to switch to Discussion)`
                              : `Locked: Discussion (click to unlock)`
                          }
                          className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-all shrink-0 ${
                            effectiveMode === 'analysis'
                              ? 'bg-primary/10 text-primary hover:bg-primary/20'
                              : 'bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20'
                          }`}
                       >
                          {effectiveMode === 'analysis' ? <ScanLine className="h-3 w-3" /> : <MessageCircle className="h-3 w-3" />}
                          <span>{effectiveMode === 'analysis' ? 'Analysis' : 'Discussion'}</span>
                          {lockedMode ? <Lock className="h-2.5 w-2.5 opacity-60" /> : <span className="h-1.5 w-1.5 rounded-full bg-current opacity-50 animate-pulse" />}
                       </button>
                       <Button
                          onClick={handleSubmit}
                          size="icon"
                          disabled={isStreaming}
                          className={`h-9 w-9 rounded-full transition-all ${
                             prompt.trim() || selectedImages.length > 0 ? 'bg-primary text-primary-foreground shadow-md' : 'bg-secondary text-muted-foreground'
                          }`}
                       >
                          {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                       </Button>
                    </div>
                 </div>
              </div>
           </div>
        </div>

      </div>
      )}

      {/* ─── Universal Image Upload Modal ──────────────────────── */}
      <Dialog open={!!pendingUpload} onOpenChange={(open) => { if (!open) setPendingUpload(null); }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-sm">
              <ImageIcon className="h-4 w-4 text-primary" /> Upload Chest X-Ray
            </DialogTitle>
          </DialogHeader>
          {pendingUpload && (
            <div className="space-y-4 pt-1">
              {/* Image preview */}
              <div className="relative h-44 w-full rounded-lg overflow-hidden bg-black border border-border">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                {uploadPreviewUrl && (
                  <img src={uploadPreviewUrl} alt="Preview" className="h-full w-full object-contain" />
                )}
              </div>
              <div className="flex items-center justify-between text-[10px] text-muted-foreground font-mono -mt-1">
                <span className="truncate max-w-[70%]">{pendingUpload.file.name}</span>
                <span>{(pendingUpload.file.size / 1024).toFixed(0)} KB</span>
              </div>

              {/* Date & time picker */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5 text-primary" /> Study Date &amp; Time
                </label>
                <input
                  type="datetime-local"
                  value={uploadDateTime}
                  onChange={(e) => setUploadDateTime(e.target.value)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50 text-foreground [color-scheme:dark]"
                />
                <p className="text-[10px] text-muted-foreground leading-snug">
                  Sets the study&apos;s temporal position in the imaging timeline. Defaults to now.
                </p>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-2 pt-1">
                <Button variant="outline" size="sm" className="h-9" onClick={() => setPendingUpload(null)}>
                  Cancel
                </Button>
                <Button
                  size="sm"
                  className="h-9"
                  onClick={handleConfirmUpload}
                  disabled={!uploadDateTime}
                >
                  <Upload className="mr-1.5 h-3.5 w-3.5" /> Upload Image
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {showTutorial && <TutorialOverlay onDone={() => setShowTutorial(false)} />}
    </div>
  );
};

export default Dashboard;

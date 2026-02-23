## Introduction

This web application empowers physicians to harness AI-driven temporal analysis of chest X-rays, transforming how radiological progression is understood and communicated. The interface must strike a critical balance: intuitive enough for rapid clinical workflows where doctors need answers in seconds, yet visually refined to inspire confidence in a medical-grade tool handling sensitive patient data. Every interaction—from uploading X-rays to reviewing AI-generated reports—should feel effortless and trustworthy. The design philosophy centers on progressive disclosure: presenting essential information prominently (patient timeline, latest findings, critical changes) while keeping advanced features (custom image selection, detailed comparisons, historical analysis) accessible but unobtrusive. Visual clarity is paramount: chronological timelines must be instantly scannable, X-ray comparisons side-by-side with synchronized zooming, and AI insights highlighted with clear visual hierarchy distinguishing stable findings from concerning changes. This isn't just another dashboard—it's a clinical decision support tool where every pixel serves the physician's need to quickly understand "what changed, why it matters, and what to do next." Beauty here isn't decorative; it's functional elegance that reduces cognitive load during high-stakes medical assessments.


## Completed

- Patient search and selection with Supabase-backed data
- Full authentication flow (JWT + bcrypt)
- Dual-pane clinical dashboard with collapsible panels
- Editable vitals, clinical alerts, and patient notes (CRUD)
- Imaging history with signed-URL thumbnails and multi-select
- Real-time streaming AI chat via SSE (MedGemma 4B + LoRA adapter)
- Conversation persistence to Supabase
- System prompt and prompt-wrapping fixes for natural model responses
- max_tokens bug fix ensuring full-length model output

## Next Steps

### Priority 1 — Quick Wins (< 1 hour each)

1. **Fix consultations endpoint (500 error)**
   - `GET /patients/{id}/consultations` currently returns 500
   - Debug Supabase `.range()` pagination in `consultations.py`
   - Unblocks the "Past Consultations" section in the sidebar

2. **Error toast notifications**
   - API failures are silently swallowed in the frontend
   - Add a lightweight toast/snackbar system (e.g. sonner or react-hot-toast)
   - Surface errors for failed note saves, auth expiry, streaming failures

3. **Image lightbox / preview**
   - Clicking an X-ray thumbnail should open a larger preview
   - Currently click only toggles selection for AI context
   - Add a Dialog-based lightbox with zoom support

### Priority 2 — Medium Impact (1-3 hours each)

4. **Load past conversation messages**
   - Clicking a past consultation should reload its messages in the chat pane
   - Backend endpoint `GET /consultations/{id}` already exists
   - Frontend just needs to call it and populate the messages array

5. **Vital signs trend sparklines**
   - Small inline charts next to HR / SpO2 / BP showing recent history
   - Visually impressive and medically relevant for judges
   - Requires a new `GET /patients/{id}/vitals/history` endpoint

6. **Export consultation as PDF**
   - "Download Report" button that generates a PDF with:
     - Patient demographics, vitals, and alert status
     - AI analysis text and attached image thumbnails
   - Use a client-side library (e.g. jsPDF or react-pdf)

### Priority 3 — Demo Wow-Factor

7. **Side-by-side image comparison**
   - Select two images and compare with a slider or toggle overlay
   - Synchronized zoom/pan across both images
   - Very visual and impressive for a live demo

8. **Streaming markdown rendering**
   - AI responses contain markdown (bold, bullets, headers)
   - Currently rendered as plain text in the chat bubble
   - Use react-markdown to render formatted output during streaming

### Priority 4 — Polish

9. **Loading skeletons**
   - Replace the single spinner with skeleton placeholders
   - Shimmer effect for patient info, vitals, notes, and imaging cards

10. **Split Dashboard.tsx (~990 lines)**
    - Extract into smaller components: VitalsPanel, AlertCard, NotesSection, ImagingHistory, ChatPane, AttachmentTray
    - Improves readability and makes future changes easier

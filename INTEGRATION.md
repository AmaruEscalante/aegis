# Aegis Middleware ↔ Frontend Integration

## What Was Done

Wired the real **Aegis classification bridge** into the chat and file-upload flows, replacing the mock keyword PII simulation in the backend. Added a live toggle, health indicator, and file analysis card to the frontend UI.

---

## Architecture After Integration

```
Frontend (Next.js :3000)
  │
  ├─ GET  /api/bridge/health  (every 30s) ──────────────────┐
  ├─ POST /api/bridge/toggle                                │
  ├─ POST /api/analyze  (on file upload)                   │
  └─ POST /api/chat  (streaming)                           │
                                                           ▼
Backend (FastAPI :8000)  ──────────► Aegis Bridge (:7523)
  │  api.py                            aegis_bridge.py
  │  • analyze_via_bridge()            POST /classify
  │  • bridge_enabled flag             GET  /health
  └─────────────────────────────────► Gemini 2.5 Flash (cloud)
                                       (only if not blocked)
```

### Verdict Flow

| Bridge verdict | Chat behavior | File analysis card |
|---|---|---|
| `classify_safe` | Pass through to Gemini | ✓ green "Safe to Send" |
| `flag_pii` | Warn + pass through | ⚠ yellow "PII Detected" + type tags |
| `block_transfer` | Hard stop, Gemini NOT called | ✕ red "Blocked" + send button disabled |
| `request_permission` | Warn + pass through | ? orange "Review Required" + Proceed/Cancel |

---

## Files Changed

### `backend/requirements.txt`
Added `httpx` for async HTTP calls from FastAPI to the bridge.

### `backend/api.py`
Complete rewrite from the mock scaffold. Key additions:

**New constants (module-level):**
```python
BRIDGE_URL = "http://127.0.0.1:7523"
bridge_enabled: bool = True   # toggled via /api/bridge/toggle
```

**`analyze_via_bridge(text)`** — async helper that:
1. `POST /classify` → gets `{tool, arguments, confidence, time_ms}`
2. Maps response to a unified dict returned to callers
3. Falls back to `classify_safe` on `ConnectError` or any exception (never blocks chat)

**`/api/chat`** — replaced mock `if "@" in msg` logic with:
- Calls `analyze_via_bridge()` when `bridge_enabled`
- `block_transfer` → yields blocked message and returns (no Gemini call)
- `flag_pii` → yields PII warning, then calls Gemini
- `request_permission` → yields review warning, then calls Gemini
- `classify_safe` / bridge off → calls Gemini directly

**Three new endpoints:**

| Endpoint | Purpose |
|---|---|
| `POST /api/analyze` | File analysis — takes `{text, filename}`, returns full analysis result |
| `GET /api/bridge/health` | Proxies bridge `/health`, adds `bridge_enabled` to response |
| `POST /api/bridge/toggle` | Flips `bridge_enabled` flag, returns new state |

### `frontend/src/app/globals.css`
Added pulse animation for the live status dot:
```css
@keyframes bridge-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.bridge-dot-online { animation: bridge-pulse 2s ease-in-out infinite; }
```

### `frontend/src/app/page.tsx`
Changes by category:

**New types:**
```typescript
interface FileAnalysisResult {
  success: boolean;
  classification: 'classify_safe' | 'flag_pii' | 'block_transfer' | 'request_permission';
  reason: string;
  confidence: number;
  pii_types: string;      // comma-separated, flag_pii only
  summary: string;
  execution_time_ms: number;
  filename: string;
}
type BridgeStatus = 'online' | 'offline' | 'unknown';
```

**New icon:** `IconShieldOff` — shown in toggle when bridge is OFF.

**New component: `FileAnalysisCard`**
- Rendered below the file attachment chip after upload analysis
- Loading state: Gemini spinner + "Analyzing with Aegis DataGuard..."
- Result state: color-coded verdict badge, reason text, PII type pills, timing
- Action buttons: "Proceed anyway" (escalate), "Remove file" (block)

**New state variables:**
```typescript
const [bridgeEnabled, setBridgeEnabled] = useState<boolean>(true);
const [bridgeStatus, setBridgeStatus]   = useState<BridgeStatus>('unknown');
const [fileAnalysis, setFileAnalysis]   = useState<FileAnalysisResult | null>(null);
const [isAnalyzing, setIsAnalyzing]     = useState<boolean>(false);
```

**New `useEffect` — bridge health polling:**
- Fires on mount + every 30 seconds
- Calls `GET /api/bridge/health`
- Sets `bridgeStatus` ('online' | 'offline') and syncs `bridgeEnabled` from backend

**New callbacks:**

| Callback | Purpose |
|---|---|
| `fetchBridgeHealth` | Polls bridge health endpoint |
| `handleBridgeToggle` | `POST /api/bridge/toggle`, updates local state |
| `handleAnalysisProceed` | Clears analysis card (user approved escalate) |
| `handleAnalysisCancel` | Clears file + analysis (user rejected) |

**Modified `handleFileChange`** — now `async useCallback`:
- Reads file as text (unchanged)
- If `bridgeEnabled`: calls `POST /api/analyze`, sets `fileAnalysis`
- `isAnalyzing` shows spinner during the call
- Bridge errors are silently swallowed — file upload never blocked by network failure

**Modified `submitMessage`:**
- Guards: `if (fileAnalysis?.classification === 'block_transfer') return`
- Clears `fileAnalysis` on successful submit

**Modified header (right side):**
- Replaced static "Privacy layer active" badge with:
  - **Aegis ON/OFF toggle pill** — green when ON, grey when OFF, calls `handleBridgeToggle`
  - **DataGuard status badge** — live pulsing dot (green/red/yellow) + label

**Modified file chip area:**
- X button now also clears `fileAnalysis`
- `FileAnalysisCard` rendered conditionally below chip when `isAnalyzing || fileAnalysis`

**Modified send button:**
- Disabled when `fileAnalysis?.classification === 'block_transfer'`

---

## Running the Stack

```bash
# 1. Ollama (if not running)
ollama serve

# 2. Aegis Bridge
python aegis_bridge.py

# 3. Backend
cd backend
pip install -r requirements.txt
uvicorn api:app --port 8000

# 4. Frontend
cd frontend
npm run dev
```

---

## Bridge API Contract

The backend calls the bridge at `http://127.0.0.1:7523`:

**`POST /classify`**
```json
// Request
{ "text": "<raw file content>" }

// Response
{
  "tool": "flag_pii",
  "arguments": { "types": "email, phone" },
  "confidence": 0.94,
  "time_ms": 187.2
}
```

**Tool names → internal verdict:**

| Bridge `tool` | Internal classification |
|---|---|
| `classify_safe` | `classify_safe` |
| `flag_pii` | `flag_pii` |
| `block_transfer` | `block_transfer` |
| `request_permission` | `request_permission` |

---

## Bridge Not Available?

The bridge needs:
- **Ollama** running locally with `gemma4:31b` pulled

When the bridge is down the frontend shows a red status dot and all classification gracefully degrades to pass-through.

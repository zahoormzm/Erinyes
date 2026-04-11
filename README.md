<p align="center">
  <img src="frontend/public/eirview-brand.png" alt="EirView" width="400"/>
</p>

# EirView

EirView is a full-stack health intelligence platform that combines deterministic health calculations, multi-source data ingestion, and AI-assisted coaching. It runs locally with a React frontend, a FastAPI backend, SQLite storage, and a small agent/tool layer for guided reasoning tasks.

## What It Does

- Computes biological age across cardiovascular, metabolic, musculoskeletal, and neurological subsystems
- Tracks health data from blood reports, body composition scans, Apple Health exports, meals, posture checks, and manual entries
- Projects medium-term health risks and supports what-if scenario simulation
- Provides contextual coaching for activity, nutrition, future-self reflection, and mental health support
- Surfaces reminders, alerts, specialist recommendations, and data freshness timelines

## Stack

**Frontend**
- React 19, Vite, Tailwind CSS, Zustand, Recharts

**Backend**
- FastAPI, SQLite with `aiosqlite`
- Deterministic health and risk logic in Python
- Claude and Gemini API integrations for parsing and coaching flows

**Supporting Services**
- Spotify Web API
- OpenWeatherMap
- USDA food data
- ONNX Runtime for face age inference
- MediaPipe Tasks for browser posture analysis

## Repository Layout

```
Health/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── formulas.py
│   ├── reminder_engine.py
│   ├── activity.py
│   ├── parsers.py
│   ├── alerts.py
│   ├── specialists.py
│   ├── reports.py
│   ├── family.py
│   ├── gamification.py
│   ├── spotify.py
│   ├── faceage.py
│   ├── posture_runner.py
│   ├── agents/
│   └── tools/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── api.js
│   │   ├── store.js
│   │   └── App.jsx
│   └── package.json
└── ...
```

## Design Philosophy

The central architectural decision is: **formulas compute, AI communicates.**

Every health number — biological age, risk projection, nutrition limits — comes from deterministic Python code based on peer-reviewed research. The AI models never generate a health number. They parse unstructured input, explain what the math produced, and decide which tools to invoke. Same inputs always produce the same outputs. The boundary between math and language model is explicit and auditable via the transparency page.

## Agent Architecture

The backend uses 6 specialized agents built on Claude's tool-use API:

| Agent | Role |
|---|---|
| **Orchestrator** | Receives user input and routes to the appropriate specialist agent |
| **Collector** | Parses unstructured documents — blood reports, fitness screenshots, food photos |
| **Mirror** | Computes and explains biological age across all four subsystems |
| **Time Machine** | Projects health risk curves 15 years forward and runs what-if simulations |
| **Coach** | Generates personalized recommendations using blood work, weather, AQI, and nutrition gaps |
| **Mental Health** | Conducts conversational assessments mapped to the PHQ-9 clinical scale |

Each agent calls deterministic tool functions for any calculation — it never does the math itself. Agents chain automatically: uploading a blood report triggers the Collector, which triggers the Mirror, Coach, and Time Machine in sequence. Every agent call is logged with prompt, token count, latency, and cost.

## Multi-Model Routing

The system routes between two models based on task type:

- **Claude** handles complex reasoning — mental health conversations, coaching, anything requiring nuance or clinical context
- **Gemini 2.5 Flash** handles fast vision tasks — identifying food in photos, reading fitness screenshots — at a fraction of the cost and under one second latency

The database is the shared context. The models never communicate with each other; they read from and write to the same source of truth.

## Formula References

The biological age engine is inspired by [PhenoAge (Levine et al., *Aging*, 2018)](https://www.aging-us.com/article/101414/text) and the [Klemera-Doubal method (2006)](https://pubmed.ncbi.nlm.nih.gov/16318865/), adapted into a four-subsystem model using consumer-available biomarkers.

| Subsystem | Weight | Key inputs | Sources |
|---|---|---|---|
| Cardiovascular | 0.30 | Resting HR, LDL/HDL ratio, BP, VO2 max | Framingham Heart Study; D'Agostino et al., *Circulation*, 2008; ATP III guidelines |
| Metabolic | 0.25 | Fasting glucose, HbA1c, triglycerides, BMI, visceral fat | GBD 2015 Obesity Collaborators; ADA prediabetic thresholds |
| Musculoskeletal | 0.20 | Body fat %, muscle mass, bone density, posture score, gait asymmetry | Standard clinical reference ranges |
| Neurological | 0.25 | HRV (SDNN), sleep stages, sleep duration, PHQ-9 score | ESC HRV standards, 1996; Cappuccio et al., *Sleep*, 2010 |

Additional references:
- **VO2 max weighting** — Ross et al., *Circulation*, 2016 (strongest single predictor of cardiovascular longevity)
- **Vitamin D thresholds** — Holick, *NEJM*, 2007; Endocrine Society guidelines, 2011
- **PHQ-9** — Kroenke, Spitzer & Williams, *Journal of General Internal Medicine*, 2001
- **FaceAge model** — Biological age from facial imaging, *The Lancet Digital Health*, 2025; trained on 58,851 individuals, runs locally via ONNX (no cloud call, image never leaves the device)

## Core Features

**Health Modeling**
- Biological age scoring across subsystems
- Mental wellness scoring
- Risk projection and habit simulation
- Workout and nutrition target generation

**Data Ingestion**
- Blood report upload (PDF parsing)
- Cult.fit / body composition scan upload
- Apple Health zip or XML import
- Meal photo or text analysis
- Face age estimation
- Browser-based posture checks

**Coaching & Guidance**
- Coach chat, mental health chat, Future Self chat
- Contextual reminders and specialist recommendations
- Doctor-report generation

## Local Development

**Requirements**
- Python 3.12+
- Node.js 20+
- npm

### 1. Set up the backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Set up the frontend

```bash
cd frontend
npm install
```

### 3. Configure environment variables

Copy `.env.example` to `.env` at the repository root and fill in the keys you need.

Minimum setup:

```env
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
EIRVIEW_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Optional integrations:

```env
OPENWEATHERMAP_API_KEY=
USDA_API_KEY=DEMO_KEY
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5173/callback
FACEAGE_MODEL_PATH=FaceAge-main/models/faceage_model.onnx
FACE_LANDMARKER_PATH=FaceAge-main/models/face_landmarker.task
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=EirView Alerts
```

### 4. Run

Backend:

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir backend
```

Frontend (in a separate terminal):

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

- Frontend: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/docs

## Notes

**Face Age** — requires local model assets under `FaceAge-main/models/`. That directory is not committed to the repo.

**Posture** — runs entirely in the browser via MediaPipe Tasks Web; readings are stored through the backend.

**Weather / AQI** — falls back to cached/default conditions if `OPENWEATHERMAP_API_KEY` is not set.

**Spotify** — per-user OAuth; the redirect URI in your Spotify developer dashboard must match the value in `.env`.

## Validation

```bash
# From repo root
python3 -m py_compile backend/main.py backend/formulas.py backend/reminder_engine.py backend/activity.py

cd frontend
npm run build
```

# 🎬 Nexus Vlog Memory

[![Vue](https://img.shields.io/badge/Vue-3.x-42b883?logo=vue.js&logoColor=white)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.11x-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Run%20%7C%20GCS%20%7C%20Firestore-4285F4?logo=googlecloud&logoColor=white)](https://cloud.google.com/)
[![Vertex AI](https://img.shields.io/badge/Vertex%20AI-Veo%20%7C%20Gemini-FF6F00?logo=google&logoColor=white)](https://cloud.google.com/vertex-ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Nexus Vlog Memory** is an AI-powered, cinematic vlog generation platform. Upload a photo of any real-world landmark, and the system autonomously researches the location, writes a compelling narration, generates a custom 5-second AI video clip (via Google Veo), and stitches everything into a professional Vlog with crossfade transitions, landmark captions, and adaptive background music.

---

## ✨ Key Features

| Feature | Technology |
|---|---|
| 🗺️ Interactive landmark map | Vue 3 + Leaflet.js |
| 🤖 AI narration & prompt writing | Gemini 2.0 Flash |
| 🎥 5-second AI video generation | Vertex AI Veo 2 |
| ✂️ Cinematic stitching (xfade + captions + BGM) | Pure FFmpeg |
| ☁️ Cloud storage & persistence | GCS + Firestore |
| 🔒 Multi-room data sandbox | Room-code isolation |
| 🌍 Multi-location support | Dynamic location switching |

---

## 🏗️ Architecture

![Architecture Diagram](./architecture.png)

```
┌─────────────────────┐     REST API      ┌──────────────────────────┐
│   Vue 3 Frontend    │ ◄────────────────► │   FastAPI Backend         │
│  (Vite + Leaflet)   │                   │   (ai_video_engine/)      │
└─────────────────────┘                   └───────────┬──────────────┘
                                                      │
                          ┌───────────────────────────┼────────────────────────┐
                          │                           │                        │
                ┌─────────▼────────┐   ┌─────────────▼──────┐   ┌────────────▼──────┐
                │  Gemini 2.0 Flash│   │  Vertex AI Veo 2   │   │  Google Cloud      │
                │  (narration,     │   │  (5s clip          │   │  (GCS blob store,  │
                │   prompt guard)  │   │   generation)      │   │   Firestore DB)    │
                └──────────────────┘   └────────────────────┘   └───────────────────┘
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.10 – 3.12
- Node.js 18+
- FFmpeg (must be in system `PATH`)
- A Google Cloud project with Vertex AI, GCS, and Firestore enabled

> **Hardware**: The backend runs on standard developer hardware. No cloud GPU is required. Our demo was developed on an AMD Ryzen 5 machine with a GTX 1650 — all heavy AI inference runs on Google Cloud APIs.

---

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/nexus-vlog-memory.git
cd nexus-vlog-memory
```

---

### 2. Configure Environment Variables

Create `ai_video_engine/.env` from the example below. **Never commit real values.**

```env
# ── Google Cloud Platform ──────────────────────────
GCP_PROJECT_ID=your-gcp-project-id
GCS_BUCKET_NAME=your-gcs-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=./secrets/your-service-account.json

# ── Gemini / Vertex AI ─────────────────────────────
GEMINI_API_KEY=your-gemini-api-key
VERTEX_AI_LOCATION=us-central1

# ── Firestore ──────────────────────────────────────
FIRESTORE_PROJECT_ID=your-gcp-project-id
```

> ⚠️ Place your GCP Service Account JSON key in `ai_video_engine/secrets/` — this directory is gitignored and will never be committed.

---

### 3. Backend Setup

```bash
# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
cd ai_video_engine
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The FastAPI server starts at **http://localhost:8000**.  
Interactive docs: **http://localhost:8000/docs**

---

### 4. Frontend Setup

```bash
cd wander_canvas_frontend
npm install
npm run dev
```

The frontend starts at **http://localhost:5173**.

---

## 🎮 Demo Walkthrough

Once both servers are running:

1. **Open** `http://localhost:5173` in your browser.
2. **Select a location** from the dropdown (e.g. `USS` for Universal Studios Singapore).
3. **Click a landmark pin** on the map to open the Editor.
4. **Upload a photo** from `test_assets/` to populate the landmark with a real image.
5. **Click "Generate AI Vlog Clip"** — Gemini will write a narration and Veo will render a 5-second video (takes ~60–90s).
6. Repeat for multiple landmarks.
7. **Click "Stitch Nexus Vlog"** in the sidebar — the backend will download all clips via GCS SDK, apply xfade transitions, overlay landmark captions, and mix the BGM from `test_assets/default_bgm.mp3`.
8. The finished Vlog appears in the **Vlog History** panel. Click **▶** to watch or **⬇** to download.

---

## 📁 Project Structure

```
nexus-vlog-memory/
├── ai_video_engine/          # FastAPI backend
│   ├── main.py               # API routes
│   ├── services/
│   │   ├── gemini_agent.py   # Narration & prompt generation
│   │   ├── video_generator.py # Veo video generation
│   │   ├── video_stitcher.py  # FFmpeg stitching engine
│   │   ├── gcs_client.py     # GCS SDK wrapper
│   │   ├── firestore_client.py
│   │   └── task_processor.py
│   ├── models/               # Pydantic task models
│   ├── core/                 # Config
│   └── secrets/              # 🔒 gitignored — place GCP keys here
├── wander_canvas_frontend/   # Vue 3 + Vite frontend
│   └── src/
│       ├── components/       # Sidebar, Map, EditorModal, etc.
│       ├── stores/           # Pinia landmark store
│       └── types/            # TypeScript types
├── test_assets/              # Sample media for demo
│   └── default_bgm.mp3       # Background music for Vlog
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🛡️ Security Notes

- All GCP credentials are stored in `ai_video_engine/secrets/` which is **gitignored**.
- Signed URLs expire in 60 minutes; the stitcher bypasses this by using the GCS SDK directly (`blob.download_to_filename()`).
- The Gemini prompt guard (`validate_and_enhance_video_prompt`) automatically strips copyright/IP references and harmful content before passing prompts to Veo.

---

## 🧑‍💻 Built With

- [Vue 3](https://vuejs.org/) + [Vite](https://vitejs.dev/) + [TypeScript](https://www.typescriptlang.org/)
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- [Google Gemini API](https://ai.google.dev/)
- [Vertex AI Veo 2](https://cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos)
- [Google Cloud Storage](https://cloud.google.com/storage) + [Firestore](https://cloud.google.com/firestore)
- [Leaflet.js](https://leafletjs.com/) for interactive maps
- [FFmpeg](https://ffmpeg.org/) for cinematic video stitching

---

## 📄 License

MIT © 2026 Nexus Team

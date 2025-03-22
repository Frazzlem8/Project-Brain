# 🎬 FraseLabs Shorts Automation Toolkit

Turn long YouTube videos into high-quality, engaging Shorts — automatically.

This toolkit uses a Python backend powered by Whisper, MoviePy, and Ollama for transcription, clipping, and AI-generated metadata, and a sleek React + Tailwind frontend for control and monitoring.

---

## 🚀 Demo

> 📹 **Watch the video walkthrough**  
[https://youtu.be/pFXHBmLxM_Q](https://youtu.be/pFXHBmLxM_Q)


---

## 🧰 Tech Stack

- **Backend**: Python, Whisper, yt-dlp, FFmpeg, MoviePy, Ollama
- **Frontend**: Next.js + React (TypeScript) + Tailwind CSS
- **Streaming**: Real-time logs via Server-Sent Events (SSE)
- **Extras**: YouTube Data API for uploads

---

## 📦 Setup Instructions

### 1. Clone the Repo

```bash
git clone https://github.com/fraselabs/ProjectBrain
cd ProjectBrain/site
```

---

## ⚙️ Backend Setup

Handles downloading, transcribing, clipping, metadata generation, and YouTube upload.

✅ Prerequisites

- **Python 3.10**
- **FFmpeg installed (brew install ffmpeg)**
- **Ollama running locally**
- **Whisper + yt-dlp + moviepy**


## 🔧 Setup

### Create a virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

### Install dependencies
pip install -r requirements.txt
python3.10 -m spacy download en_core_web_sm

### Example requirements.txt:

whisper
spacy
moviepy
yt-dlp
ollama
google-auth
google-auth-oauthlib
google-api-python-client


## 🔌 Start the Node Backend

```bash
npm install express cors body-parser
node backend.js
```

This enables real-time communication with the Python script via GET /api/run-script-stream.

---

## 💻 Frontend Setup

Web interface to run and monitor automation in real-time.

```bash
npx create-next-app@latest shorts-frontend --typescript
cd shorts-frontend
```

Replace app/page.tsx and app/globals.css with your custom files.

## 🖌 Install Tailwind & UI Dependencies

```bash
npm install tailwindcss postcss autoprefixer
npm install @shadcn/ui react react-dom
npx tailwindcss init -p

```

---

## ▶️ Run the Dev Server

```bash
npm run dev
```

Then open http://localhost:3000 in your browser.

---

## 🧪 Features
- ✅ YouTube video downloader
- ✅ Whisper transcription
- ✅ AI-powered keyword detection
- ✅ Automatic clip cutting & resizing (vertical format)
- ✅ Metadata generation (title/description via Ollama)
- ✅ Optional label overlays (or skip if unwanted)
- ✅ Live streaming logs in frontend
- ✅ YouTube upload with metadata
- ✅ Real-time event handling with SSE

---

## 📂 Folder Structure

/shorts-frontend       # React + Tailwind frontend
/backend.js            # Express API to trigger Python scripts
/shorts_automation.py  # Core Python automation script
/downloads             # Output folder for generated content

---

## 🙌 Built by FraseLabs

Have feature requests? Want help deploying this at scale?
📩 Reach out to us — we love helping creators automate their workflows.

---


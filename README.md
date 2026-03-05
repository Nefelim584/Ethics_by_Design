# Audio transcription (Mistral / Voxtral)

This project transcribes an audio file using Mistral's Voxtral transcription API and saves the transcript to a `.txt` file.

## Setup

1. Create a virtualenv (optional) and install dependencies:

```bash
pip install -U pip
pip install .
```

2. Export your Mistral API key:

```bash
export MISTRAL_API_KEY="YOUR_KEY_HERE"
```

## Run

### Backend (Flask API)

```bash
python3 main.py /path/to/audio.mp3
```

This writes `/path/to/audio.txt`.

### Options

- Choose a different output path:

```bash
python3 main.py /path/to/audio.mp3 --out ./transcript.txt
```

- Force a language (otherwise auto-detect):

```bash
python3 main.py /path/to/audio.mp3 --language en
```

- Pick a model:

```bash
python3 main.py /path/to/audio.mp3 --model voxtral-mini-latest
```

### Web UI

1. Start the Flask backend:

```bash
python3 web.py
```

By default it listens on `http://localhost:5000`.

2. In another terminal, start the React frontend:

```bash
cd frontend
npm install
npm run dev
```

3. Open the printed Vite URL (typically `http://localhost:5173`) in your browser, upload an audio file, optionally set a language code (like `en`), and hit **Transcribe**. The app will call the Flask endpoint and display the transcript.



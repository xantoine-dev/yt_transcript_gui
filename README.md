# YouTube Transcript GUI

A minimal, macOS-optimized desktop application for retrieving and saving YouTube video transcripts.  
Built with Python, Tkinter, and the `youtube-transcript-api`.

---

## Overview

YouTube Transcript GUI provides a simple interface for fetching and exporting video subtitles without the command line.  
It’s lightweight, open source, and tailored for macOS Ventura.

---

## Features

- Retrieve transcripts by YouTube URL
- Save results as `.txt` or `.csv`
- Responsive Tkinter interface
- Native look and feel on macOS
- Works offline after first use

---

## Installation

### Requirements
- macOS Ventura (13.0+)  
- Python 3.10 or higher  
- `pip`

### Setup
```bash
git clone https://github.com/<your-username>/yt-transcript-gui.git
cd yt-transcript-gui
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 yt_transcript_gui.py
```

---

## Usage

1. Launch the app:
   ```bash
   python3 yt_transcript_gui.py
   ```
2. Paste a YouTube URL  
3. Click “Fetch Transcript”  
4. Save or copy your transcript  

---

## Development (VS Code)

Preconfigured `.vscode` settings and launch scripts are included for macOS.

- Run → “Run YouTube Transcript GUI”
- Auto-format on save via **Black**
- Works seamlessly in virtual environments

---

## Roadmap

- Dark mode detection  
- Markdown and PDF export options  
- Integration with OpenAI for summaries  

---

## License

MIT License © 2025 <X-man>

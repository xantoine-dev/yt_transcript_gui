import sys, subprocess, importlib, threading, re, os, json, time, queue
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# ---------------- Version & Dependency Checks ----------------
MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    sys.exit(f"Python {'.'.join(map(str, MIN_PYTHON))} or later required")

REQUIRED = ["yt-dlp==2025.10.14", "PySimpleGUIQt", "PySide6"]

def ensure_dependencies():
    for pkg in REQUIRED:
        try:
            importlib.import_module(pkg.replace('-', '_'))
        except ImportError:
            print(f"📦 Installing missing dependency: {pkg}")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg, "--quiet", "--upgrade"])
            print(f"✅ Installed {pkg}")

ensure_dependencies()

import PySimpleGUIQt as sg

# ---------------- Helper Functions ----------------
CONFIG_FILE = Path.home() / '.yt_transcript_gui.json'
TRANSCRIPTS_DIR = Path.cwd() / 'transcripts'

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f)

def load_config():
    if CONFIG_FILE.exists():
        return json.load(open(CONFIG_FILE))
    return {}

def ensure_transcripts_dir():
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    return TRANSCRIPTS_DIR

def sanitize_title(title):
    safe = re.sub(r'[^A-Za-z0-9_]+', '_', title.strip())
    return safe[:80]

# ---------------- THEME ----------------
sg.theme('DarkBlue17')
FONT_MONO = ('Menlo', 11)
FONT_HEADER = ('Helvetica', 14, 'bold')
FONT_LOG = ('Menlo', 11)

# ---------------- GUI Layout ----------------
layout = [
    [sg.Text('🎥 Enter YouTube / TED URLs (one per line):', font=FONT_HEADER)],
    [sg.Multiline(size=(70, 8), key='-URLS-', font=FONT_MONO,
                  background_color='#1E1E2E', text_color='#F8F8F2',
                  tooltip='Paste your video URLs here!')],
    [sg.HorizontalSeparator()],
    [
        sg.Column([[
            sg.Button('📂 Load File', size=(16,1), button_color=('white', '#0078D7')),
            sg.Button('⬇️ Download Transcripts', size=(22,1), button_color=('white', '#2ECC71')),
            sg.Button('⛔ Stop', size=(10,1), button_color=('white', '#E74C3C')),
            sg.Button('📁 Open Folder', size=(16,1), button_color=('white', '#9B59B6'))
        ]], pad=(0, 10))
    ],
    [sg.ProgressBar(100, orientation='h', size=(50, 20), key='-PROG-', bar_color=('#2ECC71', '#222'))],
    [sg.Text('🧾 Log Output:', font=('Helvetica', 12, 'bold'))],
    [sg.Multiline(size=(70, 15), key='-LOG-', autoscroll=True,
                  background_color='#111827', text_color='#00FF7F', font=FONT_LOG)]
]

window = sg.Window('✨ Transcript Wizard ✨', layout, icon=None, resizable=True, finalize=True)
stop_flag = [False]
progress_state = {'completed': 0}
event_queue = queue.Queue()
config = load_config()
if 'last_urls' in config:
    window['-URLS-'].update(config['last_urls'])

# ---------------- Worker Functions ----------------
def log(msg):
    event_queue.put(('log', msg))

def prog(value, total=None):
    event_queue.put(('prog', (value, total)))

def download_and_clean(url, progress_state, stop_flag):
    if stop_flag[0]:
        return
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            result = subprocess.run(
                ['yt-dlp', '--get-filename', '-o', '%(title)s', url],
                text=True, capture_output=True
            )
            if result.returncode != 0:
                if 'Video unavailable' in result.stderr:
                    log(f'❌ Video not available: {url}\n')
                    return
                else:
                    log(f'❌ Could not process video: {result.stderr}\n')
                    return
            title = result.stdout.strip()
            safe = sanitize_title(title)
            log(f'▶ Downloading subtitles for: {title}\n')

            proc = subprocess.Popen([
                'yt-dlp', '--skip-download', '--write-auto-sub', '--sub-format', 'vtt',
                '--output', f'{safe}.%(ext)s', url
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            while proc.poll() is None:
                if stop_flag[0]:
                    proc.terminate()
                    log('🛑 Terminated by user.\n')
                    return
                time.sleep(0.2)

            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                if ('Precondition check failed' in stderr or 'HTTP Error 400' in stderr) and attempt < max_retries:
                    log(f'⚠️ yt-dlp transient error (attempt {attempt}/{max_retries}). Retrying...\n')
                    time.sleep(2)
                    continue
                else:
                    log(f'❌ yt-dlp failed: {stderr}\n')
                    return

            vtt = next(Path.cwd().glob(f'{safe}*.vtt'), None)
            if not vtt:
                log(f'❌ No subtitles found for {title}\n')
                return

            cleaned = []
            with open(vtt, 'r', encoding='utf-8') as f:
                for line in f:
                    if stop_flag[0]:
                        log('🛑 Cleaning cancelled.\n')
                        return
                    line = line.strip()
                    if not line or re.match(r'^(WEBVTT|[0-9:.,->]+)$', line):
                        continue
                    line = re.sub(r'<[^>]+>', '', line)
                    cleaned.append(line)

            ensure_transcripts_dir()
            out_file = TRANSCRIPTS_DIR / f'{safe}.txt'
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(cleaned))

            vtt.unlink()
            log(f'✅ Saved: {out_file}\n')
            break
        except Exception as e:
            log(f'❌ Unexpected error: {e}\n')
            return

    progress_state['completed'] += 1
    prog(progress_state['completed'], None)

def process_urls(urls, stop_flag, progress_state):
    total = len(urls)
    progress_state['completed'] = 0
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(download_and_clean, u.strip(), progress_state, stop_flag)
                   for u in urls if u.strip()]
        while any(not f.done() for f in futures):
            if stop_flag[0]:
                break
            prog(progress_state['completed'], total)
            time.sleep(0.2)
    if not stop_flag[0]:
        prog(total, total)
        log('\n✨ All done!\n')

# ---------------- Event Loop ----------------
while True:
    event, values = window.read(timeout=200)

    # Handle queued thread events
    while not event_queue.empty():
        kind, data = event_queue.get()
        if kind == 'log':
            window['-LOG-'].update(data, append=True)
        elif kind == 'prog':
            completed, total = data
            if total is not None:
                window['-PROG-'].update_bar(completed, total)
            else:
                window['-PROG-'].update_bar(completed)

    if event in (sg.WIN_CLOSED, 'Exit'):
        stop_flag[0] = True
        save_config({'last_urls': values['-URLS-']})
        break

    elif event == '📂 Load File':
        file = sg.popup_get_file('Select URL list (.txt)', file_types=(('Text Files', '*.txt'),))
        if file:
            with open(file, 'r', encoding='utf-8') as f:
                window['-URLS-'].update(f.read())

    elif event == '📁 Open Folder':
        ensure_transcripts_dir()
        subprocess.run(['open', str(TRANSCRIPTS_DIR)])

    elif event == '⛔ Stop':
        stop_flag[0] = True
        window['-LOG-'].update('\n🛑 Cancelling current operation...\n', append=True)

    elif event == '⬇️ Download Transcripts':
        stop_flag[0] = False
        urls = values['-URLS-'].strip().splitlines()
        total = len(urls)
        window['-PROG-'].update_bar(0, total)
        save_config({'last_urls': values['-URLS-']})
        threading.Thread(target=process_urls, args=(urls, stop_flag, progress_state), daemon=True).start()

window.close()

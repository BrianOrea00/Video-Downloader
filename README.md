# 🎬 Video Downloader

A modular desktop video downloader built with Python, CustomTkinter, and `yt-dlp`. Features a clean sidebar UI with dark/light theme support, a download queue, and local media libraries.

---

## ✨ Features

### Queue Tab
- URL input with automatic clipboard detection (YouTube URLs auto-fill)
- Video preview (title & duration) before downloading
- Resolution selector (144p – 1080p) and audio-only (MP3) mode
- Parallel or sequential download modes with configurable concurrency limit
- Real-time progress bars with speed, ETA, and file size
- Per-item cancel, prioritize (move up/down), and remove controls
- Queue persisted to `queue.json` — survives app restarts
- Download history saved to `history.json`

### Video Library Tab
- Scans the download folder for video files (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.flv`, `.wmv`)
- Displays file name, size, and last-modified date
- Search/filter bar
- Play (opens in VLC or system default player) and delete controls
- Sidebar storage usage indicator

### Music Library Tab
- Scans the download folder for audio files (`.mp3`, `.flac`, `.m4a`, etc.)
- Reads metadata via `mutagen` (title, artist, album, duration)
- Search/filter bar
- Play and delete controls

### Settings Tab
- **Download:** parallel vs. sequential mode, max parallel downloads
- **Defaults:** default resolution, audio-only toggle, default download path
- **Cookies:** browser cookie extraction (Chrome, Firefox, Edge, Brave, Opera, Safari) or custom cookies file path — useful for age-restricted or members-only content
- **General:** auto clipboard detection toggle, clipboard polling interval
- **Appearance:** dark/light theme toggle (also available from the top bar)

### UI / General
- Sidebar navigation with active-tab indicator
- Top bar with live item count badge and theme toggle
- Dark and light themes with a teal (`#2BB2A9`) accent, fully consistent across all widgets
- VLC auto-detection; falls back to the system default player if VLC is not found
- Clipboard polling works on native Linux, WSL, and Windows (tries `powershell`, `xclip`, `xsel` in sequence)

---

## 📁 Project Structure

```
video_downloader/
├── main.py             # Entry point — sets appearance mode, applies theme, starts app
├── ui.py               # Main App class, sidebar, top bar, tab routing, theme toggle
├── queue_tab.py        # Download queue UI and download logic
├── videos_tab.py       # Video library browser
├── music_tab.py        # Music library browser
├── settings_tab.py     # Settings UI and persistence
├── downloader.py       # yt-dlp wrapper with progress hooks and cookie support
├── theme_manager.py    # Color palette definitions and CustomTkinter theme patching
├── icon_manager.py     # CTkImage loader for all app icons
├── config.py           # Constants, resolution list, default settings, theme color reference
├── utils.py            # JSON helpers (history, queue, settings), VLC detection
├── history.json        # Download history (auto-created)
├── queue.json          # Persisted queue (auto-created)
├── settings.json       # User settings (auto-created)
├── assets/             # PNG icons (Tabler icon set)
└── requirements.txt
```

---

## ⚙️ Requirements

- Python 3.10+
- FFmpeg (required for audio extraction and video merging)
- Git

---

## 🔧 Installation

### 1. Install system dependencies

**Debian / Ubuntu / WSL:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk python3-venv ffmpeg git -y
```

**Arch:**
```bash
sudo pacman -S python python-pip tk ffmpeg git
```

**macOS (Homebrew):**
```bash
brew install python ffmpeg
```

---

### 2. Clone the repository

```bash
git clone git@github.com:BrianOrea00/Video-Downloader.git
cd Video-Downloader
```

---

### 3. Create and activate a virtual environment

```bash
python3 -m venv yt-env
source yt-env/bin/activate   # Windows: yt-env\Scripts\activate
```

---

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the App

```bash
python main.py
```

---

## 🍪 Cookie Support

Some videos (age-restricted, members-only, etc.) require authentication cookies.

Go to **Settings → Cookies** and choose one of:

| Method | How it works |
|--------|--------------|
| **None** | No cookies — works for most public videos |
| **Browser** | Extracts cookies directly from a logged-in browser profile (Chrome, Firefox, Edge, Brave, Opera, Safari) |
| **File** | Point to a `cookies.txt` file exported from your browser via a cookie-export extension |

---

## 🧠 How It Works

- `yt-dlp` handles all video/audio extraction and downloading
- Downloads run in background threads so the UI never freezes
- Progress is fed back to the UI via `yt-dlp` progress hooks
- The queue, history, and settings are stored as local JSON files
- CustomTkinter's theme is patched at runtime so all widgets use the project's own color palette

---

## ⚠️ Notes

- Not all websites are supported — depends on `yt-dlp`'s extractor list
- Some videos may be restricted (private, DRM-protected, etc.)
- On Linux, install `xclip` or `xsel` if clipboard auto-detection isn't working: `sudo apt install xclip`

---

## 📄 License

This project is for educational purposes.
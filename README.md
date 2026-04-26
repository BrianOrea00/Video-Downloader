# 🎬 Video Downloader (Python + Tkinter)

A simple modular video downloader built with Python, Tkinter, and `yt-dlp`.

This project allows you to download videos from supported websites with a clean GUI.

---

## 🚀 Features

* URL input box with clipboard auto-detect
* Select download folder (Browse button)
* Choose video resolution (144p to 1080p)
* Audio-only mode (MP3 download)
* Download progress bar (with percentage)
* Real-time download speed display
* ETA (Estimated Time Arrival) display
* Video info preview (title & duration)
* Cancel download (basic stop functionality)
* Download history (saved locally to JSON)

---

## 📁 Project Structure

```
video_downloader/
│
├── main.py
├── ui.py
├── downloader.py
├── utils.py
├── config.py
├── history.json
└── yt-env/
```

---

## ⚙️ Requirements

* Python 3.10+
* pip
* Tkinter
* FFmpeg
* Git

---

## 🔧 Installation (Debian / Linux)

### 1. Install system dependencies

```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk ffmpeg python3-venv git -y
```

---

### 2. Clone the repository

```bash
git clone git@github.com:BrianOrea00/Video-Downloader.git
cd Video-Downloader
```

---

### 3. Create virtual environment

```bash
python3 -m venv yt-env
```

---

### 4. Activate environment

```bash
source yt-env/bin/activate
```

---

### 5. Install Python dependencies

```bash
pip install -U yt-dlp
```

---

## ▶️ Run the Application

```bash
python main.py
```

---

## 🧠 How It Works

* Uses `yt-dlp` to extract and download video streams
* Tkinter provides the graphical interface
* Downloads run in a separate thread to avoid UI freezing
* Progress updates are handled via hooks
* History is saved in a JSON file

---

## ⚠️ Notes

* Not all websites are supported
* Some videos may be restricted (private, DRM, etc.)
* Cancel button stops the process after the current step

---

## 📌 Future Improvements

* Queue system (multiple downloads)
* Real cancel (force stop process)
* Thumbnail preview
* Drag & drop URL
* History viewer window (view past downloads)

---

## 📄 License

This project is for educational purposes.

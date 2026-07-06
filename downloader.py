# downloader.py
import yt_dlp
import threading
import os
import json
import logging
from config import QUEUE_FILE

# Setup logger
logger = logging.getLogger(__name__)


class Downloader:
    def __init__(self):
        self.process = None
        # Thread-safe cancelled flag
        self._cancel_lock = threading.Lock()
        self._cancelled = False
        self._partial_file = None

    @property
    def cancelled(self):
        with self._cancel_lock:
            return self._cancelled

    @cancelled.setter
    def cancelled(self, value):
        with self._cancel_lock:
            self._cancelled = value

    def get_info(self, url, cookie_settings=None):
        """Get video info with optional cookie support"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'no_color': True,
        }

        if cookie_settings:
            self._add_cookie_options(ydl_opts, cookie_settings)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _add_cookie_options(self, ydl_opts, cookie_settings):
        """Add cookie-related options to ydl_opts based on settings"""
        method = cookie_settings.get("cookie_method", "none")

        if method == "browser":
            browser = cookie_settings.get("cookie_browser", "chrome")
            browser_map = {
                "chrome": "chrome",
                "firefox": "firefox",
                "edge": "edge",
                "brave": "brave",
                "opera": "opera",
                "safari": "safari"
            }
            browser_name = browser_map.get(browser, "chrome")
            ydl_opts['cookiesfrombrowser'] = (browser_name,)

        elif method == "file":
            cookie_file = cookie_settings.get("cookie_file_path", "")
            if cookie_file and cookie_file.strip():
                ydl_opts['cookiefile'] = cookie_file.strip()

    def _find_partial_file(self, path, url):
        """Check if there's a partial download for this URL."""
        try:
            # Check queue.json for partial file info
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE, 'r') as f:
                    queue = json.load(f)
                for item in queue:
                    if item.get('url') == url and item.get('partial_file'):
                        partial_path = item.get('partial_file')
                        if os.path.exists(partial_path):
                            logger.info(f"Found partial file: {partial_path}")
                            return partial_path
            # Also check for .part files in the path
            if os.path.exists(path):
                for f in os.listdir(path):
                    if f.endswith('.part') or f.endswith('.ytdl'):
                        full_path = os.path.join(path, f)
                        # Check if this partial belongs to this URL
                        # We'll use it if we can't find a better match
                        if not self._partial_file:
                            self._partial_file = full_path
                            logger.info(f"Found orphan partial file: {full_path}")
            return None
        except Exception as e:
            logger.error(f"Error finding partial file: {e}")
            return None

    def _save_partial_tracking(self, url, partial_file):
        """Save partial file info for resume later."""
        try:
            if not os.path.exists(QUEUE_FILE):
                return
            with open(QUEUE_FILE, 'r') as f:
                queue = json.load(f)
            for item in queue:
                if item.get('url') == url:
                    item['partial_file'] = partial_file
                    item['status'] = 'paused'
                    break
            with open(QUEUE_FILE, 'w') as f:
                json.dump(queue, f, indent=4)
            logger.info(f"Saved partial tracking for {url}: {partial_file}")
        except Exception as e:
            logger.error(f"Failed to save partial tracking: {e}")

    def _clear_partial_tracking(self, url):
        """Clear partial file tracking on successful download."""
        try:
            if not os.path.exists(QUEUE_FILE):
                return
            with open(QUEUE_FILE, 'r') as f:
                queue = json.load(f)
            for item in queue:
                if item.get('url') == url:
                    item.pop('partial_file', None)
                    break
            with open(QUEUE_FILE, 'w') as f:
                json.dump(queue, f, indent=4)
            logger.info(f"Cleared partial tracking for {url}")
        except Exception as e:
            logger.error(f"Failed to clear partial tracking: {e}")

    def download(self, url, path, resolution, progress_callback, done_callback,
                 audio_only=False, cookie_settings=None):
        def run():
            self.cancelled = False
            self._partial_file = None

            # Check for existing partial download
            partial_file = self._find_partial_file(path, url)
            if partial_file:
                logger.info(f"Resuming download from: {partial_file}")

            def hook(d):
                if self.cancelled:
                    raise Exception("Download cancelled by user")

                # Track partial file for resume
                if d['status'] == 'downloading' and 'filename' in d:
                    self._partial_file = d['filename']

                if d['status'] == 'downloading':
                    progress_data = d.copy()

                    # Calculate percentage
                    if 'total_bytes' in d and d['total_bytes'] > 0:
                        percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                        progress_data['_percent'] = percent
                        progress_data['_percent_str'] = f"{percent:.1f}%"
                    elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                        percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                        progress_data['_percent'] = percent
                        progress_data['_percent_str'] = f"{percent:.1f}%"

                    # Speed
                    if 'speed' in d and d['speed']:
                        speed = d['speed']
                        if speed > 1024 * 1024:
                            speed_str = f"{speed / 1024 / 1024:.1f} MiB/s"
                        elif speed > 1024:
                            speed_str = f"{speed / 1024:.1f} KiB/s"
                        else:
                            speed_str = f"{speed:.1f} B/s"
                        progress_data['_speed_str'] = speed_str

                    # ETA
                    if 'eta' in d and d['eta']:
                        eta = d['eta']
                        if eta > 3600:
                            eta_str = f"{eta // 3600}h {(eta % 3600) // 60}m"
                        elif eta > 60:
                            eta_str = f"{eta // 60}m {eta % 60}s"
                        else:
                            eta_str = f"{eta}s"
                        progress_data['_eta_str'] = eta_str

                    # Downloaded bytes
                    if 'downloaded_bytes' in d:
                        downloaded = d['downloaded_bytes']
                        if downloaded > 1024 * 1024:
                            downloaded_str = f"{downloaded / 1024 / 1024:.1f} MB"
                        elif downloaded > 1024:
                            downloaded_str = f"{downloaded / 1024:.1f} KB"
                        else:
                            downloaded_str = f"{downloaded} B"
                        progress_data['_downloaded_bytes_str'] = downloaded_str

                    # Total bytes
                    if 'total_bytes' in d:
                        total = d['total_bytes']
                        if total > 1024 * 1024:
                            total_str = f"{total / 1024 / 1024:.1f} MB"
                        elif total > 1024:
                            total_str = f"{total / 1024:.1f} KB"
                        else:
                            total_str = f"{total} B"
                        progress_data['_total_bytes_str'] = total_str

                    progress_callback(progress_data)

                elif d['status'] == 'finished':
                    progress_callback({'status': 'finished'})

            ydl_opts = {
                'outtmpl': f'{path}/%(title)s.%(ext)s',
                'progress_hooks': [hook],
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'no_color': True,
                'continuedl': True,  # ← ENABLE RESUME
            }

            if cookie_settings:
                self._add_cookie_options(ydl_opts, cookie_settings)

            if audio_only:
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'extractaudio': True,
                })
            else:
                ydl_opts.update({
                    'format': f'bestvideo[ext=mp4][height<={resolution}]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'merge_output_format': 'mp4',
                })

            try:
                logger.info(f"Starting download: {url}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                if not self.cancelled:
                    # Clear partial tracking on success
                    self._clear_partial_tracking(url)
                    logger.info(f"Download completed: {url}")
                    done_callback("Download completed successfully!")
            except Exception as e:
                if not self.cancelled:
                    # Save partial file info for resume
                    if self._partial_file:
                        self._save_partial_tracking(url, self._partial_file)
                    logger.error(f"Download failed: {url} - {str(e)}")
                    done_callback(f"Error: {str(e)}")
                else:
                    logger.info(f"Download cancelled: {url}")
                    done_callback("Download cancelled by user")

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def cancel(self):
        with self._cancel_lock:
            self._cancelled = True
        logger.info("Download cancelled by user")

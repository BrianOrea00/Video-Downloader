# downloader.py
import yt_dlp
import threading
import logging
import time

logger = logging.getLogger(__name__)


class Downloader:
    def __init__(self):
        self.process = None
        self._cancel_lock = threading.Lock()
        self._cancelled = False
        self._thread = None   # store thread for join

    @property
    def cancelled(self):
        with self._cancel_lock:
            return self._cancelled

    @cancelled.setter
    def cancelled(self, value):
        with self._cancel_lock:
            self._cancelled = value

    def wait(self):
        """Wait for the download thread to finish."""
        if self._thread and self._thread.is_alive():
            self._thread.join()

    def get_info(self, url, cookie_settings=None):
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

    def download(self, url, path, resolution, progress_callback, done_callback,
                 audio_only=False, cookie_settings=None, max_retries=3, backoff_factor=2,
                 stop_event=None, info_callback=None):
        def stopped():
            return stop_event is not None and stop_event.is_set()

        def run():
            if stopped():
                logger.info(f"Download aborted before start (stop requested): {url}")
                done_callback("Download stopped")
                return

            self.cancelled = False

            attempt = 0
            last_exception = None

            while attempt < max_retries and not self.cancelled and not stopped():
                attempt += 1
                logger.info(f"Download attempt {attempt}/{max_retries} for {url}")
                progress_callback({
                    'status': 'retrying',
                    'attempt': attempt,
                    'max_retries': max_retries,
                    'message': f"Attempt {attempt}/{max_retries}"
                })

                def hook(d):
                    if self.cancelled or stopped():
                        raise Exception("Download stopped")
                    if d['status'] == 'downloading':
                        progress_data = d.copy()
                        if 'total_bytes' in d and d['total_bytes'] > 0:
                            percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                            progress_data['_percent'] = percent
                            progress_data['_percent_str'] = f"{percent:.1f}%"
                        elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                            percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                            progress_data['_percent'] = percent
                            progress_data['_percent_str'] = f"{percent:.1f}%"
                        if 'speed' in d and d['speed']:
                            speed = d['speed']
                            if speed > 1024 * 1024:
                                speed_str = f"{speed / 1024 / 1024:.1f} MiB/s"
                            elif speed > 1024:
                                speed_str = f"{speed / 1024:.1f} KiB/s"
                            else:
                                speed_str = f"{speed:.1f} B/s"
                            progress_data['_speed_str'] = speed_str
                        if 'eta' in d and d['eta']:
                            eta = d['eta']
                            if eta > 3600:
                                eta_str = f"{eta // 3600}h {(eta % 3600) // 60}m"
                            elif eta > 60:
                                eta_str = f"{eta // 60}m {eta % 60}s"
                            else:
                                eta_str = f"{eta}s"
                            progress_data['_eta_str'] = eta_str
                        if 'downloaded_bytes' in d:
                            downloaded = d['downloaded_bytes']
                            if downloaded > 1024 * 1024:
                                downloaded_str = f"{downloaded / 1024 / 1024:.1f} MB"
                            elif downloaded > 1024:
                                downloaded_str = f"{downloaded / 1024:.1f} KB"
                            else:
                                downloaded_str = f"{downloaded} B"
                            progress_data['_downloaded_bytes_str'] = downloaded_str
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
                    'continuedl': True,
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
                        info = ydl.extract_info(url, download=True)
                    if self.cancelled or stopped():
                        logger.info(f"Download stopped: {url}")
                        done_callback("Download stopped")
                        return
                    if info_callback and info:
                        try:
                            info_callback(info)
                        except Exception as cb_err:
                            logger.error(f"info_callback failed: {cb_err}")
                    logger.info(f"Download completed: {url}")
                    done_callback("Download completed successfully!")
                    return
                except Exception as e:
                    last_exception = e
                    if self.cancelled or stopped():
                        logger.info(f"Download stopped: {url}")
                        done_callback("Download stopped")
                        return
                    error_msg = str(e).lower()
                    is_retryable = any(keyword in error_msg for keyword in [
                        'timeout', 'connection', 'network', '5xx', 'http error 500',
                        'http error 502', 'http error 503', 'http error 504',
                        'unreachable', 'reset', 'eof', 'read timed out'
                    ])
                    if not is_retryable or attempt >= max_retries:
                        break
                    wait_time = backoff_factor ** (attempt - 1)
                    logger.warning(f"Download failed (attempt {attempt}), retrying in {wait_time}s: {e}")
                    progress_callback({
                        'status': 'retrying',
                        'attempt': attempt,
                        'max_retries': max_retries,
                        'wait_time': wait_time,
                        'message': f"Retrying in {wait_time}s..."
                    })
                    time.sleep(wait_time)

            if not self.cancelled and not stopped():
                error_msg = str(last_exception) if last_exception else "Unknown error"
                logger.error(f"Download failed after {attempt} attempts: {url} - {error_msg}")
                done_callback(f"Error: {error_msg}")

        thread = threading.Thread(target=run, daemon=True)
        self._thread = thread
        thread.start()

    def cancel(self):
        with self._cancel_lock:
            self._cancelled = True
        logger.info("Download cancelled by user")

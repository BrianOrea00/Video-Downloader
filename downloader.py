import yt_dlp
import subprocess
import threading

class Downloader:
    def __init__(self):
        self.process = None
        self.cancelled = False

    def get_info(self, url):
        with yt_dlp.YoutubeDL() as ydl:
            return ydl.extract_info(url, download = False)

    def download(self, url, path, resolution, progress_callback, done_callback):
        def run():
            self.cancelled = False

            def hook(d):
                if d['status'] == 'downloading':
                    progress_callback(d)
                if self.cancelled:
                    raise Exception("Cancelled")

            ydl_opts = {
                    'outtmpl': f'{path}/%(title)s.%(ext)s',
                    'format': f'bestvideo[height<={resolution}]+bestaudio/best',
                    'progress_hook': [hook]
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                done_callback("Finished!")
            except Exception as e:
                done_callback(str(e))

        threading.Thread(target=run).start()

    def cancel(self):
        self.cancelled = True

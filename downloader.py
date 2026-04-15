import yt_dlp
import threading
import re

class Downloader:
    def __init__(self):
        self.process = None
        self.cancelled = False

    def get_info(self, url):
        with yt_dlp.YoutubeDL() as ydl:
            return ydl.extract_info(url, download=False)

    def download(self, url, path, resolution, progress_callback, done_callback, audio_only=False):
        def run():
            self.cancelled = False

            def hook(d):
                if self.cancelled:
                    raise Exception("Download cancelled by user")
                    
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
                        if speed > 1024*1024:
                            speed_str = f"{speed/1024/1024:.1f} MiB/s"
                        elif speed > 1024:
                            speed_str = f"{speed/1024:.1f} KiB/s"
                        else:
                            speed_str = f"{speed:.1f} B/s"
                        progress_data['_speed_str'] = speed_str
                    
                    
                    if 'eta' in d and d['eta']:
                        eta = d['eta']
                        if eta > 3600:
                            eta_str = f"{eta//3600}h {(eta%3600)//60}m"
                        elif eta > 60:
                            eta_str = f"{eta//60}m {eta%60}s"
                        else:
                            eta_str = f"{eta}s"
                        progress_data['_eta_str'] = eta_str
                    
                    
                    if 'downloaded_bytes' in d:
                        downloaded = d['downloaded_bytes']
                        if downloaded > 1024*1024:
                            downloaded_str = f"{downloaded/1024/1024:.1f} MB"
                        elif downloaded > 1024:
                            downloaded_str = f"{downloaded/1024:.1f} KB"
                        else:
                            downloaded_str = f"{downloaded} B"
                        progress_data['_downloaded_bytes_str'] = downloaded_str
                    
                    if 'total_bytes' in d:
                        total = d['total_bytes']
                        if total > 1024*1024:
                            total_str = f"{total/1024/1024:.1f} MB"
                        elif total > 1024:
                            total_str = f"{total/1024:.1f} KB"
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
            }

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
                    'format': f'bestvideo[height<={resolution}]+bestaudio/best',
                    'merge_output_format': 'mp4',
                })

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                if not self.cancelled:
                    done_callback("Download completed successfully!")
            except Exception as e:
                if not self.cancelled:
                    done_callback(f"Error: {str(e)}")

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def cancel(self):
        self.cancelled = True

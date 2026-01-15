from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import yt_dlp
import os
import shutil
import tempfile

class handler(BaseHTTPRequestHandler):
    def set_cors_headers(self):
        """Set CORS headers to allow requests from any origin"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(200)
        self.set_cors_headers()
        self.end_headers()

    def setup_cookies(self):
        """
        Copies cookies.txt from read-only app storage to writable /tmp storage.
        This is required for the latest yt-dlp to handle session updates.
        """
        # The path where your file is uploaded (usually root)
        src = os.path.join(os.getcwd(), 'cookies.txt')
        # The only writable path in serverless environments
        dst = os.path.join(tempfile.gettempdir(), 'cookies_writable.txt')
        
        if os.path.exists(src):
            try:
                shutil.copy2(src, dst)
                return dst
            except Exception:
                return src # Fallback to original if copy fails
        return None

    def get_audio_url(self, video_id, cookie_path):
        """Get direct audio download URL for a video"""
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'extract_flat': False,
                'skip_download': True,
                'nocheckcertificate': True,
                'geo_bypass': True,
                'cookiefile': cookie_path,
                'cachedir': False,  # Prevents yt-dlp from creating a cache folder
                'extractor_args': {
                    'youtube': {
                        # Using these specific clients helps bypass bot detection
                        'player_client': ['ios', 'android_music'],
                        'player_skip': ['webpage', 'configs'],
                    }
                },
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Iterate through formats to find the best audio-only stream
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            if fmt.get('url'):
                                return fmt.get('url')
                
                return info.get('url')
        except Exception:
            return None
    
    def do_GET(self):
        """Handle GET requests for searching music with download URLs"""
        try:
            # Step 1: Initialize writable cookie path
            writable_cookie_path = self.setup_cookies()
            
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            query = params.get('q', [''])[0]
            max_results = int(params.get('max', ['10'])[0])
            
            if not query:
                self.send_response(400)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': 'Query parameter "q" is required'}).encode())
                return
            
            # Step 2: Search Configuration
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False, # Must be False to get thumbnails
                'default_search': 'ytsearch',
                'cookiefile': writable_cookie_path,
                'cachedir': False,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                        'player_skip': ['webpage'],
                    }
                },
            }
            
            results = []
            search_query = f"ytsearch{max_results}:{query}"
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            video_id = entry.get('id')
                            # Fetch direct audio URL for each result
                            download_url = self.get_audio_url(video_id, writable_cookie_path)
                            
                            results.append({
                                'id': video_id,
                                'title': entry.get('title'),
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'duration': entry.get('duration'),
                                'thumbnail': entry.get('thumbnail'),
                                'channel': entry.get('uploader') or entry.get('channel'),
                                'view_count': entry.get('view_count'),
                                'download_url': download_url if download_url else 'Not available'
                            })
            
            # Step 3: Send Final Response
            self.send_response(200)
            self.set_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'success': True,
                'query': query,
                'count': len(results),
                'results': results
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            self.send_response(500)
            self.set_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import yt_dlp
import os
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

    def get_cookie_path(self):
        """
        Locates the cookies.txt file. 
        If in a read-only environment, ensure the path is accessible.
        """
        # Looks for cookies.txt in the current script directory
        return os.path.join(os.getcwd(), 'cookies.txt')

    def get_audio_url(self, video_id):
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
                'cookiefile': self.get_cookie_path(),
                # Specify a writable cache directory to avoid Errno 30
                'cachedir': os.path.join(tempfile.gettempdir(), 'yt-dlp-cache'),
                'extractor_args': {
                    'youtube': {
                        'player_client': ['ios', 'android_music'],
                        'player_skip': ['webpage', 'configs'],
                    }
                },
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            if fmt.get('url'):
                                return fmt.get('url')
                
                return info.get('url')
        except:
            return None
    
    def do_GET(self):
        """Handle GET requests for searching music with download URLs"""
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            query = params.get('q', [''])[0]
            max_results = int(params.get('max', ['10'])[0])
            
            if not query:
                self.send_response(400)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Missing query parameter "q".'
                }).encode())
                return
            
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'default_search': 'ytsearch',
                'cookiefile': self.get_cookie_path(),
                'cachedir': os.path.join(tempfile.gettempdir(), 'yt-dlp-cache-search'),
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
                            download_url = self.get_audio_url(video_id)
                            
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
            
            self.send_response(200)
            self.set_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            self.wfile.write(json.dumps({
                'success': True,
                'query': query,
                'count': len(results),
                'results': results
            }, indent=2).encode())
            
        except Exception as e:
            self.send_response(500)
            self.set_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())

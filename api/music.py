from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import yt_dlp

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
                # Use standard clients to ensure URL extraction
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'ios'],
                    }
                },
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Try to find the best audio-only format
                formats = info.get('formats', [])
                for fmt in formats:
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                        if fmt.get('url'):
                            return fmt.get('url')
                
                # Fallback to the main info URL if specific audio format fails
                return info.get('url')
                
        except Exception:
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
                    'error': 'Missing query parameter "q". Usage: /api/music?q=song name&max=10'
                }).encode())
                return
            
            # Changed extract_flat to False to ensure thumbnails are captured
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False, 
                'default_search': 'ytsearch',
                'max_downloads': max_results,
            }
            
            results = []
            search_query = f"ytsearch{max_results}:{query}"
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            video_id = entry.get('id')
                            
                            # Get direct audio URL
                            download_url = self.get_audio_url(video_id)
                            
                            # thumbnail is now available because extract_flat is False
                            result = {
                                'id': video_id,
                                'title': entry.get('title'),
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'duration': entry.get('duration'),
                                'thumbnail': entry.get('thumbnail'),
                                'channel': entry.get('uploader') or entry.get('channel'),
                                'view_count': entry.get('view_count'),
                                'download_url': download_url if download_url else 'Not available'
                            }
                            
                            results.append(result)
            
            # Send response
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
            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e)
            }).encode())

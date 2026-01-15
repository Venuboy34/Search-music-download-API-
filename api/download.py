from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import yt_dlp

class handler(BaseHTTPRequestHandler):
    def set_cors_headers(self):
        """Set CORS headers to allow requests from any origin"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(200)
        self.set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests for getting download URLs"""
        try:
            # Parse query parameters
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            video_url = params.get('url', [''])[0]
            video_id = params.get('id', [''])[0]
            quality = params.get('quality', ['audio'])[0] 
            
            if not video_url and not video_id:
                self.send_response(400)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Missing parameter "url" or "id"'}).encode())
                return
            
            # Construct full URL if only ID is provided
            if video_id and not video_url:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # BYPASS BOT DETECTION CONFIG
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best' if quality == 'audio' else 'bestvideo+bestaudio/best',
                'extract_flat': False,
                'nocheckcertificate': True,
                'extractor_args': {
                    'youtube': {
                        # 'ios' is the most reliable client to bypass bot checks currently
                        'player_client': ['ios'], 
                    }
                },
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Filter formats to keep response size small
                formats = []
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('url'):
                            formats.append({
                                'format_id': fmt.get('format_id'),
                                'ext': fmt.get('ext'),
                                'resolution': fmt.get('resolution'),
                                'filesize': fmt.get('filesize'),
                                'url': fmt.get('url'),
                                'vcodec': fmt.get('vcodec'),
                                'acodec': fmt.get('acodec'),
                            })
                
                response = {
                    'success': True,
                    'video_info': {
                        'id': info.get('id'),
                        'title': info.get('title'),
                        'duration': info.get('duration'),
                        'thumbnail': info.get('thumbnail'),
                        'uploader': info.get('uploader'),
                    },
                    'download_url': info.get('url'), 
                    'formats': formats[:15] # Return top 15 formats
                }
                
                self.send_response(200)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response, indent=2).encode())
                
        except Exception as e:
            self.send_response(500)
            self.set_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': str(e),
                'success': False
            }).encode())

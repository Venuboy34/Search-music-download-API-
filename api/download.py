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
            quality = params.get('quality', ['audio'])[0]  # 'audio' or 'video'
            
            if not video_url and not video_id:
                self.send_response(400)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Missing parameter "url" or "id"'
                }).encode())
                return
            
            # Construct full URL if only ID is provided
            if video_id and not video_url:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Configure yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best' if quality == 'audio' else 'best',
                'extract_flat': False,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                        'player_skip': ['webpage', 'configs'],
                    }
                },
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Get available formats
                formats = []
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('url'):
                            format_info = {
                                'format_id': fmt.get('format_id'),
                                'ext': fmt.get('ext'),
                                'quality': fmt.get('quality'),
                                'filesize': fmt.get('filesize'),
                                'url': fmt.get('url'),
                                'acodec': fmt.get('acodec'),
                                'vcodec': fmt.get('vcodec'),
                                'abr': fmt.get('abr'),
                                'vbr': fmt.get('vbr'),
                                'format_note': fmt.get('format_note'),
                            }
                            formats.append(format_info)
                
                # Get best format URL
                best_url = info.get('url')
                
                # Build response
                response = {
                    'success': True,
                    'video_info': {
                        'id': info.get('id'),
                        'title': info.get('title'),
                        'duration': info.get('duration'),
                        'thumbnail': info.get('thumbnail'),
                        'description': info.get('description'),
                        'uploader': info.get('uploader'),
                        'view_count': info.get('view_count'),
                        'like_count': info.get('like_count'),
                    },
                    'download_url': best_url,
                    'formats': formats[:10]  # Limit to first 10 formats
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

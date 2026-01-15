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
        """Handle GET requests for searching YouTube music"""
        try:
            # Parse query parameters
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
                    'error': 'Missing query parameter "q"'
                }).encode())
                return
            
            # Configure yt-dlp options for search
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'force_generic_extractor': False,
                'default_search': 'ytsearch',
            }
            
            results = []
            search_query = f"ytsearch{max_results}:{query}"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            results.append({
                                'id': entry.get('id'),
                                'title': entry.get('title'),
                                'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
                                'duration': entry.get('duration'),
                                'thumbnail': entry.get('thumbnail'),
                                'channel': entry.get('uploader') or entry.get('channel'),
                                'view_count': entry.get('view_count'),
                            })
            
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
                'error': str(e),
                'success': False
            }).encode())

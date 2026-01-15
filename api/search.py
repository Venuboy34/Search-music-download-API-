from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import yt_dlp

class handler(BaseHTTPRequestHandler):
    def set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Fast search without download URLs"""
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            query = params.get('q', [''])[0]
            max_results = min(int(params.get('max', ['10'])[0]), 20)
            
            if not query:
                self.send_response(400)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Missing "q" parameter'
                }).encode())
                return
            
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': 'ytsearch',
            }
            
            results = []
            search_query = f"ytsearch{max_results}:{query}"
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            video_id = entry.get('id')
                            result = {
                                'id': video_id,
                                'title': entry.get('title'),
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'duration': entry.get('duration'),
                                'thumbnail': entry.get('thumbnail') or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                                'channel': entry.get('uploader') or entry.get('channel'),
                                'view_count': entry.get('view_count'),
                                'download_api': f"/api/download?id={video_id}"
                            }
                            results.append(result)
            
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

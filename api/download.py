from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, quote
import json
import urllib.request

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
        """Get download URL using RapidAPI"""
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            video_id = params.get('id', [''])[0]
            audio_quality = params.get('quality', ['128'])[0]  # 128, 192, 256, 320
            
            if not video_id:
                self.send_response(400)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Missing "id" parameter. Usage: /api/download?id=VIDEO_ID'
                }).encode())
                return
            
            # Construct YouTube URL
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            encoded_url = quote(youtube_url, safe='')
            
            # RapidAPI request
            api_url = f"https://youtube-info-download-api.p.rapidapi.com/ajax/download.php?format=mp3&add_info=0&url={encoded_url}&audio_quality={audio_quality}&allow_extended_duration=false&no_merge=false&audio_language=en"
            
            request = urllib.request.Request(api_url)
            request.add_header('x-rapidapi-host', 'youtube-info-download-api.p.rapidapi.com')
            request.add_header('x-rapidapi-key', 'e239f85679msh1175aa87c891e18p1557f0jsnb52f646bd75c')
            
            # Make API request
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode())
            
            # Extract download links
            if data.get('status') == 'ok' or data.get('download'):
                download_links = data.get('download', {})
                
                # Get MP3 download links
                mp3_links = []
                for quality, link_data in download_links.items():
                    if isinstance(link_data, dict):
                        mp3_links.append({
                            'quality': quality,
                            'url': link_data.get('url'),
                            'size': link_data.get('size'),
                            'format': link_data.get('ext', 'mp3')
                        })
                
                # Get best quality link
                best_link = None
                if mp3_links:
                    best_link = mp3_links[0]['url']
                elif download_links and isinstance(download_links, dict):
                    # Try to get any available link
                    for key, value in download_links.items():
                        if isinstance(value, dict) and value.get('url'):
                            best_link = value.get('url')
                            break
                
                self.send_response(200)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response_data = {
                    'success': True,
                    'video_id': video_id,
                    'title': data.get('title'),
                    'thumbnail': data.get('thumbnail'),
                    'duration': data.get('duration'),
                    'download_url': best_link,
                    'available_formats': mp3_links,
                    'info': data.get('info', {})
                }
                
                self.wfile.write(json.dumps(response_data, indent=2).encode())
            else:
                self.send_response(500)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Failed to get download URL from API',
                    'video_id': video_id,
                    'api_response': data
                }).encode())
                
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.set_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': f'API Error: {e.code} - {e.reason}',
                'video_id': video_id if 'video_id' in locals() else None
            }).encode())
            
        except Exception as e:
            self.send_response(500)
            self.set_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e),
                'video_id': video_id if 'video_id' in locals() else None
            }).encode())

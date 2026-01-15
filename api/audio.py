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
        """Handle GET requests for getting audio download URLs"""
        try:
            # Parse query parameters
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            video_url = params.get('url', [''])[0]
            video_id = params.get('id', [''])[0]
            
            if not video_url and not video_id:
                self.send_response(400)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Missing parameter "url" or "id"'
                }).encode())
                return
            
            # Construct full URL if only ID is provided
            if video_id and not video_url:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Configure yt-dlp options with aggressive bot bypass
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'extract_flat': False,
                'skip_download': True,
                'nocheckcertificate': True,
                'geo_bypass': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['ios', 'android_creator', 'android_music', 'android_embedded'],
                        'player_skip': ['webpage', 'configs', 'js'],
                        'skip': ['hls', 'dash', 'translated_subs'],
                    }
                },
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Extract only audio formats
                audio_formats = []
                
                if 'formats' in info:
                    for fmt in info['formats']:
                        # Only audio formats (no video)
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            if fmt.get('url'):
                                audio_formats.append({
                                    'format_id': fmt.get('format_id'),
                                    'url': fmt.get('url'),
                                    'ext': fmt.get('ext'),
                                    'quality': fmt.get('format_note', 'unknown'),
                                    'bitrate': fmt.get('abr'),
                                    'filesize': fmt.get('filesize'),
                                    'filesize_mb': round(fmt.get('filesize', 0) / (1024*1024), 2) if fmt.get('filesize') else None,
                                })
                
                # Get best audio format
                best_audio_url = None
                best_format = None
                
                if audio_formats:
                    # Sort by bitrate (highest first)
                    audio_formats.sort(key=lambda x: x.get('bitrate') or 0, reverse=True)
                    best_format = audio_formats[0]
                    best_audio_url = best_format['url']
                elif info.get('url'):
                    best_audio_url = info.get('url')
                    best_format = {
                        'url': best_audio_url,
                        'ext': info.get('ext', 'unknown'),
                        'quality': 'best available',
                    }
                
                # Build response
                response = {
                    'success': True,
                    'video_id': info.get('id'),
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'duration_string': info.get('duration_string'),
                    'artist': info.get('artist') or info.get('uploader'),
                    'thumbnail': info.get('thumbnail'),
                    'view_count': info.get('view_count'),
                    'download_url': best_audio_url,
                    'best_format': best_format,
                    'available_formats': audio_formats[:5],  # Top 5 formats
                }
                
                self.send_response(200)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response, indent=2).encode())
                
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a bot detection error
            if 'Sign in to confirm' in error_msg or 'bot' in error_msg.lower():
                self.send_response(403)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Bot detection triggered',
                    'message': 'YouTube detected automated access. Try again later or use a different video.',
                    'video_id': video_id or video_url,
                    'suggestions': [
                        'Wait 5-10 minutes and try again',
                        'Try a different video',
                        'Use videos from search results'
                    ]
                }).encode())
            else:
                self.send_response(500)
                self.set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': error_msg,
                    'video_id': video_id or video_url
                }).encode())

from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Remedy Search - Traditional & Herbal Remedies</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; margin: 0; background: #f8f9fa; }
        .wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .box { width: min(800px, 92vw); text-align: center; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #2d3748; margin-bottom: 10px; }
        .subtitle { color: #718096; margin-bottom: 30px; }
        .status { margin: 20px 0; padding: 20px; border-radius: 8px; background: #e6fffa; color: #2c7a7b; border: 1px solid #81e6d9; }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="box">
            <h1>🌿 Remedy Search</h1>
            <p class="subtitle">Traditional & Herbal Remedies from Ancient Wisdom</p>
            
            <div class="status">
                <strong>✅ App is now working!</strong><br>
                The deployment was successful. We're building the full functionality next.
            </div>
            
            <div style="margin-top: 30px; font-size: 14px; color: #718096;">
                <strong>Features to be added:</strong><br>
                • Upload EPUB files with traditional remedy books<br>
                • Search for remedies by symptoms<br>
                • Extract structured ingredients and instructions<br>
                • Amazon affiliate links for ingredients
            </div>
        </div>
    </div>
</body>
</html>
            """
            
            self.wfile.write(html.encode())
            
        elif self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {"status": "healthy", "message": "Basic API working"}
            self.wfile.write(json.dumps(response).encode())
            
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {"detail": "Not Found"}
            self.wfile.write(json.dumps(response).encode())
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    """Serve the main HTML page"""
    return """
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
                <strong>✅ App is working!</strong><br>
                The full functionality is being deployed. Please check back in a few minutes for the complete remedy search interface.
            </div>
            
            <div style="margin-top: 30px; font-size: 14px; color: #718096;">
                <strong>Coming soon:</strong><br>
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

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "message": "Basic API working"}
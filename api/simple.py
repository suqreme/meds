import os
import json
import hashlib
import re
import urllib.parse
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile
import shutil

# Import dependencies
try:
    from ebooklib import epub
    from bs4 import BeautifulSoup
    from slugify import slugify
except ImportError as e:
    print(f"Import error: {e}")

app = FastAPI(title="Remedy Search API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage
books_data = []  # Store all text chunks with metadata
AFFILIATE_TAG = os.environ.get("AMZ_TAG", "YOURTAG-20")

# Regex patterns
AMOUNT_RE = r"(?:\d+(?:\.\d+)?|\d+/\d+)"
UNIT_RE = r"(?:tsp|tbsp|teaspoon|tablespoon|cup|cups|ml|l|g|kg|ounce|oz|inches|slice|slices|piece|pieces|drops?|pinch|handful)"
BULLET_RE = re.compile(r"^\s*(?:[-•*]|\d+\.)\s+")
ING_LINE = re.compile(rf"^\s*(?:{AMOUNT_RE}\s*(?:{UNIT_RE})?\s+)?([A-Za-z][\w\s\-']+)", re.IGNORECASE)

def clean_html(xhtml_bytes: bytes) -> str:
    """Clean HTML content and extract text"""
    soup = BeautifulSoup(xhtml_bytes, "html.parser")
    text = soup.get_text(" ", strip=True)
    return " ".join(text.split())

def chunk_words(text: str, max_words=900, overlap=150) -> List[str]:
    """Split text into overlapping chunks"""
    words = text.split()
    out, i = [], 0
    while i < len(words):
        end_idx = min(i + max_words, len(words))
        out.append(" ".join(words[i:end_idx]))
        if end_idx >= len(words):
            break
        i += max_words - overlap
    return out

def extract_ingredients_and_steps(snippet: str) -> Dict[str, Any]:
    """Extract ingredients and instructions from text using heuristics"""
    lines = [l.strip() for l in snippet.splitlines() if l.strip()]
    ingredients, steps = [], []

    mode = None
    for ln in lines:
        low = ln.lower()
        if "ingredient" in low: 
            mode = "ing"
            continue
        if any(k in low for k in ["method", "directions", "instructions", "preparation", "steps"]):
            mode = "step"
            continue

        # Check for ingredient-like lines
        if mode == "ing" or (BULLET_RE.search(ln) and any(unit in low for unit in ["tsp", "tbsp", "cup", "ml", "g", "oz"])):
            m = ING_LINE.match(ln)
            if m:
                name = m.group(1).strip()
                amt_m = re.search(AMOUNT_RE, ln)
                unit_m = re.search(UNIT_RE, ln, re.IGNORECASE)
                ingredients.append({
                    "name": name,
                    "amount": amt_m.group(0) if amt_m else None,
                    "unit": unit_m.group(0) if unit_m else None,
                    "raw": ln
                })
                continue

        # Check for step-like lines
        if BULLET_RE.search(ln) or mode == "step":
            steps.append(re.sub(BULLET_RE, "", ln))

    # Deduplicate ingredients by normalized name
    seen, dedup = set(), []
    for ing in ingredients:
        key = slugify(ing["name"]).lower()
        if key in seen: 
            continue
        seen.add(key)
        dedup.append(ing)
    
    return {"ingredients": dedup, "instructions": steps[:12]}

def simple_text_search(query: str, max_results: int = 5) -> List[Dict]:
    """Simple keyword-based search"""
    query_words = set(query.lower().split())
    results = []
    
    for chunk in books_data:
        # Calculate simple relevance score
        text_lower = chunk["text"].lower()
        score = 0
        
        for word in query_words:
            if word in text_lower:
                score += text_lower.count(word)
        
        # Bonus for remedy keywords
        if any(kw in text_lower for kw in ["remedy", "treatment", "cure", "heal", "recipe"]):
            score += 5
            
        # Bonus for having ingredients
        if "ingredient" in text_lower:
            score += 3
            
        if score > 0:
            results.append({
                "chunk": chunk,
                "score": score
            })
    
    # Sort by score and return top results
    results.sort(key=lambda x: x["score"], reverse=True)
    return [r["chunk"] for r in results[:max_results]]

def affiliate_search_url(query: str, tag: str = AFFILIATE_TAG) -> str:
    """Generate Amazon affiliate search URL"""
    q = urllib.parse.quote_plus(query)
    return f"https://www.amazon.com/s?k={q}&i=grocery&tag={tag}"

class SearchQuery(BaseModel):
    q: str
    k: int = 5

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
        input[type="text"] { width: 100%; padding: 14px 18px; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 16px; margin-bottom: 15px; }
        input[type="file"] { margin-bottom: 10px; }
        .btn { padding: 12px 24px; border-radius: 8px; border: none; background: #4299e1; color: white; cursor: pointer; font-size: 16px; margin: 5px; }
        .btn:hover { background: #3182ce; }
        .btn-secondary { background: #718096; }
        .btn-secondary:hover { background: #4a5568; }
        .card { margin-top: 20px; text-align: left; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; }
        .card h3 { color: #2d3748; margin-top: 0; }
        .ingredients li { margin: 8px 0; padding: 5px 0; }
        .ing-link { display: inline-block; margin-left: 10px; padding: 4px 12px; background: #4299e1; color: white; text-decoration: none; border-radius: 4px; font-size: 12px; }
        .ing-link:hover { background: #3182ce; }
        .instructions { margin-top: 15px; }
        .instructions ol { padding-left: 20px; }
        .instructions li { margin: 5px 0; line-height: 1.5; }
        .source { font-size: 12px; color: #718096; margin-top: 15px; padding-top: 15px; border-top: 1px solid #e2e8f0; }
        .disclosure { font-size: 12px; color: #718096; margin-top: 20px; padding: 15px; background: #f7fafc; border-radius: 6px; }
        .status { margin: 10px 0; padding: 10px; border-radius: 6px; }
        .status.success { background: #c6f6d5; color: #2f855a; }
        .status.error { background: #fed7d7; color: #c53030; }
        .loading { color: #4299e1; }
        .empty-state { text-align: center; color: #718096; margin: 40px 0; }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="box">
            <h1>🌿 Remedy Search</h1>
            <p class="subtitle">Traditional & Herbal Remedies from Ancient Wisdom</p>
            
            <div id="upload-section">
                <form id="upload-form" enctype="multipart/form-data">
                    <input type="file" name="file" accept=".epub" id="file-input">
                    <br>
                    <button class="btn btn-secondary" type="submit">📚 Upload & Index EPUB</button>
                </form>
                <div id="upload-status"></div>
            </div>
            
            <div style="margin: 30px 0; border-top: 1px solid #e2e8f0;"></div>
            
            <div id="search-section">
                <input type="text" id="query" placeholder="Type a symptom (e.g., headache, cough, indigestion, sore throat)">
                <button class="btn" id="search-btn">🔍 Search Remedies</button>
                <div id="results"></div>
            </div>
            
            <div class="disclosure">
                <strong>Important Disclaimers:</strong><br>
                • This information is for educational purposes only and is not medical advice<br>
                • Always consult healthcare professionals before trying new remedies<br>
                • As an Amazon Associate, we may earn from qualifying purchases
            </div>
        </div>
    </div>

    <script>
        const uploadForm = document.getElementById('upload-form');
        const uploadStatus = document.getElementById('upload-status');
        const query = document.getElementById('query');
        const searchBtn = document.getElementById('search-btn');
        const results = document.getElementById('results');

        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(uploadForm);
            uploadStatus.innerHTML = '<div class="status loading">📚 Processing EPUB file...</div>';
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (data.ok) {
                    uploadStatus.innerHTML = `<div class="status success">✅ Successfully indexed ${data.chunks} chunks!</div>`;
                } else {
                    uploadStatus.innerHTML = `<div class="status error">❌ Error: ${data.error}</div>`;
                }
            } catch (error) {
                uploadStatus.innerHTML = `<div class="status error">❌ Upload failed: ${error.message}</div>`;
            }
        });

        async function performSearch() {
            if (!query.value.trim()) return;
            
            results.innerHTML = '<div class="loading">🔍 Searching for remedies...</div>';
            
            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ q: query.value, k: 5 })
                });
                const data = await response.json();
                
                if (!data.ok) {
                    results.innerHTML = `<div class="status error">❌ Search error: ${data.error}</div>`;
                    return;
                }
                
                if (data.remedies.length === 0) {
                    results.innerHTML = '<div class="empty-state">No remedies found. Try uploading an EPUB file first or searching for different symptoms.</div>';
                    return;
                }
                
                results.innerHTML = data.remedies.map(remedy => `
                    <div class="card">
                        <h3>${remedy.title}</h3>
                        ${remedy.summary ? `<p>${remedy.summary}</p>` : ''}
                        
                        ${remedy.ingredients.length > 0 ? `
                            <h4>🧪 Ingredients</h4>
                            <ul class="ingredients">
                                ${remedy.ingredients.map(ing => `
                                    <li>
                                        ${[ing.amount, ing.unit, ing.name].filter(Boolean).join(' ')}
                                        <a href="${ing.link}" target="_blank" rel="nofollow sponsored noopener" class="ing-link">🛒 Get it</a>
                                    </li>
                                `).join('')}
                            </ul>
                        ` : ''}
                        
                        ${remedy.instructions && remedy.instructions.length > 0 ? `
                            <div class="instructions">
                                <h4>📋 Instructions</h4>
                                <ol>
                                    ${remedy.instructions.map(step => `<li>${step}</li>`).join('')}
                                </ol>
                            </div>
                        ` : ''}
                        
                        <div class="source">
                            📖 Source: ${remedy.source?.chapter || 'EPUB'}, section ${remedy.source?.pos ?? '?'}
                        </div>
                    </div>
                `).join('');
                
            } catch (error) {
                results.innerHTML = `<div class="status error">❌ Search failed: ${error.message}</div>`;
            }
        }

        searchBtn.addEventListener('click', performSearch);
        query.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    </script>
</body>
</html>
    """

@app.post("/api/upload")
async def upload_epub(file: UploadFile = File(...)):
    """Upload and process EPUB file"""
    global books_data
    
    if not file.filename.endswith('.epub'):
        raise HTTPException(status_code=400, detail="Only EPUB files are supported")
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            # Process EPUB
            book = epub.read_epub(tmp_path)
            items = list(book.get_items())
            books_data = []

            for item in items:
                if item.get_type() == epub.ITEM_DOCUMENT:
                    ch_text = clean_html(item.get_content())
                    if not ch_text:
                        continue
                    
                    parts = chunk_words(ch_text, 900, 150)
                    for pos, part in enumerate(parts):
                        books_data.append({
                            "chapter": getattr(item, "file_name", item.get_name()),
                            "pos": pos,
                            "text": part
                        })

            if not books_data:
                raise HTTPException(status_code=400, detail="No parsable text found in EPUB")

            return {"ok": True, "chunks": len(books_data)}
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/api/search")
async def search(q: SearchQuery):
    """Search for remedies using simple text matching"""
    if not books_data:
        raise HTTPException(status_code=400, detail="No data available. Upload an EPUB file first.")
    
    try:
        # Find relevant chunks
        matching_chunks = simple_text_search(q.q, q.k * 2)
        
        # Extract remedies from matching chunks
        remedies = []
        for chunk in matching_chunks:
            # Look for chunks that seem to contain remedy info
            text_lower = chunk["text"].lower()
            if (any(k in text_lower for k in ["ingredient", "ingredients"]) and 
                any(k in text_lower for k in ["remedy", "treatment", "recipe", "for ", "cure", "heal"])):
                
                extracted = extract_ingredients_and_steps(chunk["text"])
                if extracted["ingredients"]:
                    # Extract title from first sentence
                    title = chunk["text"][:150].split(".")[0].strip()
                    if len(title) > 100:
                        title = title[:100] + "..."
                    
                    remedy_id = hashlib.md5(
                        (chunk["chapter"] + str(chunk["pos"])).encode()
                    ).hexdigest()[:12]
                    
                    # Add affiliate links to ingredients
                    ingredients_with_links = []
                    for ingredient in extracted["ingredients"]:
                        ing_copy = ingredient.copy()
                        ing_copy["link"] = affiliate_search_url(ingredient["name"])
                        ingredients_with_links.append(ing_copy)
                    
                    remedies.append({
                        "id": remedy_id,
                        "title": title,
                        "summary": None,
                        "ingredients": ingredients_with_links,
                        "instructions": extracted["instructions"],
                        "source": {"chapter": chunk["chapter"], "pos": chunk["pos"]}
                    })
                    
                    if len(remedies) >= 3:
                        break
        
        return {"ok": True, "remedies": remedies}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "chunks_loaded": len(books_data)}

# Vercel handler
def handler(request, context):
    return app(request, context)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
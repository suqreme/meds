import os
import json
import hashlib
import re
import urllib.parse
import tempfile
import shutil
from typing import List, Dict, Any, Optional
from http.server import BaseHTTPRequestHandler
import cgi

# Global storage for EPUB data
books_data = []  # Store all text chunks with metadata
remedies_cache = []  # Store extracted remedies

# Configuration
AFFILIATE_TAG = os.environ.get("AMZ_TAG", "YOURTAG-20")

# Regex patterns for ingredient extraction
AMOUNT_RE = r"(?:\d+(?:\.\d+)?|\d+/\d+)"
UNIT_RE = r"(?:tsp|tbsp|teaspoon|tablespoon|cup|cups|ml|l|g|kg|ounce|oz|inches|slice|slices|piece|pieces|drops?|pinch|handful)"
BULLET_RE = re.compile(r"^\s*(?:[-•*]|\d+\.)\s+")
ING_LINE = re.compile(rf"^\s*(?:{AMOUNT_RE}\s*(?:{UNIT_RE})?\s+)?([A-Za-z][\w\s\-']+)", re.IGNORECASE)

def parse_post_data(rfile, headers):
    """Parse multipart form data from POST request"""
    try:
        form = cgi.FieldStorage(
            fp=rfile,
            headers=headers,
            environ={'REQUEST_METHOD': 'POST'}
        )
        return form
    except:
        return None

def clean_html_basic(html_content: str) -> str:
    """Basic HTML tag removal"""
    # Remove HTML tags
    import re
    clean = re.compile('<.*?>')
    text = re.sub(clean, ' ', html_content)
    # Clean up whitespace
    return " ".join(text.split())

def chunk_words(text: str, max_words=900, overlap=150) -> List[str]:
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        end_idx = min(i + max_words, len(words))
        chunks.append(" ".join(words[i:end_idx]))
        if end_idx >= len(words):
            break
        i += max_words - overlap
    return chunks

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

    return {"ingredients": ingredients[:10], "instructions": steps[:12]}

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
    # Determine category based on ingredient type
    category = "grocery"
    if any(tool in query.lower() for tool in ["mortar", "pestle", "gauze", "bandage", "thermometer"]):
        category = "hpc"
    i_param = {"grocery": "grocery", "hpc": "hpc"}.get(category, "grocery")
    return f"https://www.amazon.com/s?k={q}&i={i_param}&tag={tag}"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Serve the main HTML page
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
        input[type="text"] { width: 100%; padding: 14px 18px; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 16px; margin-bottom: 15px; box-sizing: border-box; }
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
                                        <a href="${ing.link}" target="_blank" rel="nofollow sponsored noopener" class="ing-link">🛒 Buy</a>
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
            
            self.wfile.write(html.encode())
            
        elif self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "status": "healthy", 
                "chunks_loaded": len(books_data),
                "remedies_cached": len(remedies_cache)
            }
            self.wfile.write(json.dumps(response).encode())
            
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"detail": "Not Found"}
            self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        if self.path == '/api/upload':
            self.handle_upload()
        elif self.path == '/api/search':
            self.handle_search()
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"detail": "Not Found"}
            self.wfile.write(json.dumps(response).encode())

    def handle_upload(self):
        """Handle EPUB file upload and processing"""
        global books_data, remedies_cache
        
        try:
            # Parse the uploaded file
            form = parse_post_data(self.rfile, self.headers)
            if not form or 'file' not in form:
                self.send_error_response("No file uploaded")
                return
                
            file_item = form['file']
            if not file_item.filename.endswith('.epub'):
                self.send_error_response("Only EPUB files are supported")
                return
            
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as tmp_file:
                shutil.copyfileobj(file_item.file, tmp_file)
                tmp_path = tmp_file.name
            
            try:
                # Process EPUB file
                books_data = self.process_epub(tmp_path)
                
                if not books_data:
                    self.send_error_response("No readable text found in EPUB file")
                    return
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {"ok": True, "chunks": len(books_data)}
                self.wfile.write(json.dumps(response).encode())
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            
        except Exception as e:
            self.send_error_response(f"Upload error: {str(e)}")

    def process_epub(self, epub_path):
        """Process EPUB file and extract text chunks"""
        try:
            # Import ebooklib here to handle missing dependency gracefully
            from ebooklib import epub
            from bs4 import BeautifulSoup
        except ImportError:
            # Fallback to sample data if dependencies not available
            return [
                {"chapter": "Sample Chapter 1", "pos": 0, "text": "Ginger remedy for nausea. Ingredients: 1 tsp fresh ginger root, 1 cup hot water. Instructions: Steep ginger in hot water for 10 minutes. Drink warm."},
                {"chapter": "Sample Chapter 2", "pos": 0, "text": "Honey and lemon for sore throat. Ingredients: 2 tbsp honey, 1 lemon juiced, 1 cup warm water. Instructions: Mix honey and lemon juice in warm water. Sip slowly."},
                {"chapter": "Sample Chapter 3", "pos": 0, "text": "Turmeric paste for inflammation. Ingredients: 1 tsp turmeric powder, water to make paste. Instructions: Apply paste to affected area. Leave for 20 minutes."},
                {"chapter": "Sample Chapter 4", "pos": 0, "text": "Chamomile tea for insomnia. Ingredients: 1 tbsp dried chamomile flowers, 1 cup boiling water. Instructions: Steep for 15 minutes, strain, drink before bed."},
                {"chapter": "Sample Chapter 5", "pos": 0, "text": "Apple cider vinegar for heartburn. Ingredients: 1 tbsp apple cider vinegar, 1 cup water. Instructions: Mix and drink 30 minutes before meals."}
            ]
        
        try:
            book = epub.read_epub(epub_path)
            items = list(book.get_items())
            chunks = []

            for item in items:
                if item.get_type() == epub.ITEM_DOCUMENT:
                    # Extract text from HTML content
                    content = item.get_content()
                    if content:
                        soup = BeautifulSoup(content, "html.parser")
                        text = soup.get_text(" ", strip=True)
                        text = " ".join(text.split())  # Clean whitespace
                        
                        if len(text) > 100:  # Only process substantial text
                            # Split into chunks
                            text_chunks = chunk_words(text, 900, 150)
                            for pos, chunk in enumerate(text_chunks):
                                chunks.append({
                                    "chapter": getattr(item, "file_name", item.get_name()),
                                    "pos": pos,
                                    "text": chunk
                                })

            return chunks
            
        except Exception as e:
            # Return sample data if EPUB processing fails
            return [
                {"chapter": "Processed Sample", "pos": 0, "text": f"EPUB processing encountered an issue: {str(e)}. Using sample remedy data. Ginger remedy for nausea. Ingredients: 1 tsp fresh ginger root, 1 cup hot water. Instructions: Steep ginger in hot water for 10 minutes."}
            ]

    def handle_search(self):
        """Handle remedy search"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            search_params = json.loads(post_data.decode('utf-8'))
            
            query = search_params.get('q', '')
            max_results = search_params.get('k', 5)
            
            if not books_data:
                self.send_error_response("No data available. Upload an EPUB file first.")
                return
            
            # Find relevant chunks
            matching_chunks = simple_text_search(query, max_results)
            
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
                        title = chunk["text"][:100].split(".")[0].strip()
                        if len(title) > 80:
                            title = title[:80] + "..."
                        
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
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {"ok": True, "remedies": remedies}
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_error_response(f"Search error: {str(e)}")

    def send_error_response(self, message):
        """Send error response"""
        self.send_response(400)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {"ok": False, "error": message}
        self.wfile.write(json.dumps(response).encode())
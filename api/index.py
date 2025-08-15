import os
import json
import hashlib
import re
import urllib.parse
from typing import List, Dict, Any
from http.server import BaseHTTPRequestHandler

# Global storage for pre-loaded EPUB data
books_data = []  # Store all text chunks with metadata

# Configuration
AFFILIATE_TAG = os.environ.get("AMZ_TAG", "YOURTAG-20")

# Regex patterns for ingredient extraction
AMOUNT_RE = r"(?:\d+(?:\.\d+)?|\d+/\d+)"
UNIT_RE = r"(?:tsp|tbsp|teaspoon|tablespoon|cup|cups|ml|l|g|kg|ounce|oz|inches|slice|slices|piece|pieces|drops?|pinch|handful)"
BULLET_RE = re.compile(r"^\s*(?:[-•*]|\d+\.)\s+")
ING_LINE = re.compile(rf"^\s*(?:{AMOUNT_RE}\s*(?:{UNIT_RE})?\s+)?([A-Za-z][\w\s\-']+)", re.IGNORECASE)

def load_epub_books():
    """Load and process the pre-existing EPUB books"""
    global books_data
    
    if books_data:  # Already loaded
        return
    
    # Debug: Check what files exist
    current_files = []
    try:
        current_files = os.listdir('.')
        print(f"Files in current directory: {current_files}")
    except Exception as e:
        print(f"Error listing files: {e}")
    
    try:
        # Try to import EPUB processing libraries
        from ebooklib import epub
        from bs4 import BeautifulSoup
        print("EPUB libraries imported successfully")
        
        epub_files = []
        # Check for EPUB files in the current directory
        for filename in ['1.epub', '2.epub', 'test-book.epub']:
            if os.path.exists(filename):
                epub_files.append(filename)
                print(f"Found EPUB file: {filename}")
        
        print(f"Total EPUB files found: {len(epub_files)}")
        
        chunks = []
        for epub_file in epub_files:
            try:
                print(f"Processing {epub_file}...")
                book = epub.read_epub(epub_file)
                items = list(book.get_items())
                print(f"Found {len(items)} items in {epub_file}")

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
                                        "book": epub_file,
                                        "chapter": getattr(item, "file_name", item.get_name()),
                                        "pos": pos,
                                        "text": chunk
                                    })
                                    
                print(f"Extracted {len([c for c in chunks if c['book'] == epub_file])} chunks from {epub_file}")
                                    
            except Exception as e:
                print(f"Error processing {epub_file}: {e}")
                continue
        
        books_data = chunks
        print(f"Total chunks loaded: {len(books_data)}")
        
    except ImportError as e:
        print(f"EPUB libraries not available: {e}")
        chunks = []  # Reset chunks for fallback
        
    # Always ensure we have some data - use sample data if no EPUB chunks were loaded
    if not chunks:
        print("Loading fallback sample data...")
        books_data = [
            {"book": "Sample Book 1", "chapter": "Digestive Issues", "pos": 0, "text": "Ginger remedy for nausea and morning sickness. Ingredients: 1 tsp fresh ginger root, 1 cup hot water, honey to taste. Instructions: Peel and slice fresh ginger. Steep in hot water for 10 minutes. Add honey and drink warm. Effective for motion sickness and pregnancy nausea."},
            
            {"book": "Sample Book 1", "chapter": "Respiratory Health", "pos": 0, "text": "Honey and lemon for sore throat and cough. Ingredients: 2 tbsp raw honey, 1 fresh lemon juiced, 1 cup warm water, pinch of salt. Instructions: Mix honey and lemon juice in warm water. Add salt and stir. Sip slowly throughout the day. Soothes throat irritation."},
            
            {"book": "Sample Book 1", "chapter": "Pain Management", "pos": 0, "text": "Turmeric paste for joint pain and inflammation. Ingredients: 2 tsp turmeric powder, coconut oil to make paste, black pepper pinch. Instructions: Mix turmeric with enough coconut oil to form thick paste. Add black pepper. Apply to affected area and cover with cloth. Leave for 30 minutes."},
            
            {"book": "Sample Book 2", "chapter": "Sleep Disorders", "pos": 0, "text": "Chamomile tea for insomnia and anxiety. Ingredients: 1 tbsp dried chamomile flowers, 1 cup boiling water, honey optional. Instructions: Pour boiling water over chamomile flowers. Steep covered for 15 minutes. Strain and add honey if desired. Drink 30 minutes before bedtime."},
            
            {"book": "Sample Book 2", "chapter": "Digestive Health", "pos": 0, "text": "Apple cider vinegar for heartburn and acid reflux. Ingredients: 1 tbsp raw apple cider vinegar with mother, 1 cup warm water, honey to taste. Instructions: Mix apple cider vinegar in warm water. Add honey to improve taste. Drink 30 minutes before meals to prevent heartburn."},
            
            {"book": "Sample Book 2", "chapter": "Skin Conditions", "pos": 0, "text": "Aloe vera gel for burns and skin irritation. Ingredients: Fresh aloe vera leaf, vitamin E oil optional. Instructions: Cut aloe leaf and extract clear gel. Apply directly to affected skin. For enhanced healing, mix with a few drops of vitamin E oil. Reapply 2-3 times daily."},
            
            {"book": "Sample Book 1", "chapter": "Headaches", "pos": 0, "text": "Peppermint oil for headache relief. Ingredients: 2-3 drops pure peppermint essential oil, 1 tsp carrier oil like coconut oil. Instructions: Dilute peppermint oil with carrier oil. Massage gently onto temples and forehead. Avoid eye area. Also inhale directly for sinus headaches."},
            
            {"book": "Sample Book 2", "chapter": "Cold and Flu", "pos": 0, "text": "Elderberry syrup for immune support. Ingredients: 1 cup dried elderberries, 3 cups water, 1 cup raw honey, 1 tsp ginger powder, cinnamon stick. Instructions: Simmer elderberries in water for 15 minutes. Strain and add honey while warm. Add spices. Take 1 tbsp daily during cold season."},
            
            {"book": "Sample Book 1", "chapter": "Circulation", "pos": 0, "text": "Cayenne pepper for poor circulation. Ingredients: 1/4 tsp cayenne pepper powder, 1 cup warm water, lemon juice optional. Instructions: Mix cayenne pepper in warm water. Add lemon juice to taste. Drink slowly. Start with smaller amount and increase gradually. Improves blood flow."},
            
            {"book": "Sample Book 2", "chapter": "Detox", "pos": 0, "text": "Dandelion root tea for liver detox. Ingredients: 1 tsp dried dandelion root, 1 cup boiling water, lemon slice. Instructions: Pour boiling water over dandelion root. Steep for 10 minutes. Strain and add lemon slice. Drink twice daily to support liver function and detoxification."}
        ]
    else:
        books_data = chunks
    
    print(f"Final: Loaded {len(books_data)} text chunks from books")

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
        # Ensure books are loaded
        load_epub_books()
        
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
    <title>Traditional Remedy Search - Natural Healing Database</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #333; }
        .wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .box { width: min(900px, 95vw); text-align: center; background: rgba(255,255,255,0.95); padding: 40px; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.15); }
        h1 { color: #2d3748; margin-bottom: 15px; font-size: 2.5em; background: linear-gradient(45deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .subtitle { color: #718096; margin-bottom: 30px; font-size: 1.2em; }
        .stats { background: #f0f7ff; padding: 15px; border-radius: 10px; margin-bottom: 30px; color: #2c5282; }
        input[type="text"] { width: 100%; padding: 16px 20px; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 18px; margin-bottom: 20px; box-sizing: border-box; transition: border-color 0.3s; }
        input[type="text"]:focus { border-color: #667eea; outline: none; }
        .btn { padding: 16px 32px; border-radius: 10px; border: none; background: linear-gradient(45deg, #667eea, #764ba2); color: white; cursor: pointer; font-size: 18px; font-weight: 600; transition: transform 0.2s; }
        .btn:hover { transform: translateY(-2px); }
        .card { margin-top: 25px; text-align: left; padding: 25px; border: 1px solid #e2e8f0; border-radius: 15px; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .card h3 { color: #2d3748; margin-top: 0; font-size: 1.3em; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
        .ingredients li { margin: 10px 0; padding: 8px 0; }
        .ing-link { display: inline-block; margin-left: 15px; padding: 6px 14px; background: linear-gradient(45deg, #667eea, #764ba2); color: white; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: 500; }
        .ing-link:hover { opacity: 0.9; }
        .instructions { margin-top: 20px; }
        .instructions ol { padding-left: 25px; }
        .instructions li { margin: 8px 0; line-height: 1.6; }
        .source { font-size: 13px; color: #718096; margin-top: 20px; padding-top: 15px; border-top: 1px solid #e2e8f0; background: #f8f9fa; padding: 15px; border-radius: 8px; }
        .disclosure { font-size: 13px; color: #718096; margin-top: 30px; padding: 20px; background: #fff3cd; border-radius: 10px; border-left: 4px solid #ffc107; }
        .status { margin: 15px 0; padding: 15px; border-radius: 10px; }
        .status.success { background: #d4edda; color: #155724; border-left: 4px solid #28a745; }
        .status.error { background: #f8d7da; color: #721c24; border-left: 4px solid #dc3545; }
        .loading { color: #667eea; font-size: 18px; }
        .empty-state { text-align: center; color: #718096; margin: 50px 0; padding: 40px; background: #f8f9fa; border-radius: 15px; }
        .sample-searches { margin: 20px 0; }
        .sample-tag { display: inline-block; margin: 5px; padding: 8px 12px; background: #e2e8f0; color: #4a5568; border-radius: 20px; cursor: pointer; font-size: 14px; transition: all 0.2s; }
        .sample-tag:hover { background: #667eea; color: white; }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="box">
            <h1>🌿 Traditional Remedy Search</h1>
            <p class="subtitle">Discover Natural Healing Wisdom from Ancient Texts</p>
            
            <div class="stats" id="stats">
                📚 Loading remedy database...
            </div>
            
            <div id="search-section">
                <input type="text" id="query" placeholder="Enter your symptoms or condition (e.g., headache, nausea, sore throat, insomnia)">
                <button class="btn" id="search-btn">🔍 Find Natural Remedies</button>
                
                <div class="sample-searches">
                    <strong>Try searching for:</strong><br>
                    <span class="sample-tag" onclick="searchFor('headache')">Headache</span>
                    <span class="sample-tag" onclick="searchFor('nausea')">Nausea</span>
                    <span class="sample-tag" onclick="searchFor('sore throat')">Sore Throat</span>
                    <span class="sample-tag" onclick="searchFor('insomnia')">Insomnia</span>
                    <span class="sample-tag" onclick="searchFor('inflammation')">Inflammation</span>
                    <span class="sample-tag" onclick="searchFor('cold')">Cold & Flu</span>
                </div>
                
                <div id="results"></div>
            </div>
            
            <div class="disclosure">
                <strong>⚠️ Important Medical Disclaimer:</strong><br>
                • This information is for educational purposes only and is not intended as medical advice<br>
                • Always consult qualified healthcare professionals before using any natural remedies<br>
                • Do not replace conventional medical treatment with these suggestions<br>
                • As an Amazon Associate, we may earn from qualifying purchases through our links
            </div>
        </div>
    </div>

    <script>
        const query = document.getElementById('query');
        const searchBtn = document.getElementById('search-btn');
        const results = document.getElementById('results');
        const stats = document.getElementById('stats');

        // Load stats on page load
        loadStats();

        async function loadStats() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                stats.innerHTML = `📚 Database contains <strong>${data.chunks_loaded}</strong> remedy sections ready for search`;
            } catch (error) {
                stats.innerHTML = '📚 Remedy database loaded and ready';
            }
        }

        function searchFor(term) {
            query.value = term;
            performSearch();
        }

        async function performSearch() {
            if (!query.value.trim()) return;
            
            results.innerHTML = '<div class="loading">🔍 Searching through traditional remedy texts...</div>';
            
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
                    results.innerHTML = '<div class="empty-state">No remedies found for this search. Try different terms like "pain", "cough", or "digestion".</div>';
                    return;
                }
                
                results.innerHTML = data.remedies.map(remedy => `
                    <div class="card">
                        <h3>${remedy.title}</h3>
                        ${remedy.summary ? `<p><em>${remedy.summary}</em></p>` : ''}
                        
                        ${remedy.ingredients.length > 0 ? `
                            <h4>🧪 Natural Ingredients</h4>
                            <ul class="ingredients">
                                ${remedy.ingredients.map(ing => `
                                    <li>
                                        <strong>${[ing.amount, ing.unit, ing.name].filter(Boolean).join(' ')}</strong>
                                        <a href="${ing.link}" target="_blank" rel="nofollow sponsored noopener" class="ing-link">🛒 Find on Amazon</a>
                                    </li>
                                `).join('')}
                            </ul>
                        ` : ''}
                        
                        ${remedy.instructions && remedy.instructions.length > 0 ? `
                            <div class="instructions">
                                <h4>📋 Preparation & Usage</h4>
                                <ol>
                                    ${remedy.instructions.map(step => `<li>${step}</li>`).join('')}
                                </ol>
                            </div>
                        ` : ''}
                        
                        <div class="source">
                            📖 Source: ${remedy.source?.book || 'Traditional Text'} - ${remedy.source?.chapter || 'Chapter'} (Section ${remedy.source?.pos || '?'})
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
            
            # Get current directory files for debugging
            try:
                current_files = os.listdir('.')
                epub_files = [f for f in current_files if f.endswith('.epub')]
            except:
                current_files = []
                epub_files = []
            
            response = {
                "status": "healthy", 
                "chunks_loaded": len(books_data),
                "books": len(set(chunk.get("book", "unknown") for chunk in books_data)),
                "debug": {
                    "total_files": len(current_files),
                    "epub_files": epub_files,
                    "sample_files": current_files[:10]  # First 10 files
                }
            }
            self.wfile.write(json.dumps(response).encode())
            
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"detail": "Not Found"}
            self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        if self.path == '/api/search':
            self.handle_search()
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"detail": "Not Found"}
            self.wfile.write(json.dumps(response).encode())

    def handle_search(self):
        """Handle remedy search"""
        load_epub_books()  # Ensure books are loaded
        
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            search_params = json.loads(post_data.decode('utf-8'))
            
            query = search_params.get('q', '')
            max_results = search_params.get('k', 5)
            
            print(f"Search request: query='{query}', max_results={max_results}")
            print(f"Books data length: {len(books_data)}")
            
            if not books_data:
                self.send_error_response("No remedy data loaded.")
                return
            
            # Find relevant chunks
            matching_chunks = simple_text_search(query, max_results * 2)
            print(f"Found {len(matching_chunks)} matching chunks")
            
            # Extract remedies from matching chunks - be more lenient
            remedies = []
            for i, chunk in enumerate(matching_chunks):
                print(f"Processing chunk {i}: {chunk['text'][:100]}...")
                
                # First, try strict search for proper remedies
                text_lower = chunk["text"].lower()
                is_remedy_chunk = (any(k in text_lower for k in ["ingredient", "ingredients"]) and 
                                 any(k in text_lower for k in ["remedy", "treatment", "recipe", "for ", "cure", "heal"]))
                
                extracted = extract_ingredients_and_steps(chunk["text"])
                
                # If we found a proper remedy, use it
                if is_remedy_chunk and extracted["ingredients"]:
                    # Extract title from first sentence
                    first_sentence = chunk["text"].split(".")[0].strip()
                    if len(first_sentence) > 100:
                        first_sentence = first_sentence[:100] + "..."
                    
                    title = first_sentence if first_sentence else f"Remedy for {query}"
                    
                    remedy_id = hashlib.md5(
                        (chunk["book"] + chunk["chapter"] + str(chunk["pos"])).encode()
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
                        "source": {
                            "book": chunk.get("book", "Traditional Text"),
                            "chapter": chunk.get("chapter", "Unknown Chapter"), 
                            "pos": chunk.get("pos", 0)
                        }
                    })
                    print(f"Added remedy: {title}")
                    
                # If no strict remedies found, create a simple remedy from any matching chunk
                elif len(remedies) == 0 and i < 3:  # Only for first few chunks if no proper remedies
                    # Create a basic remedy from the chunk
                    title = f"Traditional approach for {query}"
                    remedy_id = hashlib.md5((chunk["text"][:50]).encode()).hexdigest()[:12]
                    
                    # Extract any ingredients we can find
                    basic_ingredients = []
                    if extracted["ingredients"]:
                        basic_ingredients = extracted["ingredients"]
                    else:
                        # Try to find ingredient-like words
                        words = chunk["text"].split()
                        for word in words:
                            if any(herb in word.lower() for herb in ["ginger", "honey", "lemon", "water", "oil", "tea", "garlic", "turmeric"]):
                                basic_ingredients.append({
                                    "name": word,
                                    "amount": None,
                                    "unit": None,
                                    "raw": word,
                                    "link": affiliate_search_url(word)
                                })
                    
                    remedies.append({
                        "id": remedy_id,
                        "title": title,
                        "summary": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                        "ingredients": basic_ingredients,
                        "instructions": extracted["instructions"] or ["Refer to traditional preparation methods"],
                        "source": {
                            "book": chunk.get("book", "Traditional Text"),
                            "chapter": chunk.get("chapter", "General"), 
                            "pos": chunk.get("pos", 0)
                        }
                    })
                    print(f"Added basic remedy: {title}")
                        
                if len(remedies) >= max_results:
                    break
            
            print(f"Total remedies found: {len(remedies)}")
            
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

# Load books on module import
load_epub_books()
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
        # Try to import EPUB processing libraries with specific error handling
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
        print("EPUB libraries imported successfully")
        print(f"ebooklib version: {getattr(ebooklib, '__version__', 'unknown')}")
        
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

                document_count = 0
                for item in items:
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        document_count += 1
                        try:
                            # Extract text from HTML content
                            content = item.get_content()
                            if content:
                                soup = BeautifulSoup(content, "lxml" if "lxml" in str(content) else "html.parser")
                                text = soup.get_text(" ", strip=True)
                                text = " ".join(text.split())  # Clean whitespace
                                
                                if len(text) > 50:  # Lower threshold to capture more content
                                    print(f"Processing document {document_count}: {text[:100]}...")
                                    # Split into chunks
                                    text_chunks = chunk_words(text, 900, 150)
                                    for pos, chunk in enumerate(text_chunks):
                                        chunks.append({
                                            "book": epub_file,
                                            "chapter": getattr(item, "file_name", item.get_name()),
                                            "pos": pos,
                                            "text": chunk
                                        })
                        except Exception as doc_error:
                            print(f"Error processing document in {epub_file}: {doc_error}")
                            continue
                                    
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
        print("Loading fallback sample data - EPUB processing failed!")
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

def chunk_words(text: str, max_words=1200, overlap=200) -> List[str]:
    """Split text into overlapping chunks with better remedy detection"""
    
    # First try to split by sections/chapters if they exist
    if re.search(r'\d+\.\s+[A-Z][^.]*(?:cancer|disease|condition|remedy)', text, re.IGNORECASE):
        # Split by numbered sections (like "43. Liver Cancer")
        sections = re.split(r'(\d+\.\s+[A-Z][^.]*(?:cancer|disease|condition|remedy)[^.]*)', text, flags=re.IGNORECASE)
        chunks = []
        
        for i in range(1, len(sections), 2):  # Every other item starting from 1
            if i + 1 < len(sections):
                section_title = sections[i].strip()
                section_content = sections[i + 1].strip()
                full_section = f"{section_title} {section_content}"
                
                # If section is too long, split it but keep title
                if len(full_section.split()) > max_words:
                    content_words = section_content.split()
                    for j in range(0, len(content_words), max_words - 50):
                        chunk_content = " ".join(content_words[j:j + max_words - 50])
                        chunks.append(f"{section_title} {chunk_content}")
                else:
                    chunks.append(full_section)
        
        if chunks:
            print(f"📚 Split into {len(chunks)} section-based chunks")
            return chunks
    
    # Fallback to word-based chunking with larger size for remedies
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        end_idx = min(i + max_words, len(words))
        chunks.append(" ".join(words[i:end_idx]))
        if end_idx >= len(words):
            break
        i += max_words - overlap
    
    print(f"📚 Split into {len(chunks)} word-based chunks")
    return chunks

def extract_ingredients_and_steps(snippet: str) -> Dict[str, Any]:
    """Extract ingredients and instructions from text using heuristics"""
    print(f"\n=== EXTRACTION DEBUG START ===")
    print(f"Snippet length: {len(snippet)}")
    print(f"Snippet preview: {snippet[:200]}...")
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

    print(f"\nBasic parser found {len(ingredients)} ingredients:")
    for i, ing in enumerate(ingredients):
        print(f"  {i+1}. {ing.get('name', 'NO NAME')}: {ing}")
    
    # Always try AI extraction for better ingredients if available
    if snippet:
        print(f"\nCalling AI extraction...")
        ai_ingredients = ai_extract_ingredients(snippet)
        print(f"AI returned {len(ai_ingredients)} ingredients:")
        for i, ing in enumerate(ai_ingredients):
            print(f"  AI-{i+1}. {ing.get('name', 'NO NAME')}: {ing}")
        
        if ai_ingredients:  # If AI found ingredients, use them instead
            print(f"REPLACING basic ingredients with AI ingredients")
            ingredients = ai_ingredients
        else:
            print(f"AI returned empty list, keeping basic ingredients")

    # Always try AI formatting for better instructions if available
    if snippet:
        formatted_instructions = format_medical_text(snippet)
        if formatted_instructions and len(formatted_instructions) > 1:  # If AI formatted well, use it
            steps = formatted_instructions
        elif not steps:  # Otherwise use basic formatting as fallback
            # Basic text splitting as fallback
            steps = [snippet]

    final_ingredients = smart_dedupe_ingredients(ingredients)
    print(f"\nFinal ingredients after deduplication ({len(final_ingredients)}):")
    for i, ing in enumerate(final_ingredients):
        print(f"  FINAL-{i+1}. {ing.get('name', 'NO NAME')}: {ing}")
    print(f"=== EXTRACTION DEBUG END ===\n")
    
    return {"ingredients": final_ingredients, "instructions": steps[:12]}

def ai_extract_ingredients(text: str) -> List[Dict]:
    """Use AI to extract ingredients from remedy text"""
    
    openai_key = os.environ.get("OPENAI_API_KEY")
    print(f"OpenAI API key exists: {bool(openai_key)}")
    if openai_key:
        print(f"API key starts with: {openai_key[:10]}...")
    if not openai_key:
        print("❌ No OpenAI API key found - AI extraction disabled")
        return []
    
    print(f"Attempting AI ingredient extraction...")
    
    try:
        import openai
        # Initialize client with minimal parameters to avoid version issues
        try:
            client = openai.OpenAI(api_key=openai_key)
        except TypeError as te:
            # Fallback for older OpenAI versions  
            print(f"Trying fallback OpenAI client initialization: {te}")
            import openai as openai_fallback
            openai_fallback.api_key = openai_key
            # Use the old-style client if available
            if hasattr(openai_fallback, 'ChatCompletion'):
                client = openai_fallback
            else:
                raise te
        
        prompt = f"""You are an expert herbalist. Extract ONLY beneficial natural remedies, herbs, and healing ingredients from this traditional medicine text.

CONTEXT: This is from a traditional remedy book. Focus ONLY on:
- Medicinal herbs (Red Clover, Burdock, Rhodiola, Ginseng, Ashwagandha, Turmeric, Ginger, Devil's Claw, Nettle, Hibiscus)
- Healing foods (Coconut Water, Lemon, Honey, Garlic)
- Natural healing substances and plant extracts

IGNORE and DO NOT extract:
- Harmful substances (tobacco, alcohol, processed foods)
- Things to avoid (soft drinks, white flour, processed sugar)
- Generic foods without medicinal properties

Return ONLY a JSON array of beneficial healing ingredients:
{{"name": "ingredient_name", "amount": "1 tsp" or null, "unit": "tsp" or null}}

Text to analyze:
{text[:1500]}

Extract only beneficial healing ingredients as JSON:"""

        # Handle both new and old OpenAI client APIs
        model_name = "gpt-3.5-turbo"
        print(f"🤖 Using AI model: {model_name}")
        try:
            # New client API
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.2
            )
        except AttributeError:
            # Old client API fallback
            response = client.ChatCompletion.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
            )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ OpenAI API call succeeded, response length: {len(result)}")
        print(f"Raw AI response: {result[:500]}...")
        print(f"Input text was: {text[:300]}...")
        
        import json
        try:
            parsed_ingredients = json.loads(result)
            if isinstance(parsed_ingredients, list):
                # Filter out non-remedy items
                non_remedy_items = {
                    "soft drinks", "liquor", "tobacco", "alcohol", "cigarettes", "smoking",
                    "white flour", "white rice", "cane sugar", "processed sugar", "refined sugar", "sugar products",
                    "processed foods", "junk food", "fast food", "soda", "cola", "beer", "wine",
                    "coffee", "caffeine", "artificial sweeteners", "msg", "preservatives",
                    "meats", "pork", "beef", "chicken", "dairy", "milk", "cheese", "butter",
                    "especially pork", "cane sugar products", "white flour", "white rice",
                    "soft drink", "processed", "refined", "artificial", "chemical"
                }
                
                # Convert to our format and filter out non-remedies
                formatted_ingredients = []
                for ing in parsed_ingredients:
                    if isinstance(ing, dict) and "name" in ing:
                        ingredient_name = ing["name"].lower().strip()
                        
                        # Skip if it's in the non-remedy list
                        if any(bad_item in ingredient_name for bad_item in non_remedy_items):
                            print(f"🚫 Filtering out non-remedy: {ing['name']}")
                            continue
                        
                        # Skip overly generic items
                        if ingredient_name in ["water", "salt", "sugar", "oil"] and len(formatted_ingredients) > 5:
                            continue
                        
                        # Fix amount/unit formatting - avoid duplication
                        amount = ing.get("amount", "").strip() if ing.get("amount") else ""
                        unit = ing.get("unit", "").strip() if ing.get("unit") else ""
                        
                        # If amount already contains unit, don't add unit separately
                        if unit and amount and unit.lower() in amount.lower():
                            unit = ""
                        
                        formatted_ingredients.append({
                            "name": ing["name"].strip(),
                            "amount": amount if amount else None,
                            "unit": unit if unit else None, 
                            "raw": ing["name"]
                        })
                        
                        # Limit to reasonable number of ingredients
                        if len(formatted_ingredients) >= 15:
                            break
                
                print(f"✅ Filtered ingredients: {len(formatted_ingredients)} from {len(parsed_ingredients)} total")
                return formatted_ingredients
        except json.JSONDecodeError:
            pass
            
    except Exception as e:
        print(f"OpenAI API error in ingredient extraction: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
    
    return []

def format_medical_text(text: str) -> List[str]:
    """AI-powered formatting of medical/remedy text using OpenAI"""
    
    # First try AI formatting, fall back to manual if it fails
    try:
        ai_formatted = ai_format_remedy_text(text)
        if ai_formatted and len(ai_formatted) > 1:
            return ai_formatted
    except Exception as e:
        print(f"AI formatting failed: {e}")
    
    # Fallback to manual formatting
    return manual_format_medical_text(text)

def ai_format_remedy_text(text: str) -> List[str]:
    """Use OpenAI to intelligently format remedy text"""
    
    # Check if OpenAI API key is available
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("No OpenAI API key found")
        return []
    
    try:
        import openai
        # Initialize client with minimal parameters to avoid version issues
        try:
            client = openai.OpenAI(api_key=openai_key)
        except TypeError as te:
            # Fallback for older OpenAI versions  
            print(f"Trying fallback OpenAI client initialization: {te}")
            import openai as openai_fallback
            openai_fallback.api_key = openai_key
            # Use the old-style client if available
            if hasattr(openai_fallback, 'ChatCompletion'):
                client = openai_fallback
            else:
                raise te
        
        prompt = f"""You are an expert herbalist. Convert this traditional remedy text into PRACTICAL, actionable instructions. Return ONLY a simple JSON array of strings (not objects).

Each string should be a complete, practical instruction including:
- Specific dosages and amounts
- Clear preparation methods  
- When and how often to use
- Practical steps anyone can follow

Good examples:
"Prepare Red Clover tea: Steep 1-2 teaspoons dried red clover in 1 cup boiling water for 10-15 minutes. Drink 2-3 cups daily."
"Make Burdock root decoction: Simmer 1 tablespoon dried burdock root in 2 cups water for 20 minutes. Strain and drink 1/2 cup twice daily."  
"Turmeric paste: Mix 1 teaspoon turmeric powder with 1/4 teaspoon black pepper and 1 tablespoon coconut oil. Take twice daily with meals."

Text to convert:
{text[:1800]}

Return ONLY a JSON array of strings (NOT objects):
["instruction 1", "instruction 2", "instruction 3"]"""

        # Handle both new and old OpenAI client APIs
        model_name = "gpt-3.5-turbo"
        print(f"🤖 Using AI model for formatting: {model_name}")
        try:
            # New client API
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.3
            )
        except AttributeError:
            # Old client API fallback
            response = client.ChatCompletion.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
            )
        
        result = response.choices[0].message.content.strip()
        
        # Try to parse as JSON
        import json
        try:
            parsed_steps = json.loads(result)
            if isinstance(parsed_steps, list) and len(parsed_steps) > 0:
                # Ensure all items are strings, not objects
                string_steps = []
                for step in parsed_steps[:8]:
                    if isinstance(step, dict):
                        # Extract the main instruction text from structured object
                        if 'step' in step:
                            # Format: "Step text (Dosage: X, Timing: Y)"
                            main_step = step['step']
                            extras = []
                            if step.get('dosage') and step['dosage'] != 'As per individual preference':
                                extras.append(f"Dosage: {step['dosage']}")
                            if step.get('timing') and step['timing'] not in ['Throughout the day', 'As needed']:
                                extras.append(f"Timing: {step['timing']}")
                            
                            if extras:
                                string_steps.append(f"{main_step} ({', '.join(extras)})")
                            else:
                                string_steps.append(main_step)
                        else:
                            # Fallback to any text fields
                            text = step.get('text', step.get('instruction', str(step)))
                            string_steps.append(str(text))
                    elif isinstance(step, str):
                        string_steps.append(step)
                    else:
                        string_steps.append(str(step))
                return string_steps
        except json.JSONDecodeError:
            # If not valid JSON, split by lines
            lines = [line.strip() for line in result.split('\n') if line.strip()]
            return lines[:6]
            
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return []
    
    return []

def manual_format_medical_text(text: str) -> List[str]:
    """Fallback manual formatting with practical instructions"""
    
    # Clean up the text first
    text = re.sub(r'\s+', ' ', text).strip()
    
    sections = []
    
    # Create practical instructions based on common herbal preparation methods
    practical_instructions = [
        "Tea Preparation: For most herbs, steep 1-2 teaspoons of dried herb in 1 cup boiling water for 10-15 minutes. Strain and drink 2-3 times daily.",
        "Tincture Use: If using liquid extracts, take 1-3 dropperfuls (about 1-3 ml) in water, 2-3 times daily between meals.",
        "Fresh Juice: For vegetable juices mentioned (celery, cucumber, parsley), drink 4-8 oz fresh juice daily, preferably on an empty stomach.",
        "Dietary Integration: Include the mentioned fruits and vegetables as 50-70% of daily food intake, focusing on fresh, organic produce when possible.",
        "Treatment Duration: Continue herbal protocol for 2-4 weeks initially, then reassess. Consult healthcare provider for serious conditions.",
        "Important Note: Start with smaller doses to test tolerance. Always consult a qualified herbalist or healthcare provider before beginning any herbal treatment program."
    ]
    
    # Look for specific herbs mentioned and create targeted instructions
    herbs_found = []
    common_herbs = {
        "red clover": "Red Clover Tea: Steep 1-2 tsp dried red clover blossoms in 1 cup hot water for 10 minutes. Drink 2-3 cups daily.",
        "burdock": "Burdock Root Decoction: Simmer 1 tbsp dried burdock root in 2 cups water for 20 minutes. Strain, drink 1/2 cup twice daily.",
        "turmeric": "Turmeric Paste: Mix 1 tsp turmeric powder + 1/4 tsp black pepper + 1 tbsp coconut oil. Take twice daily with meals.",
        "ginger": "Ginger Tea: Steep 1 tsp fresh grated ginger in 1 cup hot water for 10 minutes. Add honey if desired. Drink 2-3 times daily.",
        "nettle": "Nettle Infusion: Pour 1 cup boiling water over 1-2 tsp dried nettle leaves. Steep 10-15 minutes. Drink 2-3 cups daily."
    }
    
    text_lower = text.lower()
    for herb, instruction in common_herbs.items():
        if herb in text_lower:
            herbs_found.append(instruction)
    
    # If we found specific herbs, use targeted instructions
    if herbs_found:
        sections = herbs_found[:4]  # Limit to 4 specific herb instructions
        sections.extend(practical_instructions[:2])  # Add general guidance
    else:
        # Use general practical instructions
        sections = practical_instructions
    
    return sections[:6]


def smart_dedupe_ingredients(ingredients: List[Dict]) -> List[Dict]:
    """Smart deduplication and consolidation of ingredients"""
    if not ingredients:
        return []
    
    # Group similar ingredients
    ingredient_groups = {}
    common_herbs = {
        "ginger": ["ginger", "ginger root", "fresh ginger"],
        "lemon": ["lemon", "lemon juice", "fresh lemon", "lemon juiced"],
        "honey": ["honey", "raw honey", "organic honey"],
        "water": ["water", "hot water", "warm water", "boiling water"],
        "tea": ["tea", "herbal tea", "green tea"],
        "oil": ["oil", "coconut oil", "olive oil", "essential oil"],
        "turmeric": ["turmeric", "turmeric powder", "fresh turmeric"],
        "garlic": ["garlic", "fresh garlic", "garlic cloves"],
        "rhodiola": ["rhodiola", "rhodiola root"],
        "ginseng": ["ginseng", "american ginseng", "korean ginseng"],
        "ashwagandha": ["ashwagandha", "ashwagandha root"],
        "devil's claw": ["devil's claw", "devils claw"],
        "nettle": ["nettle", "stinging nettle", "nettle leaf"],
        "coconut water": ["coconut water", "coconut milk"],
        "hibiscus": ["hibiscus", "hibiscus flower", "hibiscus tea"]
    }
    
    # Reverse mapping for quick lookup
    herb_lookup = {}
    for main_name, variants in common_herbs.items():
        for variant in variants:
            herb_lookup[variant.lower()] = main_name
    
    consolidated = {}
    
    for ing in ingredients:
        name_lower = ing["name"].lower().strip()
        
        # Skip non-ingredients
        if name_lower in ["teaspoon", "tablespoon", "cup", "boiling", "fresh", "organic", "raw"]:
            continue
            
        # Find the main ingredient name
        main_name = herb_lookup.get(name_lower, name_lower)
        
        # If we already have this ingredient, choose the best version
        if main_name in consolidated:
            existing = consolidated[main_name]
            # Prefer the version with amount and unit
            if ing["amount"] and ing["unit"] and not (existing["amount"] and existing["unit"]):
                consolidated[main_name] = ing
        else:
            consolidated[main_name] = ing
            consolidated[main_name]["name"] = main_name.title()  # Capitalize properly
    
    return list(consolidated.values())

def simple_text_search(query: str, max_results: int = 5) -> List[Dict]:
    """Precise search focused on exact query matching"""
    original_query = query.lower().strip()
    query_words = set(original_query.split())
    results = []
    
    print(f"🔍 Precise search for: '{original_query}' (words: {query_words})")
    
    # Extended remedy keywords for better matching
    remedy_keywords = ["remedy", "treatment", "cure", "heal", "recipe", "medicine", "therapeutic", 
                      "natural", "herbal", "traditional", "preparation", "formula", "mixture"]
    ingredient_keywords = ["ingredient", "ingredients", "herb", "herbs", "plant", "plants", 
                          "root", "leaf", "flower", "extract", "oil", "tea", "tincture"]
    
    for chunk in books_data:
        text_lower = chunk["text"].lower()
        score = 0
        
        # Split text into sentences for analysis
        sentences = text_lower.split('.')
        
        # ULTRA-PRECISE MATCHING: Must be specifically about the query, not just mentioning it
        if original_query in text_lower:
            # Check if this is actually ABOUT the condition, not just mentioning it in a list
            specific_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if original_query in sentence:
                    # Penalize if it's just a list of many conditions
                    condition_count = sentence.count('cancer') + sentence.count(',') + sentence.count('disease')
                    
                    if condition_count <= 3:  # Max 3 conditions mentioned = likely specific
                        score += 50
                        specific_sentences.append(sentence)
                        print(f"✅ Found specific sentence about '{original_query}': {sentence[:150]}...")
                        
                        # Extra bonus if this sentence also mentions remedies/treatments
                        if any(kw in sentence for kw in remedy_keywords):
                            score += 30
                    else:
                        # This is likely a generic list - lower score
                        score += 10
                        print(f"⚠️ Found generic list mentioning '{original_query}': {sentence[:150]}...")
            
            # If no specific sentences found, penalize heavily
            if not specific_sentences and original_query in text_lower:
                score = max(0, score - 30)
                print(f"❌ Only found '{original_query}' in generic context, reducing score")
        
        # Secondary scoring: Individual word matches but with proximity requirements
        if score == 0:  # Only if we didn't find exact matches
            words_found_in_chunk = 0
            for word in query_words:
                if word in text_lower:
                    words_found_in_chunk += 1
            
            # Only consider if most/all query words are present
            word_match_ratio = words_found_in_chunk / len(query_words)
            if word_match_ratio >= 0.8:  # At least 80% of words must be present
                score += int(word_match_ratio * 20)
                
                # Look for proximity - words should appear close together
                for sentence in sentences:
                    words_in_sentence = sum(1 for word in query_words if word in sentence)
                    if words_in_sentence >= 2:  # Multiple query words in same sentence
                        score += words_in_sentence * 5
        
        # Bonus for remedy content only if we have some base score
        if score > 0:
            if any(kw in text_lower for kw in ingredient_keywords):
                score += 3
            if any(kw in text_lower for kw in remedy_keywords):
                score += 5
            
            # PRIORITIZE Barbara O'Neill books (1.epub, 2.epub) over general content
            book_name = chunk.get("book", "").lower()
            if any(priority_book in book_name for priority_book in ["1.epub", "2.epub"]):
                score += 20  # Significant boost for Barbara O'Neill content
                print(f"📚 Boosting Barbara O'Neill book: {book_name}")
            elif "test-book" in book_name:
                score = max(0, score - 10)  # Reduce score for test content
                print(f"📚 Reducing test book score: {book_name}")
        
        if score > 0:
            results.append({
                "chunk": chunk,
                "score": score
            })
            print(f"📊 Chunk scored {score}: {chunk['text'][:100]}...")
    
    # Sort by score and return top results
    results.sort(key=lambda x: x["score"], reverse=True)
    print(f"📈 Found {len(results)} matching chunks, returning top {max_results}")
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
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&family=Playfair+Display:wght@400;500;600;700&display=swap');
        
        :root {
            --forest-primary: #2d5016;
            --forest-accent: #4a7c59;
            --forest-light: #7fb069;
            --forest-glow: #a3d977;
            --forest-mist: #c8e6c9;
            --earth-brown: #8d6e63;
            --healing-gold: #ffd54f;
            --pure-white: #ffffff;
            --soft-shadow: rgba(45, 80, 22, 0.1);
            --deep-shadow: rgba(45, 80, 22, 0.2);
            --glass-bg: rgba(255, 255, 255, 0.85);
            --glass-border: rgba(255, 255, 255, 0.3);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #1a4c3d 0%, #2d5016 25%, #4a7c59 75%, #7fb069 100%);
            background-attachment: fixed;
            color: var(--forest-primary);
            line-height: 1.7;
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 20%, rgba(163, 217, 119, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(200, 230, 201, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 40% 60%, rgba(255, 213, 79, 0.2) 0%, transparent 50%);
            pointer-events: none;
            z-index: -1;
        }
        
        .floating-leaves {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
        }
        
        .leaf {
            position: absolute;
            width: 20px;
            height: 20px;
            background: var(--forest-light);
            border-radius: 0 100% 0 100%;
            opacity: 0.6;
            animation: float 15s infinite ease-in-out;
        }
        
        .leaf:nth-child(2) { left: 10%; animation-delay: -2s; animation-duration: 12s; }
        .leaf:nth-child(3) { left: 20%; animation-delay: -4s; animation-duration: 18s; }
        .leaf:nth-child(4) { left: 30%; animation-delay: -6s; animation-duration: 14s; }
        .leaf:nth-child(5) { left: 40%; animation-delay: -8s; animation-duration: 16s; }
        .leaf:nth-child(6) { left: 60%; animation-delay: -10s; animation-duration: 13s; }
        .leaf:nth-child(7) { left: 70%; animation-delay: -12s; animation-duration: 17s; }
        .leaf:nth-child(8) { left: 80%; animation-delay: -14s; animation-duration: 15s; }
        .leaf:nth-child(9) { left: 90%; animation-delay: -16s; animation-duration: 11s; }
        
        @keyframes float {
            0%, 100% { transform: translateY(-100vh) rotate(0deg); opacity: 0; }
            10%, 90% { opacity: 0.6; }
            50% { transform: translateY(50vh) rotate(180deg); }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem 1rem;
            position: relative;
            z-index: 1;
        }
        
        .header {
            text-align: center;
            margin-bottom: 4rem;
            position: relative;
        }
        
        .title {
            font-family: 'Playfair Display', serif;
            font-size: 4rem;
            font-weight: 700;
            color: var(--pure-white);
            margin-bottom: 1rem;
            letter-spacing: -0.02em;
            text-shadow: 2px 2px 20px var(--deep-shadow);
            position: relative;
        }
        
        .title-emoji {
            display: inline-block;
            font-size: 4.5rem;
            margin-right: 1rem;
            filter: drop-shadow(0 0 20px var(--healing-gold));
            animation: glow 3s ease-in-out infinite alternate;
        }
        
        @keyframes glow {
            from { filter: drop-shadow(0 0 20px var(--healing-gold)) drop-shadow(0 0 40px var(--forest-glow)); }
            to { filter: drop-shadow(0 0 30px var(--healing-gold)) drop-shadow(0 0 60px var(--forest-glow)); }
        }
        
        .subtitle {
            font-size: 1.4rem;
            color: var(--forest-mist);
            font-weight: 400;
            margin-bottom: 2rem;
            text-shadow: 1px 1px 10px var(--soft-shadow);
        }
        
        .stats {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            padding: 1rem 2rem;
            border-radius: 50px;
            border: 1px solid var(--glass-border);
            font-weight: 500;
            color: var(--forest-primary);
            box-shadow: 0 8px 32px var(--soft-shadow);
        }
        
        .search-section {
            background: var(--glass-bg);
            backdrop-filter: blur(30px);
            padding: 3rem;
            border-radius: 25px;
            box-shadow: 0 20px 60px var(--deep-shadow);
            border: 1px solid var(--glass-border);
            margin-bottom: 3rem;
            position: relative;
            overflow: hidden;
        }
        
        .search-section::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, var(--forest-glow) 0%, transparent 70%);
            opacity: 0.1;
            animation: shimmer 6s ease-in-out infinite;
        }
        
        @keyframes shimmer {
            0%, 100% { transform: rotate(0deg); }
            50% { transform: rotate(180deg); }
        }
        
        .search-input {
            width: 100%;
            padding: 1.5rem 2rem;
            border: 2px solid var(--glass-border);
            border-radius: 20px;
            font-size: 1.2rem;
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            color: var(--forest-primary);
            font-weight: 500;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .search-input:focus {
            outline: none;
            border-color: var(--forest-light);
            background: var(--pure-white);
            box-shadow: 0 0 0 5px rgba(127, 176, 105, 0.2), inset 0 2px 10px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        
        .search-btn {
            width: 100%;
            padding: 1.5rem 2rem;
            background: linear-gradient(135deg, var(--forest-accent) 0%, var(--forest-light) 50%, var(--forest-glow) 100%);
            color: var(--pure-white);
            border: none;
            border-radius: 20px;
            font-size: 1.2rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 1.5rem;
            position: relative;
            overflow: hidden;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            box-shadow: 0 10px 30px var(--soft-shadow);
        }
        
        .search-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.5s;
        }
        
        .search-btn:hover::before {
            left: 100%;
        }
        
        .search-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 40px var(--deep-shadow);
        }
        
        .search-btn:active {
            transform: translateY(-1px);
        }
        
        .sample-searches {
            margin-top: 1.5rem;
            text-align: center;
        }
        
        .sample-label {
            color: var(--text-secondary);
            font-weight: 500;
            margin-bottom: 1rem;
            display: block;
        }
        
        .sample-tag {
            display: inline-block;
            margin: 0.25rem;
            padding: 0.5rem 1rem;
            background: var(--secondary);
            color: var(--text-secondary);
            border-radius: 100px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            transition: all 0.2s ease;
            border: 1px solid var(--border);
        }
        
        .sample-tag:hover {
            background: var(--primary);
            color: white;
            transform: translateY(-1px);
        }
        
        .remedy-card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            transition: all 0.2s ease;
        }
        
        .remedy-card:hover {
            box-shadow: var(--shadow-lg);
            transform: translateY(-2px);
        }
        
        .remedy-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 1rem;
            border-bottom: 2px solid var(--border);
            padding-bottom: 1rem;
        }
        
        .remedy-summary {
            color: var(--text-secondary);
            font-style: italic;
            margin-bottom: 1.5rem;
            font-size: 1.1rem;
        }
        
        .section-title {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin: 1.5rem 0 1rem 0;
        }
        
        .ingredients-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }
        
        .ingredient-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg-page);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        
        .ingredient-name {
            font-weight: 500;
            color: var(--text-primary);
        }
        
        .ingredient-link {
            background: var(--primary);
            color: white;
            text-decoration: none;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .ingredient-link:hover {
            background: var(--primary-dark);
            transform: scale(1.05);
        }
        
        .instructions-list {
            list-style: none;
            counter-reset: step-counter;
        }
        
        .instructions-list li {
            counter-increment: step-counter;
            margin-bottom: 1rem;
            padding: 1rem;
            background: var(--bg-page);
            border-radius: 8px;
            border-left: 3px solid var(--primary);
            position: relative;
        }
        
        .instructions-list li::before {
            content: counter(step-counter);
            position: absolute;
            left: -1.5rem;
            top: 1rem;
            background: var(--primary);
            color: white;
            border-radius: 50%;
            width: 2rem;
            height: 2rem;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 0.875rem;
        }
        
        .source-info {
            background: var(--secondary);
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1.5rem;
            border-left: 3px solid var(--primary);
        }
        
        .source-text {
            font-size: 0.875rem;
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .loading {
            text-align: center;
            padding: 4rem;
            background: var(--glass-bg);
            backdrop-filter: blur(30px);
            border-radius: 25px;
            border: 1px solid var(--glass-border);
            box-shadow: 0 20px 60px var(--deep-shadow);
            position: relative;
            overflow: hidden;
        }
        
        .loading::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, var(--healing-gold) 0%, transparent 70%);
            opacity: 0.1;
            animation: shimmer 4s ease-in-out infinite;
        }
        
        .spinner {
            width: 3rem;
            height: 3rem;
            border: 4px solid rgba(127, 176, 105, 0.3);
            border-top: 4px solid var(--forest-light);
            border-radius: 50%;
            animation: spin 1.5s linear infinite;
            margin: 0 auto 2rem;
            position: relative;
            z-index: 1;
        }
        
        .spinner::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 1rem;
            height: 1rem;
            background: var(--healing-gold);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            animation: pulse 2s ease-in-out infinite;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 
            0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
            50% { transform: translate(-50%, -50%) scale(1.5); opacity: 0.7; }
        }
        
        .loading-text {
            color: var(--forest-primary);
            font-weight: 600;
            margin-bottom: 1rem;
            font-size: 1.2rem;
            position: relative;
            z-index: 1;
        }
        
        .loading-subtext {
            color: var(--forest-accent);
            font-size: 1rem;
            position: relative;
            z-index: 1;
        }
        
        .disclaimer {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border: 1px solid #f59e0b;
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 3rem;
        }
        
        .disclaimer-title {
            font-weight: 600;
            color: #92400e;
            margin-bottom: 0.5rem;
        }
        
        .disclaimer-text {
            font-size: 0.875rem;
            color: #92400e;
            line-height: 1.5;
        }
        
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: var(--text-secondary);
        }
        
        .status.error {
            background: #fef2f2;
            color: #dc2626;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 1rem;
        }
        
        @media (max-width: 768px) {
            .title { font-size: 2rem; }
            .container { padding: 1rem; }
            .search-section { padding: 1.5rem; }
            .remedy-card { padding: 1.5rem; }
            .ingredients-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="floating-leaves">
        <div class="leaf"></div>
        <div class="leaf"></div>
        <div class="leaf"></div>
        <div class="leaf"></div>
        <div class="leaf"></div>
        <div class="leaf"></div>
        <div class="leaf"></div>
        <div class="leaf"></div>
        <div class="leaf"></div>
    </div>
    
    <div class="container">
        <div class="header">
            <h1 class="title"><span class="title-emoji">🌿</span> Natural Healing Sanctuary</h1>
            <p class="subtitle">Ancient Wisdom from Barbara O'Neill's Sacred Remedy Collection</p>
            
            <div class="stats" id="stats">
                📚 Loading sacred remedy database...
            </div>
        </div>
        
        <div class="search-section">
            <input type="text" class="search-input" id="query" placeholder="Search for conditions like liver cancer, stomach pain, inflammation...">
            <button class="search-btn" id="search-btn">🔍 Find Natural Remedies</button>
            
            <div class="sample-searches">
                <span class="sample-label">Popular searches:</span>
                <span class="sample-tag" onclick="searchFor('liver cancer')">Liver Cancer</span>
                <span class="sample-tag" onclick="searchFor('stomach cancer')">Stomach Cancer</span>
                <span class="sample-tag" onclick="searchFor('inflammation')">Inflammation</span>
                <span class="sample-tag" onclick="searchFor('headache')">Headache</span>
                <span class="sample-tag" onclick="searchFor('arthritis')">Arthritis</span>
                <span class="sample-tag" onclick="searchFor('diabetes')">Diabetes</span>
            </div>
        </div>
        
        <div id="results"></div>
        
        <div class="disclaimer">
            <div class="disclaimer-title">⚠️ Important Medical Disclaimer</div>
            <div class="disclaimer-text">
                This information is for educational purposes only and is not intended as medical advice. 
                Always consult qualified healthcare professionals before using any natural remedies. 
                Do not replace conventional medical treatment with these suggestions. 
                As an Amazon Associate, we may earn from qualifying purchases through our links.
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
            
            // Show modern forest-themed loading indicator
            results.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <div class="loading-text">🌿 Searching Sacred Remedy Forest...</div>
                    <div class="loading-subtext">Discovering ancient healing wisdom from Barbara O'Neill's collection</div>
                </div>
            `;
            
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
                    <div class="remedy-card">
                        <h2 class="remedy-title">${remedy.title}</h2>
                        ${remedy.summary ? `<p class="remedy-summary">${remedy.summary}</p>` : ''}
                        
                        ${remedy.ingredients.length > 0 ? `
                            <div class="section-title">🧪 Natural Ingredients</div>
                            <div class="ingredients-grid">
                                ${remedy.ingredients.map(ing => `
                                    <div class="ingredient-item">
                                        <span class="ingredient-name">${[ing.amount, ing.unit, ing.name].filter(Boolean).join(' ')}</span>
                                        <a href="${ing.link}" target="_blank" rel="nofollow sponsored noopener" class="ingredient-link">🛒 Shop</a>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                        
                        ${remedy.instructions && remedy.instructions.length > 0 ? `
                            <div class="section-title">📋 Preparation & Usage</div>
                            <ol class="instructions-list">
                                ${remedy.instructions.map(step => `<li>${step}</li>`).join('')}
                            </ol>
                        ` : ''}
                        
                        <div class="source-info">
                            <div class="source-text">📖 Source: ${remedy.source?.book || 'Barbara O\'Neill Book'} - ${remedy.source?.chapter || 'Chapter'} (Section ${remedy.source?.pos || '?'})</div>
                        </div>
                    </div>
                `).join('');
                
            } catch (error) {
                results.innerHTML = `<div class="status error">❌ Search failed: ${error.message}</div>`;
            }
        }

        // Add event listeners with debugging
        searchBtn.addEventListener('click', (e) => {
            console.log('Search button clicked');
            e.preventDefault();
            performSearch();
        });
        
        query.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                console.log('Enter key pressed');
                e.preventDefault();
                performSearch();
            }
        });
        
        // Ensure DOM is loaded
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded, elements:', {
                query: !!query,
                searchBtn: !!searchBtn,
                results: !!results
            });
        });
    </script>
</body>
</html>
            """
            
            self.wfile.write(html.encode())
            
        elif self.path == '/api/debug':
            # Debug endpoint to test EPUB processing
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            debug_info = {
                "epub_libraries": False,
                "epub_files_found": [],
                "processing_log": []
            }
            
            try:
                import ebooklib
                from ebooklib import epub
                from bs4 import BeautifulSoup
                debug_info["epub_libraries"] = True
                debug_info["processing_log"].append("EPUB libraries imported successfully")
                
                # Try to process one EPUB file
                if os.path.exists('1.epub'):
                    try:
                        book = epub.read_epub('1.epub')
                        items = list(book.get_items())
                        debug_info["processing_log"].append(f"1.epub: Found {len(items)} items")
                        
                        doc_count = 0
                        for item in items:
                            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                                doc_count += 1
                                if doc_count <= 3:  # Only process first 3 documents
                                    content = item.get_content()
                                    if content:
                                        soup = BeautifulSoup(content, "html.parser")
                                        text = soup.get_text(" ", strip=True)[:200]
                                        debug_info["processing_log"].append(f"Document {doc_count}: {text}...")
                        
                        debug_info["processing_log"].append(f"Total documents in 1.epub: {doc_count}")
                        
                    except Exception as e:
                        debug_info["processing_log"].append(f"Error processing 1.epub: {str(e)}")
                
            except ImportError as e:
                debug_info["processing_log"].append(f"Cannot import EPUB libraries: {str(e)}")
            except Exception as e:
                debug_info["processing_log"].append(f"Other error: {str(e)}")
            
            self.wfile.write(json.dumps(debug_info, indent=2).encode())
            
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
        print("🔍 SEARCH REQUEST RECEIVED!")
        load_epub_books()  # Ensure books are loaded
        
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            search_params = json.loads(post_data.decode('utf-8'))
            
            query = search_params.get('q', '')
            max_results = search_params.get('k', 5)
            
            print(f"🔍 Search request: query='{query}', max_results={max_results}")
            print(f"📚 Books data length: {len(books_data)}")
            print(f"📊 Search parameters: {search_params}")
            
            if not books_data:
                self.send_error_response("No remedy data loaded.")
                return
            
            # Find relevant chunks
            matching_chunks = simple_text_search(query, max_results * 2)
            print(f"Found {len(matching_chunks)} matching chunks")
            
            # Extract remedies from matching chunks - be more lenient
            remedies = []
            used_remedy_ids = set()  # Track unique remedies to prevent duplicates
            used_titles = set()  # Track titles to prevent similar content
            
            # Define remedy keywords for relevance checking
            remedy_keywords = ["remedy", "treatment", "cure", "heal", "recipe", "medicine", "therapeutic", 
                              "natural", "herbal", "traditional", "preparation", "formula", "mixture"]
            
            # Make query available for processing
            original_query = query.lower().strip()
            for i, chunk in enumerate(matching_chunks):
                print(f"Processing chunk {i}: {chunk['text'][:100]}...")
                
                # First, try strict search for proper remedies
                text_lower = chunk["text"].lower()
                
                # Check if this chunk is actually relevant to the query
                query_relevance = 0
                if original_query in text_lower:
                    # Check how many times query appears and in what context
                    query_count = text_lower.count(original_query)
                    # Check if it's surrounded by remedy context
                    sentences_with_query = [s for s in text_lower.split('.') if original_query in s]
                    remedy_context_count = sum(1 for s in sentences_with_query 
                                             if any(kw in s for kw in remedy_keywords))
                    query_relevance = query_count + remedy_context_count * 2
                
                # Skip chunks that are clearly not relevant to the specific query
                irrelevant_keywords = ["children", "kids", "baby", "infant", "toddler", "pediatric"]
                if any(ikw in text_lower for ikw in irrelevant_keywords) and query_relevance < 2:
                    print(f"❌ Skipping irrelevant chunk (children/pediatric content): {chunk['text'][:100]}...")
                    continue
                
                # Skip generic detox/cleansing content unless specifically relevant
                generic_keywords = ["detox", "cleansing", "general health", "overall wellness"]
                if any(gkw in text_lower for gkw in generic_keywords) and query_relevance < 3:
                    print(f"❌ Skipping generic content: {chunk['text'][:100]}...")
                    continue
                
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
                    
                    # Create more unique remedy ID using content hash
                    content_snippet = chunk["text"][:200] + title  # Use content + title for uniqueness
                    remedy_id = hashlib.md5(content_snippet.encode()).hexdigest()[:12]
                    
                    # Check for duplicate remedies by ID and title similarity
                    title_key = title.lower().replace(" ", "").replace("-", "").replace(":", "")[:50]
                    
                    if remedy_id in used_remedy_ids or title_key in used_titles:
                        print(f"Skipping duplicate remedy: {remedy_id} - {title[:50]}...")
                        continue
                    
                    used_remedy_ids.add(remedy_id)
                    used_titles.add(title_key)
                    print(f"✅ Adding unique remedy: {remedy_id} - {title[:50]}...")
                    
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
                    # Create unique ID for basic remedies too
                    content_snippet = chunk["text"][:200] + title
                    remedy_id = hashlib.md5(content_snippet.encode()).hexdigest()[:12]
                    title_key = title.lower().replace(" ", "").replace("-", "").replace(":", "")[:50]
                    
                    # Check for duplicate remedies by ID and title similarity
                    if remedy_id in used_remedy_ids or title_key in used_titles:
                        print(f"Skipping duplicate basic remedy: {remedy_id} - {title[:50]}...")
                        continue
                    
                    used_remedy_ids.add(remedy_id)
                    used_titles.add(title_key)
                    print(f"✅ Adding unique basic remedy: {remedy_id} - {title[:50]}...")
                    
                    # Extract any ingredients we can find
                    basic_ingredients = []
                    if extracted["ingredients"]:
                        basic_ingredients = extracted["ingredients"]
                    else:
                        # Try to find ingredient-like words from common herbs
                        text_lower = chunk["text"].lower()
                        common_ingredients = ["ginger", "honey", "lemon", "water", "oil", "tea", "garlic", "turmeric", 
                                           "cinnamon", "pepper", "salt", "vinegar", "chamomile", "mint", "basil"]
                        
                        found_ingredients = set()
                        for ingredient in common_ingredients:
                            if ingredient in text_lower and ingredient not in found_ingredients:
                                found_ingredients.add(ingredient)
                                basic_ingredients.append({
                                    "name": ingredient.title(),
                                    "amount": None,
                                    "unit": None,
                                    "raw": ingredient,
                                    "link": affiliate_search_url(ingredient)
                                })
                                if len(basic_ingredients) >= 5:  # Limit to 5 basic ingredients
                                    break
                    
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
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
        
        prompt = f"""You are an expert herbalist. Convert this traditional remedy text into PRACTICAL, actionable instructions that people can actually follow. Focus on HOW TO USE the ingredients with specific amounts, preparation methods, and timing.

Transform the text into clear steps that include:
1. SPECIFIC DOSAGES (how much of each ingredient)
2. PREPARATION METHODS (how to make teas, tinctures, etc.)
3. TIMING (when to take, how often)
4. DURATION (how long to continue treatment)
5. PRACTICAL APPLICATION (exactly what to do)

Examples of good instructions:
- "Prepare Red Clover tea: Steep 1-2 teaspoons dried red clover in 1 cup boiling water for 10-15 minutes. Drink 2-3 cups daily."
- "Make Burdock root decoction: Simmer 1 tablespoon dried burdock root in 2 cups water for 20 minutes. Strain and drink 1/2 cup twice daily."
- "Turmeric paste: Mix 1 teaspoon turmeric powder with 1/4 teaspoon black pepper and 1 tablespoon coconut oil. Take this mixture twice daily with meals."

Text to convert:
{text[:2000]}

Return ONLY a JSON array of practical step-by-step instructions with specific dosages and methods:"""

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
                        # If it's an object, convert to string representation
                        string_steps.append(str(step.get('text', step.get('instruction', str(step)))))
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
        .loading { 
            color: #667eea; 
            font-size: 18px; 
            text-align: center; 
            padding: 30px; 
            background: #f0f7ff; 
            border-radius: 15px; 
            border-left: 4px solid #667eea;
        }
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #e2e8f0;
            border-radius: 50%;
            border-top-color: #667eea;
            animation: spin 1s ease-in-out infinite;
            margin-right: 10px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .loading-text {
            display: inline-block;
            animation: pulse 1.5s ease-in-out infinite alternate;
        }
        @keyframes pulse {
            from { opacity: 0.6; }
            to { opacity: 1; }
        }
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
            
            // Show enhanced loading indicator
            results.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <span class="loading-text">🔍 Analyzing traditional remedy texts...</span>
                    <br><br>
                    <small>Extracting herbs and ingredients using AI...</small>
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
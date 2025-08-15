# Remedy Search

A powerful web application that searches traditional and herbal remedy books (EPUB format) and automatically generates Amazon affiliate links for ingredients.

## Features

- 📚 **EPUB Processing**: Upload and index traditional remedy books
- 🔍 **Smart Search**: Vector-based semantic search for symptoms and conditions  
- 🧪 **Ingredient Extraction**: Automatically extracts ingredients with amounts and units
- 📋 **Instructions**: Structured step-by-step remedy instructions
- 🛒 **Affiliate Links**: Auto-generated Amazon affiliate links for ingredients
- 💻 **Responsive Design**: Works on desktop and mobile devices
- ⚡ **Fast Performance**: Optimized for quick search results

## Technology Stack

- **Backend**: FastAPI (Python)
- **Search**: FAISS vector search with sentence transformers
- **EPUB Processing**: ebooklib + BeautifulSoup
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Deployment**: Vercel

## Quick Start

### Local Development

1. **Clone and setup**:
   ```bash
   cd remedy-search
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your Amazon affiliate tag
   ```

3. **Run locally**:
   ```bash
   python -m uvicorn api.index:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Open**: http://localhost:8000

### Vercel Deployment

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Deploy**:
   ```bash
   vercel --prod
   ```

3. **Set environment variables** in Vercel dashboard:
   - `AMZ_TAG`: Your Amazon affiliate tag (required)
   - `ADMIN_TOKEN`: Optional admin token for upload restrictions

## Usage

### Upload EPUB

1. Click "Upload & Index EPUB" 
2. Select your traditional remedy EPUB file
3. Wait for processing (creates searchable index)

### Search Remedies

1. Type a symptom in the search box (e.g., "headache", "cough", "indigestion")
2. View structured remedies with:
   - Ingredient lists with Amazon affiliate links
   - Step-by-step instructions
   - Source citations

## Environment Variables

- `AMZ_TAG`: Your Amazon Associates affiliate tag (required for affiliate links)
- `ADMIN_TOKEN`: Optional token to restrict EPUB uploads

## API Endpoints

- `GET /`: Main web interface
- `POST /api/upload`: Upload and process EPUB files
- `POST /api/search`: Search for remedies
- `GET /api/health`: Health check

## Features in Detail

### EPUB Processing
- Extracts text from EPUB chapters
- Chunks text for optimal search performance
- Creates vector embeddings for semantic search
- Identifies remedy sections with ingredients

### Ingredient Extraction
- Uses regex patterns to identify ingredients with amounts/units
- Supports common measurements (tsp, tbsp, cups, ml, oz, etc.)
- Deduplicates similar ingredients
- Generates appropriate Amazon search categories

### Amazon Affiliate Integration
- Automatic category detection (grocery, health, garden)
- Search links instead of direct product links (ToS compliant)
- Proper rel attributes for SEO compliance
- Clear affiliate disclosures

### Security & Compliance
- File type validation
- Content sanitization
- Medical disclaimers
- Affiliate disclosure
- Rate limiting ready

## File Structure

```
remedy-search/
├── api/
│   └── index.py          # FastAPI backend
├── public/
│   └── index.html        # Static redirect
├── requirements.txt      # Python dependencies
├── vercel.json          # Vercel configuration
├── package.json         # Project metadata
└── README.md           # This file
```

## Deployment Notes

### Vercel Specific
- Uses `@vercel/python` runtime
- 30-second function timeout
- In-memory storage (ephemeral)
- Cold start optimization

### Performance Tips
- Lazy loading of heavy ML dependencies
- Efficient chunking strategy
- Normalized embeddings for faster search
- Batch processing for embeddings

## Legal Disclaimers

⚠️ **Important**: This application is for educational purposes only
- Not medical advice - always consult healthcare professionals
- Remedies are from uploaded books, not verified medical sources  
- Amazon affiliate links are clearly disclosed
- Users should verify ingredient safety and dosages

## Support

For issues or questions:
1. Check the health endpoint: `/api/health`
2. Review browser console for errors
3. Verify EPUB file format and content

## License

This project is provided as-is for educational purposes. Users are responsible for:
- Complying with Amazon Associates terms
- Ensuring uploaded content rights
- Following local regulations for health information
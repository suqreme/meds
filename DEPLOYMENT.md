# Deployment Guide for Vercel

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Amazon Associates Account**: For affiliate links
3. **Git Repository**: Push your code to GitHub/GitLab

## Step-by-Step Deployment

### 1. Prepare for Deployment

```bash
# Navigate to project directory
cd remedy-search

# Ensure all files are present
ls -la
# Should see: api/, public/, requirements.txt, vercel.json, package.json
```

### 2. Install Vercel CLI

```bash
npm install -g vercel
```

### 3. Login to Vercel

```bash
vercel login
```

### 4. Deploy to Vercel

```bash
# Deploy to production
vercel --prod

# Follow the prompts:
# - Set up and deploy? Y
# - Which scope? (your account)
# - Link to existing project? N
# - Project name: remedy-search
# - Directory: ./
```

### 5. Configure Environment Variables

In the Vercel dashboard:

1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add these variables:

```
AMZ_TAG=your-amazon-affiliate-tag-20
ADMIN_TOKEN=optional-admin-password
```

**Important**: Replace `your-amazon-affiliate-tag-20` with your actual Amazon Associates tag.

### 6. Redeploy with Environment Variables

```bash
vercel --prod
```

## Configuration Details

### Vercel Settings

The `vercel.json` file configures:
- Python runtime for the API
- Static file serving for public directory
- Route handling between static and API endpoints
- 30-second timeout for processing EPUBs

### Runtime Specifications

- **Runtime**: Python 3.9
- **Function Timeout**: 30 seconds
- **Memory**: Default Vercel allocation
- **Cold Start**: Optimized with lazy imports

## Environment Variables Explained

| Variable | Required | Description |
|----------|----------|-------------|
| `AMZ_TAG` | Yes | Your Amazon Associates affiliate tag (e.g., "yoursite-20") |
| `ADMIN_TOKEN` | No | Password to restrict EPUB uploads (leave empty for public uploads) |

## Testing Your Deployment

### 1. Basic Health Check

Visit: `https://your-app.vercel.app/api/health`

Should return:
```json
{"status": "healthy", "has_index": false}
```

### 2. Upload Test

1. Go to your app URL
2. Upload one of the EPUB files from `/home/ariappa/meds/`
3. Wait for processing confirmation
4. Try searching for "headache" or "cough"

### 3. Search Test

After uploading, search for common symptoms:
- "headache"
- "cough" 
- "indigestion"
- "sore throat"

## Troubleshooting

### Common Issues

**1. Import Errors**
- Check that `requirements.txt` includes all dependencies
- Verify Python version compatibility

**2. EPUB Processing Fails**
- Ensure EPUB file is valid
- Check file size (Vercel has limits)
- Review function logs in Vercel dashboard

**3. Search Returns No Results**
- Verify EPUB was processed successfully
- Check that book contains ingredient lists
- Try different search terms

**4. Affiliate Links Not Working**
- Verify `AMZ_TAG` environment variable is set
- Check Amazon Associates account status
- Ensure links include proper affiliate tag

### Debug Steps

1. **Check Vercel Function Logs**:
   ```bash
   vercel logs
   ```

2. **Local Testing**:
   ```bash
   pip install -r requirements.txt
   uvicorn api.index:app --reload
   ```

3. **Environment Variables**:
   ```bash
   vercel env ls
   ```

## Performance Optimization

### Cold Start Mitigation
- Heavy dependencies are imported only when needed
- Model initialization is lazy
- Embeddings are computed in batches

### Memory Usage
- FAISS index stored in memory (ephemeral)
- Chunking strategy optimized for search quality vs. memory
- Cleanup of temporary files

### Search Performance
- Normalized embeddings for faster similarity search
- Limited result sets (top 3-5)
- Efficient deduplication

## Security Considerations

### File Upload Security
- File type validation (only .epub)
- Content sanitization with BeautifulSoup
- No persistent file storage

### API Security
- CORS configured for web access
- Optional admin token for upload restriction
- No sensitive data in logs

### Content Safety
- Clear medical disclaimers
- Affiliate link disclosures
- Source attribution

## Scaling Considerations

### Current Limitations
- In-memory storage (lost on cold starts)
- Single-user concurrent uploads
- 30-second processing timeout

### Future Improvements
- Database storage for persistent indexes
- Background job processing
- Multiple book management
- User accounts and saved searches

## Cost Optimization

### Vercel Usage
- Serverless functions bill per invocation
- Static hosting is free up to bandwidth limits
- Consider function timeout vs. cost trade-offs

### Amazon Associates
- Search links are free (no API costs)
- Commission only on actual purchases
- No price scraping (ToS compliant)

## Legal Requirements

### Amazon Associates Compliance
- Proper affiliate disclosure on all pages
- Search links instead of direct product links
- No price display or scraping
- Compliance with state/country regulations

### Medical Disclaimers
- Clear "not medical advice" messaging
- Educational purpose statements
- Recommendation to consult healthcare providers

## Monitoring

### Key Metrics to Track
- EPUB processing success rate
- Search response times
- Affiliate link click-through rates
- Function error rates

### Vercel Analytics
Enable in Vercel dashboard for:
- Page views
- Function invocations
- Error rates
- Performance metrics

## Support

For deployment issues:
1. Check Vercel function logs
2. Verify environment variables
3. Test locally first
4. Review requirements.txt dependencies

For Amazon Associates issues:
1. Verify affiliate tag format
2. Check account status
3. Ensure link compliance
4. Review ToS requirements
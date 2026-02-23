# Environment Setup

## Setting Up Your .env File

The project requires a `.env` file with your configuration. This file is not tracked in git for security reasons.

### Quick Setup

1. Copy the example file:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Edit `.env` and add your actual credentials:
   - Replace `AZURE_API_KEY` with your Azure OpenAI API key
   - Replace `AZURE_ENDPOINT` with your Azure endpoint URL
   - Update database passwords if different from defaults

### Required Configuration

**Azure OpenAI** (required for AI-powered features):
```
AZURE_API_KEY=your_actual_azure_api_key
AZURE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
```

**Database** (default values work for local development):
```
DATABASE_URL=postgresql://postgres:12345@localhost:5432/tdm
TARGET_DATABASE_URL=postgresql://postgres:12345@localhost:5432/tdm_target
```

### Security Note

**NEVER commit the `.env` file to git!**
- It contains sensitive credentials
- The `.env.example` file is the template for reference
- Your actual `.env` file stays local only

### Verifying Setup

Check if your environment is configured correctly:

```powershell
cd tdm-backend
python -c "from config import settings; print('✓ Config loaded successfully')"
```

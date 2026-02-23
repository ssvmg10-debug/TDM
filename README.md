# Test Data Management (TDM) Platform

> Enterprise-grade Test Data Management with dynamic synthetic data generation, PII masking, and environment provisioning.

## 🚀 Quick Start

### Start Backend
```powershell
cd tdm-backend
python -m uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### Start UI
```powershell
cd tdm-ui
npm run dev
```

### Access
- **UI**: http://localhost:5173
- **API**: http://localhost:8002
- **API Docs**: http://localhost:8002/docs

## ✨ Features

### 🎯 Three Ways to Generate Test Data

1. **Schema-Based** - From existing databases
   - Discover database schema
   - Generate data matching structure
   - Perfect for database cloning

2. **Domain-Based** ⭐ NEW
   - Pre-configured domain packs
   - E-Commerce, Banking, Telecom, Healthcare
   - Multiple scenarios per domain
   - No database needed!

3. **Test Case-Based** ⭐ INNOVATIVE
   - Crawl test case URLs
   - Extract form fields automatically
   - Generate matching test data
   - Perfect for UI/E2E testing

### 🛡️ Complete TDM Workflow

```
Schema Discovery → PII Classification → Subsetting → Masking → Provisioning
```

- **Schema Discovery**: Auto-detect database structure
- **PII Classification**: Identify sensitive data (email, phone, SSN, etc.)
- **Subsetting**: Extract related data subsets with FK integrity
- **Masking**: Transform PII (deterministic hash, email masking, redaction, tokenization)
- **Provisioning**: Deploy to environments (QA, SIT, UAT, Perf, Dev)
- **Lineage Tracking**: Full audit trail
- **Governance**: RBAC, audit logs, compliance

## 📊 Available Domains

| Domain | Entities | Scenarios |
|--------|----------|-----------|
| **E-Commerce** | customer, order, order_item, product, payment | default, b2c, b2b, marketplace |
| **Banking** | account, transaction, customer, loan, beneficiary | default, retail, corporate, investment |
| **Telecom** | customer, sim, recharge, plan, usage | default, prepaid, postpaid, enterprise |
| **Healthcare** | patient, appointment, prescription, doctor | default, hospital, clinic, pharmacy |

## 🏗️ Architecture

```
PostgreSQL (Metadata + Data) ←→ FastAPI Backend ←→ React UI
                                        ↓
                            Services: Crawler, Generator,
                            Discovery, PII, Masking, etc.
```

## 📚 Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Get started in 5 minutes
- **[E2E Testing Guide](docs/TDM_E2E_TESTING_GUIDE.md)** - Complete testing scenarios
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - What was built
- **[Full Implementation](docs/TDM_IMPLEMENTATION_END_TO_END.md)** - Architecture details

## 💡 Example Usage

### Generate E-Commerce Data
```bash
curl -X POST http://localhost:8002/api/v1/synthetic \
  -H "Content-Type: application/json" \
  -d '{"domain": "ecommerce", "scenario": "b2c", "row_counts": {"*": 1000}}'
```

### Generate from Test Case URL
```bash
curl -X POST http://localhost:8002/api/v1/synthetic \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_urls": ["https://example.com/register"],
    "domain": "generic",
    "row_counts": {"*": 500}
  }'
```

### Discover Database Schema
```bash
curl -X POST http://localhost:8002/api/v1/discover-schema \
  -H "Content-Type: application/json" \
  -d '{
    "connection_string": "postgresql://user:pass@host:5432/db",
    "schemas": ["public"]
  }'
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Database
DATABASE_URL=postgresql://postgres:12345@localhost:5432/tdm

# API
API_PORT=8002

# Azure OpenAI (Optional - for PII LLM classification)
AZURE_API_KEY=your_key
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_DEPLOYMENT=gpt-4.1
```

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8002/health
```

### List Available Domains
```bash
curl http://localhost:8002/api/v1/synthetic/domains
```

### View API Documentation
Open http://localhost:8002/docs in your browser

## 🎓 Use Cases

### 1. No Database Access
**Solution**: Use domain-based generation
- Select domain (e.g., Banking)
- Choose scenario (e.g., retail)
- Generate realistic test data instantly

### 2. Test New UI Forms
**Solution**: Use test case crawling
- Provide form/page URLs
- System extracts fields
- Generates matching data

### 3. Clone Production Data
**Solution**: Use full TDM workflow
- Discover production schema
- Classify PII
- Create masked subset
- Provision to test environment

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **UI**: React, TypeScript, Vite, TanStack Query, Tailwind CSS
- **Data Generation**: Faker, Pandas, Playwright (for crawling)
- **Optional**: Azure OpenAI (PII classification)

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### Backend Setup
```bash
cd tdm-backend
pip install -r requirements.txt
python reset_db.py  # Initialize database
python seed_env.py  # Seed environments
python -m uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### UI Setup
```bash
cd tdm-ui
npm install --ignore-scripts
npm run dev
```

### Optional: Playwright (for test case crawling)
```bash
pip install playwright
playwright install chromium
```

## 🌟 Key Features

- ✅ **Dynamic Test Data Generation** - Three flexible modes
- ✅ **PII Protection** - Auto-detect and mask sensitive data
- ✅ **Environment Management** - Deploy to multiple environments
- ✅ **Data Lineage** - Track data provenance
- ✅ **Audit Logs** - Complete operation history
- ✅ **RESTful API** - Full programmatic access
- ✅ **Modern UI** - Intuitive web interface
- ✅ **Realistic Data** - Uses Faker for authentic test data
- ✅ **FK Integrity** - Maintains relational consistency
- ✅ **Incremental Provisioning** - Efficient data loading

## 📝 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/v1/synthetic/domains` | GET | List domains |
| `/api/v1/synthetic` | POST | Generate data |
| `/api/v1/discover-schema` | POST | Discover schema |
| `/api/v1/pii/classify` | POST | Classify PII |
| `/api/v1/subset` | POST | Create subset |
| `/api/v1/mask` | POST | Apply masking |
| `/api/v1/provision` | POST | Provision data |
| `/api/v1/schemas` | GET | List schemas |
| `/api/v1/datasets` | GET | List datasets |
| `/api/v1/jobs` | GET | List jobs |

## 🎯 Roadmap

- [ ] SDV (Synthetic Data Vault) integration
- [ ] API schema extraction (OpenAPI/Swagger)
- [ ] Advanced relationship inference
- [ ] Redis job queue
- [ ] MinIO/S3 storage
- [ ] Kubernetes deployment
- [ ] CI/CD pipelines
- [ ] Performance testing

## 📄 License

MIT

## 🤝 Contributing

Contributions welcome! See documentation for development guidelines.

---

**Built with ❤️ for QA Engineers and Test Data Managers**

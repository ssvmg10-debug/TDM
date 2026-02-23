# TDM Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Start Backend
```powershell
cd tdm-backend
python -m uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### 2. Start UI
```powershell
cd tdm-ui
npm run dev
```

### 3. Open Browser
```
http://localhost:5173
```

---

## ✅ Quick Tests

### Test 1: Generate Synthetic Data (No Database Needed!)

**Via UI** (Easiest):
1. Go to **Synthetic Data Factory**
2. Select **Domain Pack** mode
3. Click **E-Commerce** card
4. Click **Generate Synthetic Data**
5. Go to **Dataset Catalog** → See your data!

**Via API**:
```bash
# Get available domains
curl http://localhost:8002/api/v1/synthetic/domains

# Generate e-commerce data
curl -X POST http://localhost:8002/api/v1/synthetic \
  -H "Content-Type: application/json" \
  -d '{"domain": "ecommerce", "row_counts": {"*": 100}}'
```

### Test 2: Generate from Test Case (Dynamic!)

**Via UI**:
1. Go to **Synthetic Data Factory**
2. Select **Test Case URLs** mode
3. Enter URL: `https://example.com` (or your test page)
4. Click **Generate Synthetic Data**
5. Check **Jobs** for status

**Via API**:
```bash
curl -X POST http://localhost:8002/api/v1/synthetic \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_urls": ["https://example.com/register"],
    "domain": "generic",
    "row_counts": {"*": 50}
  }'
```

### Test 3: Full Database Flow

1. **Discover Schema**:
   ```bash
   curl -X POST http://localhost:8002/api/v1/discover-schema \
     -H "Content-Type: application/json" \
     -d '{
       "connection_string": "postgresql://postgres:12345@localhost:5432/tdm",
       "schemas": ["public"]
     }'
   ```

2. **Generate from Schema**:
   - UI: **Synthetic Data Factory** → **Existing Schema** mode
   - Select schema and generate

---

## 📊 Available Domains

| Domain | Entities | Scenarios |
|--------|----------|-----------|
| **E-Commerce** | customer, order, order_item, product, payment | default, b2c, b2b, marketplace |
| **Banking** | account, transaction, customer, loan, beneficiary | default, retail, corporate, investment |
| **Telecom** | customer, sim, recharge, plan, usage | default, prepaid, postpaid, enterprise |
| **Healthcare** | patient, appointment, prescription, doctor, diagnosis | default, hospital, clinic, pharmacy |

---

## 🔄 Complete Workflow

```
1. Schema Discovery (Optional - if you have a database)
   ↓
2. PII Classification (Identifies sensitive data)
   ↓
3. Choose Path:
   A. Subsetting (Extract subset from database)
   B. Synthetic (Generate from schema/domain/testcases)
   ↓
4. Masking (Optional - mask sensitive columns)
   ↓
5. Provisioning (Load to QA/SIT/UAT/Perf/Dev)
   ↓
6. View in Audit Logs & Lineage
```

---

## 🎯 Common Use Cases

### Use Case 1: No Database Access
**Solution**: Domain-based synthetic generation
```bash
curl -X POST http://localhost:8002/api/v1/synthetic \
  -H "Content-Type: application/json" \
  -d '{"domain": "banking", "scenario": "retail", "row_counts": {"*": 1000}}'
```

### Use Case 2: Test New UI Forms
**Solution**: Test case crawling
- Add your form URLs to Synthetic Data Factory
- System extracts fields and generates matching data

### Use Case 3: Clone Production Data
**Solution**: Full TDM flow
1. Discover production schema
2. Classify PII
3. Create subset
4. Mask sensitive data
5. Provision to test environment

---

## 📝 API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/v1/synthetic/domains` | GET | List available domains |
| `/api/v1/synthetic` | POST | Generate synthetic data |
| `/api/v1/discover-schema` | POST | Discover database schema |
| `/api/v1/pii/classify` | POST | Classify PII columns |
| `/api/v1/subset` | POST | Create data subset |
| `/api/v1/mask` | POST | Apply masking rules |
| `/api/v1/provision` | POST | Provision to environment |
| `/api/v1/schemas` | GET | List schemas |
| `/api/v1/datasets` | GET | List datasets |
| `/api/v1/jobs` | GET | List jobs |
| `/api/v1/environments` | GET | List environments |

---

## 🐛 Quick Troubleshooting

**Backend not starting?**
```powershell
# Check if port 8002 is free
netstat -ano | findstr :8002

# If occupied, kill process or change port
```

**UI not connecting?**
- Verify backend is running: `curl http://localhost:8002/health`
- Check `.env` file in tdm-ui folder

**No data generated?**
- Check Jobs page for errors
- View job logs: `curl http://localhost:8002/api/v1/job/<job_id>`

**Playwright errors?**
```powershell
pip install playwright
playwright install chromium
```

---

## 💡 Tips

1. **Start Simple**: Use domain-based generation first
2. **Small Data Sets**: Start with 100-1000 rows
3. **Check Jobs**: Always monitor Jobs page for status
4. **Dataset Catalog**: Your one-stop for all generated data
5. **Audit Logs**: Track all operations

---

## 🎓 Learning Path

1. **Beginner**: Generate synthetic data from domain pack
2. **Intermediate**: Discover schema and generate from it
3. **Advanced**: Full workflow with masking and provisioning
4. **Expert**: Test case crawling for dynamic scenarios

---

## 📚 More Information

- Full guide: `docs/TDM_E2E_TESTING_GUIDE.md`
- Implementation details: `docs/TDM_IMPLEMENTATION_END_TO_END.md`
- UI testing: `docs/UI_TESTING_GUIDE.md`

---

## ✨ New Features

### Dynamic Test Case Crawling
- Provide any test page URL
- System automatically:
  - Extracts form fields
  - Detects data types
  - Generates matching data
- Perfect for UI/E2E testing

### Domain Packs
- Pre-configured for common industries
- Multiple scenarios per domain
- Realistic entity relationships
- Consistent data generation

### Flexible Generation
- Three modes in one UI
- Switch between modes easily
- Combine with masking/provisioning
- Full audit trail

---

**🎉 You're ready to go! Start with synthetic generation and explore from there.**

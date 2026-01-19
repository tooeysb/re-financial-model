# CLAUDE.md - Project Context for Claude Code

## Project Overview

Sand Point Real Estate App - A web-based application replicating institutional-quality Excel pro forma models for commercial real estate underwriting. Based on the 225 Worth Ave, Palm Beach retail property model.

## Resources

| Resource | URL/Location |
|----------|--------------|
| GitHub Repo | https://github.com/tooeysb/sand-point-re-app |
| Live App | https://re-fin-model-225worth-3348ecdc48e8.herokuapp.com/ |
| Heroku App Name | `re-fin-model-225worth` |
| Supabase Project | https://ubbbzshlasonurybnwra.supabase.co |

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy
- **Frontend:** Jinja2 Templates, HTMX, Alpine.js, Tailwind CSS
- **Database:** SQLite (local dev), PostgreSQL/Supabase (production)
- **Calculations:** Python (numpy, pandas)
- **Hosting:** Heroku

## Project Structure

```
app/
├── api/           # FastAPI route handlers
│   ├── calculations.py  # /api/calculate/* endpoints
│   ├── properties.py    # /api/properties endpoints
│   └── scenarios.py     # /api/scenarios endpoints
├── calculations/  # Core financial calculation engine
│   ├── irr.py          # IRR/NPV/XIRR calculations (Newton-Raphson)
│   ├── amortization.py # Loan amortization schedules
│   ├── cashflow.py     # Monthly cash flow generation
│   └── waterfall.py    # LP/GP distribution calculations
├── db/            # SQLAlchemy models
│   ├── models.py       # Property, Scenario, Lease, Loan models
│   └── database.py     # Database connection config
├── services/      # Business logic services (to be built)
└── ui/
    ├── templates/      # Jinja2 HTML templates
    │   ├── base.html   # Base template with Tailwind/HTMX
    │   ├── index.html  # Dashboard
    │   └── model.html  # Model editor (Alpine.js)
    └── static/css/     # Custom styles
docs/
└── 225_Worth_Ave_Model_Documentation_PRD.md  # Full technical docs & PRD
```

## Key Commands

```bash
# Local development
uvicorn app.main:app --reload

# Deploy to Heroku
git push origin main && git push heroku main

# View Heroku logs
heroku logs --tail --app re-fin-model-225worth

# Set Heroku config
heroku config:set KEY=value --app re-fin-model-225worth
```

## Database Configuration

**Local Development:** Uses SQLite by default (`sqlite:///./dev.db`)

**Production (Supabase):** PostgreSQL - connection string format:
```
postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

**Note:** The `&` character in passwords must be URL-encoded as `%26`

## Core Features to Build

Based on the PRD in `docs/225_Worth_Ave_Model_Documentation_PRD.md`:

1. **Property Setup** - Property info, multi-property portfolio support
2. **Rent Roll** - Multi-tenant lease management with full abstraction
3. **Operating Assumptions** - Revenue, expenses, escalations
4. **Financing** - Multiple loan tranches, fixed/floating rates, SOFR curves
5. **Exit Assumptions** - Cap rate, sales costs, terminal value
6. **Waterfall** - Flexible multi-hurdle LP/GP distribution structures
7. **Reports** - PDF/Excel export, sensitivity tables

## Calculation Engine (Already Implemented)

- `app/calculations/irr.py` - XIRR using Newton-Raphson method
- `app/calculations/amortization.py` - Full loan amortization schedules
- `app/calculations/cashflow.py` - Monthly cash flow projections
- `app/calculations/waterfall.py` - LP/GP waterfall distributions

## API Endpoints

```
GET  /                          # Dashboard
GET  /model/{model_id}          # Model editor
GET  /health                    # Health check

POST /api/calculate/cashflows   # Calculate full cash flows
POST /api/calculate/irr         # Calculate IRR from cash flows
POST /api/calculate/amortization # Generate amortization schedule

GET  /api/properties            # List properties
POST /api/properties            # Create property
GET  /api/scenarios             # List scenarios
POST /api/scenarios             # Create scenario
```

## Key Financial Metrics

| Metric | Description |
|--------|-------------|
| NOI | Net Operating Income (Revenue - OpEx) |
| IRR | Internal Rate of Return (XIRR compatible) |
| MOIC | Multiple on Invested Capital |
| Cash-on-Cash | Period cash flow / equity invested |
| DSCR | Debt Service Coverage Ratio |

## Reference Property (225 Worth Ave)

- **Location:** Palm Beach, FL (retail)
- **Size:** 9,932 RSF
- **Purchase Price:** $41.5M
- **Tenants:** Peter Millar/G-Fore, J. McLaughlin, Gucci
- **Hold Period:** 10 years
- **Exit Cap Rate:** 5%
- **Expected Returns:** 8.54% unleveraged IRR, 11.43% leveraged IRR

## Development Phases

1. Foundation, auth, basic cash flows
2. Full financing, debt schedules
3. Waterfall, scenarios, sensitivity
4. Collaboration, reporting
5. Advanced analytics, integrations

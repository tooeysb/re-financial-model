# Real Estate Financial Model

A modern, web-based real estate financial modeling application that provides institutional-quality underwriting capabilities for commercial real estate investments.

## Overview

This application replicates and enhances the functionality of traditional Excel-based real estate pro forma models, providing:

- **Multi-tenant rent roll management** with lease abstractions
- **Monthly cash flow projections** with revenue and expense modeling
- **Debt modeling** supporting multiple loan tranches (construction, permanent, mezzanine)
- **Waterfall distributions** with multi-hurdle LP/GP promote structures
- **Return metrics** including IRR, equity multiple, cash-on-cash
- **Scenario analysis** and sensitivity testing
- **Professional reporting** and Excel export

## Project Structure

```
├── app/
│   ├── api/           # FastAPI route handlers
│   ├── calculations/  # Core financial calculation engine
│   ├── db/            # SQLAlchemy models and database config
│   ├── services/      # Business logic services
│   └── ui/
│       ├── templates/ # Jinja2 HTML templates
│       └── static/    # CSS, JS assets
├── docs/              # Documentation and PRD
├── migrations/        # Alembic database migrations
├── scripts/           # Utility scripts
├── tests/             # Test suite
└── README.md
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Frontend | Jinja2 Templates, HTMX, Alpine.js, Tailwind CSS |
| Database | SQLite (dev), PostgreSQL/Supabase (prod) |
| Calculations | Python (numpy, pandas) |
| Hosting | Heroku |

## Getting Started

### Prerequisites

- Python 3.11+
- pip or pipenv

### Installation

```bash
# Clone the repository
git clone https://github.com/tooeysb/re-financial-model.git
cd re-financial-model

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env

# Run the development server
uvicorn app.main:app --reload
```

Open http://localhost:8000 in your browser.

## Features

### Core Modules

1. **Property Setup** - Property information, multi-property portfolio support
2. **Rent Roll** - Multi-tenant lease management with full abstraction
3. **Operating Assumptions** - Revenue, expenses, escalations
4. **Financing** - Multiple loan tranches, fixed/floating rates, SOFR curves
5. **Exit Assumptions** - Cap rate, sales costs, terminal value
6. **Waterfall** - Flexible multi-hurdle distribution structures

### Calculation Engine

- Monthly granularity for 30+ year projections
- Real-time recalculation via HTMX
- IRR using Newton-Raphson method (XIRR compatible)
- Full amortization schedule generation
- Waterfall distribution calculations

### Key Calculations

| Metric | Description |
|--------|-------------|
| NOI | Net Operating Income (Revenue - OpEx) |
| IRR | Internal Rate of Return |
| MOIC | Multiple on Invested Capital |
| Cash-on-Cash | Period cash flow / equity invested |
| DSCR | Debt Service Coverage Ratio |

## API Endpoints

```
GET  /                     # Dashboard
GET  /model/{model_id}     # Model editor
GET  /health               # Health check

POST /api/calculate/cashflows    # Calculate cash flows
POST /api/calculate/irr          # Calculate IRR
POST /api/calculate/amortization # Generate amortization schedule

GET  /api/properties       # List properties
POST /api/properties       # Create property
GET  /api/scenarios        # List scenarios
POST /api/scenarios        # Create scenario
```

## Live Demo

**Production App:** https://re-fin-model-225worth-3348ecdc48e8.herokuapp.com/

## Deployment (Heroku)

The app is deployed to Heroku with the following configuration:

- **App Name:** `re-fin-model-225worth`
- **Region:** US
- **Database:** Supabase PostgreSQL

### Deploy Updates

```bash
# Push to both GitHub and Heroku
git push origin main
git push heroku main
```

### Environment Variables (Heroku)

Required config vars (already set):
- `DATABASE_URL` - Supabase PostgreSQL connection string
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anon key

### Manual Deployment

```bash
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set DATABASE_URL="postgresql://..." --app your-app-name

# Deploy
git push heroku main

# Run migrations (if needed)
heroku run alembic upgrade head --app your-app-name
```

## Documentation

Full documentation is available in the `/docs` directory:

- [Technical Documentation](docs/225_Worth_Ave_Model_Documentation_PRD.md) - Complete model analysis
- [PRD](docs/225_Worth_Ave_Model_Documentation_PRD.md#part-2-product-requirements-document-prd) - Product requirements

## Development Roadmap

| Phase | Focus |
|-------|-------|
| 1 | Foundation, auth, basic cash flows |
| 2 | Full financing, debt schedules |
| 3 | Waterfall, scenarios, sensitivity |
| 4 | Collaboration, reporting |
| 5 | Advanced analytics, integrations |

## License

MIT License - see [LICENSE](LICENSE) for details.

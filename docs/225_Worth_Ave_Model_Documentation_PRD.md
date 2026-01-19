# 225 Worth Ave Real Estate Financial Model
## Technical Documentation & Product Requirements Document (PRD)

---

# PART 1: MODEL DOCUMENTATION

## 1. Executive Summary

This document provides a comprehensive technical analysis of the "225 Worth Ave" Excel-based real estate financial model. The model is a sophisticated multi-sheet financial analysis tool designed to evaluate the acquisition, operation, and disposition of a retail property located in Palm Beach, FL.

### Property Overview
- **Property**: 225 Worth Ave, Palm Beach, FL
- **Land SF**: 12,502 sq ft
- **Building RSF**: 9,932 sq ft (Net Rentable)
- **Purchase Price**: $41,500,000
- **Asset Type**: Multi-tenant retail property
- **Key Tenants**: Peter Millar/G-Fore, J. McLaughlin, Gucci

### Model Output Summary
| Metric | Unleveraged | Leveraged |
|--------|-------------|-----------|
| Profit | $42,035K | $29,767K |
| Multiple | 2.00x | 2.57x |
| IRR | 8.57% | 10.09% |
| LP IRR | - | 9.39% |
| GP IRR | - | 15.02% |

---

## 2. Model Architecture

### 2.1 Sheet Structure Overview

The model consists of **9 interconnected worksheets**:

| Sheet | Rows | Cols | Purpose |
|-------|------|------|---------|
| **Assumptions** | 80 | 40 | Central input hub - all key parameters |
| **Model** | 191 | 331 | Core monthly cash flow engine |
| **Waterfall** | 143 | 144 | LP/GP distribution waterfall calculations |
| **Debt** | 1,066 | 20 | Loan amortization schedules |
| **SOFR** | 125 | 19 | Interest rate forward curve data |
| **LCs** | 26 | 15 | Lease commission calculations |
| **Comps** | 101 | 63 | Comparable property data |
| **Charts** | 47 | 34 | Visual output (charts/graphs) |
| **Info from Bill** | 41 | 15 | Source data/due diligence info |

### 2.2 Data Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Info from Bill │────▶│   Assumptions   │────▶│      Model      │
│  (Source Data)  │     │  (Inputs Hub)   │     │ (Cash Flow Eng) │
└─────────────────┘     └────────┬────────┘     └────────┬────────┘
                                 │                       │
┌─────────────────┐              │                       │
│      SOFR       │──────────────┤                       │
│  (Rate Curve)   │              │                       │
└─────────────────┘              │                       │
                                 ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│       LCs       │────▶│      Debt       │◀────│    Waterfall    │
│(Lease Commiss.) │     │(Amort. Schedule)│     │ (Distributions) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 3. Assumptions Sheet - Detailed Analysis

### 3.1 Global Controls
- **Cell C1**: Circular reference trigger (0/1) - controls model calculation mode
- **All monetary values**: Expressed in thousands ($000s) except PSF amounts

### 3.2 Building Summary (Rows 6-9)
| Parameter | Cell | Value/Formula |
|-----------|------|---------------|
| Land SF | F7 | 12,502 |
| Building RSF | F8 | 9,932 |
| Implied FAR | F9 | `=F8/F7` |

### 3.3 Project Timing (Rows 6-9)
| Phase | Start | Duration | End |
|-------|-------|----------|-----|
| Acquisition | Month 0 | 1 | Month 0 |
| Untitled Phase | Month 1 | 18 | Month 18 |
| Project Sale | - | - | Month 120 |

**Key Timing Cells:**
- `J7-L7`: Acquisition timing
- `L9`: Sale month (120 = 10-year hold)
- `T7`: Stabilization month (77)

### 3.4 Acquisition Financing (Rows 11-27)

**Loan Structure:**
| Parameter | Cell | Value/Formula |
|-----------|------|---------------|
| Total Debt | L12 | `=L24` (from loan proceeds) |
| Total Equity | L13 | `=L22-L12` |
| Fixed/Floating | L14 | 0 (Fixed) |
| Interest Rate | J15 | 5.00% (Fixed) |
| Spread (Floating) | K15 | 200 bps |
| Loan Fees | K16 | 1.00% |
| Loan Closing Costs | K17 | 1.00% |
| I/O Period | L18 | 120 months |
| Amortization Period | L19 | 30 years |
| LTC | L23 | 55.5% |
| Total Proceeds | L24 | `=L22*L23` |

### 3.5 Permanent Loan Parameters (Rows 29-47)

| Parameter | Cell | Value/Formula |
|-----------|------|---------------|
| Total Debt | L30 | `=L44` |
| Fixed/Floating | L32 | 0 (Fixed) |
| Interest Rate (Fixed) | J33 | 5.00% |
| Interest Rate (Floating) | K33 | +200 bps spread |
| Loan Fees | K34 | 1.00% |
| I/O Period | L36 | 60 months |
| Amortization | L37 | 30 years |
| Loan Constant | L39 | 7.39% |
| Debt Yield Test | K42 | 6.50% |
| Cap Rate Test | K43 | Exit cap rate |
| Final Loan Size | L44 | `=MIN(L42:L43)` (lower of debt yield or value) |

### 3.6 Retail Rent Roll (Rows 7-11, Columns AC-AN)

| Space | Tenant | RSF | In-Place Rent PSF | Market Rent PSF | Lease End | Options | Annual Bumps |
|-------|--------|-----|-------------------|-----------------|-----------|---------|--------------|
| A | Peter Millar (G/Fore) | 2,300 | $201.45 | $300.00 | 12/31/2031 | 10 yrs | 2.50% |
| B | Georgica Pine (J McLaughlin) | 1,868 | $200.47 | $300.00 | 5/31/2030 | None | 2.50% |
| C | Gucci America Inc | 5,950 | $187.65 | $300.00 | 9/30/2033 | 10 yrs | 2.50% |
| **Total** | - | **10,118** | **$193.22** | **$300.00** | - | - | - |

### 3.7 Operating Assumptions (Rows 38-59)

**Revenue Assumptions:**
| Parameter | Cell | Value |
|-----------|------|-------|
| Market Retail Rent PSF | T39 | $300/SF/year |
| Parking Income Rate | T40 | $0/stall/month |
| Storage Income Rate | T41 | $0/unit/month |
| Lease Term (new) | T42 | 10 years |
| TI Buildout Period | T49 | 6 months |
| Free Rent | T50 | 10 months |
| General Vacancy | T51 | 0% |
| Collection Loss | T52 | 0% |

**Expense Assumptions:**
| Parameter | Cell | Value |
|-----------|------|-------|
| Fixed OpEx PSF | T54 | $36.00/SF |
| Variable OpEx PSF | T55 | Formula from detailed expenses |
| Management Fee | T56 | 4% of revenue |
| Property Tax Millage | S57 | 1.50% of purchase price |
| CapEx Reserve | T59 | $5.00/SF |

### 3.8 Exit Assumptions (Rows 12-18, Columns W-AA)

| Parameter | Cell | Value/Formula |
|-----------|------|---------------|
| Sale Month | X13 | 120 (Month) |
| Forward NOI | AA14 | `=SUM(OFFSET(Model!K69,0,X13+1,1,12))+...` |
| Retail Cap Rate | AA15 | 5.00% |
| Gross Exit Value | AA16 | `=AA14/AA15` |
| Sales Costs | Z17 | 1.00% |
| Net Exit Proceeds | AA18 | `=SUM(AA16:AA17)` |

### 3.9 Waterfall Structure (Rows 71-80)

| Parameter | Cell | Value |
|-----------|------|-------|
| LP Share | Z73 | 90% |
| GP Share | Z74 | 10% |
| Hurdle I Pref | X76 | 5.00% |
| Hurdle I LP/GP | Z76/AA76 | 90%/10% |
| Hurdle II Pref | X77 | 5.00% |
| Hurdle II LP/GP | Z77/AA77 | 75%/8.33% |
| Hurdle III Pref | X78 | 5.00% |
| Final Split LP/GP | Z79/AA79 | 75%/8.33% |
| Compound Pref Monthly | Y80 | 0 (No) |

---

## 4. Model Sheet - Cash Flow Engine

### 4.1 Structure Overview

The Model sheet is a monthly cash flow model spanning **331 columns** (approximately 27+ years) with **191 rows** of calculations.

**Timeline Structure:**
- Row 10: Month numbers (0-320+)
- Row 12: Dates (actual calendar dates)
- Column I: Total/Summary column (SUMIF aggregations)
- Columns K onwards: Monthly periods

### 4.2 Escalation Factors (Rows 2-5)

| Factor | Row | Annual Rate | Formula Pattern |
|--------|-----|-------------|-----------------|
| Market Rent | 2 | 2.50% | `=K2*(1+$D2)^(1/12)` |
| Expenses | 3 | 2.50% | `=K3*(1+$D3)^(1/12)` |
| Property Taxes | 4 | 2.50% | Annual bumps only |
| Other Costs | 5 | 2.50% | `=$K5*(1+$F5)^(L$10/12)` |

### 4.3 Unlevered Costs (Rows 14-43)

**Acquisition Costs (Rows 15-18):**
```
Purchase Price (Row 16): =IF(K$10=0,Assumptions!$C$13,0)
Closing Costs (Row 17): =IF(K$10=0,Assumptions!$C$14,0)
Total Acquisition (Row 18): =SUM(K16:K17)
```

**Development Costs (Rows 20-42):**
- Entitlement costs (referencing Assumptions sheet)
- Retail TIs by space (Rows 33-35)
- Retail LCs by space (Rows 36-38)
- Soft costs and contingencies

**Total Summary (Row 43):**
```
=SUM(K18,K24,K42)
```

### 4.4 Revenue Module (Rows 45-59)

**Retail Revenue by Space (Rows 46-48):**
```excel
Row 46 (Space A):
=IF(K$10=0,0,
  IF(K$10<=$F46,
    $E46*$G46*K$2/12/1000,
    IF(K$10>$F46,
      $E46*$H46*K$2/12/1000,0)))
```

**Key Logic:**
- Before lease expiry: In-place rent × escalation factor
- After lease expiry: Market rent × escalation factor
- TI buildout period adjustment
- Free rent deduction periods

**Free Rent (Rows 49-51):**
```excel
=IF(AND(K$10<$G49,K$10>=$E49,$H49=0),-K46,0)
```

**Other Revenue (Rows 52-55):**
- Parking Income: `=$F52*$G52/1000*K$2`
- Storage Revenue: `=$F53*$G53/1000*K$2`
- Reimbursement Revenue (Fixed): `=SUM(K61,K65)` (OpEx + Taxes)
- Reimbursement Revenue (Variable): `=SUM(K62:K64)`

**Total Revenue (Rows 56-59):**
```excel
Total Potential Revenue (56): =SUM(K46:K55)
General Vacancy (57): =-$F57*SUM(K$46:K$55)
Collection Loss (58): =-$F58*SUM(K$46:K$53)
Effective Revenue (59): =SUM(K56:K58)
```

### 4.5 Operating Expenses Module (Rows 61-67)

| Line Item | Row | Formula Pattern |
|-----------|-----|-----------------|
| Fixed OpEx | 61 | `=$F61*SUM($E$46:$E$48)/12/1000*K$3` |
| Variable OpEx | 62 | `=$F62*SUM($E$46:$E$48)/12/1000*K$3` |
| Parking Expense | 63 | `=$F63*K52` (% of parking revenue) |
| Management Fee | 64 | `=$F64*K59` (% of effective revenue) |
| Property Taxes | 65 | Complex annual escalation logic |
| CapEx Reserves | 66 | `=$F66*SUM($E$46:$E$48)*K$3/1000/12` |
| **Total OpEx** | 67 | `=SUM(K61:K66)` |

### 4.6 NOI Calculations (Rows 69-72)

```excel
Retail Potential NOI (69): =K59-K67
Total Potential NOI (71): =SUM(K69)
Total Actual NOI (72): =IF(K$10<=Assumptions!$L$9,K71,0)
```

### 4.7 Exit Proceeds (Row 74)

```excel
=IF(K10=Assumptions!$X$13,Assumptions!$AA$18,0)
```

### 4.8 Unleveraged Analysis (Rows 76-85)

| Metric | Row | Formula |
|--------|-----|---------|
| Unleveraged Costs | 76 | Referenced from costs section |
| Operating Losses | 77 | `=-MIN(K72,0)` |
| Less CF from Operations | 78 | `=-MAX(MIN(K76,K72),0)` |
| Equity Investment | 79 | `=SUM(K76:K78)` |
| **Unleveraged CF** | 81 | `=SUM(K74,K72,-K43)` |
| Profit | 82 | Cumulative positive cash flows |
| Investment | 83 | `-SUMIF(K81:KZ81,"<0")` |
| Multiple | 84 | `=I82/I83+1` |
| IRR | 85 | `=XIRR(K81:KZ81,K12:KZ12)` |

### 4.9 Leveraged Analysis - Acquisition Loan (Rows 87-127)

**Cash Flow After Debt Service (Rows 89-91):**
```excel
NOI (89): =MAX(0,K$72)
Less Debt Service (90): =-MIN(K89,K123)
CF After DS (91): =SUM(K89:K90)
```

**Levered Costs (Rows 93-104):**
- Operating Losses (95)
- Loan Closing Costs & Fees (96)
- Capitalized Interest (97)
- Variable Contribution (104)

**Equity Tracking (Rows 106-111):**
```excel
Beginning Balance (107): Previous ending
Required Funding (108): Costs requiring funding
Less CF Used as Source (109): Cash flow offset
Equity Draws (110): Complex waterfall logic
Ending Balance (111): =SUM(K107:K110)
```

**Interest Rate Calculation (Rows 113-116):**
```excel
Date Reference (113): Calendar date
SOFR Curve (114): Lookup from SOFR sheet
Spread (115): From Assumptions
Effective Rate (116): =IF($G$114=1,SUM(K114:K115),K115)
```

**Debt Schedule (Rows 118-127):**
```excel
Beginning Balance (119): =J127
Debt Draws (120): =IF(K$10>$I129,0,K104-K110)
Amortization (121): INDEX/MATCH from Debt sheet
Interest (122): =AVERAGE(K119,K119+K120)*K116*(K12-J12)/365
Total Debt Service (123): =SUM(K121:K122)
Capitalized Interest (125): =SUM(K123:K124)
Ending Balance (127): =K119+K120+K126-K121
```

### 4.10 Leveraged Analysis - Perm Loan (Rows 129-171)

Similar structure to Acquisition Loan with:
- Different loan parameters
- Refinancing trigger at construction completion
- Separate amortization schedule

### 4.11 Summary Cash Flows (Rows 173-190)

**Unleveraged Summary (Rows 173-177):**
```excel
(+/-) Acquisition/Disposition (173)
(-) Entitlement Costs (174)
(-) Soft Costs (175)
(+) NOI (176): =K72
Unleveraged CF (177): =SUM(K173:K176)
```

**Leveraged Summary (Rows 178-190):**
```excel
(+) Construction Loan Draws (178)
(+) Perm Loan Draws (179)
(-) Construction Loan DS (180)
(-) Perm Loan DS (181)
(-) Construction Closing Costs (182)
(-) Perm Closing Costs (183)
(-) Construction Principal Paydown (184)
(-) Perm Principal Paydown (185)
Leveraged CF (186): =SUM(K177:K185)
```

**Return Metrics:**
| Metric | Cell | Formula |
|--------|------|---------|
| Profit | I187 | `=I186` |
| Investment | I188 | `-SUMIF(K186:EN186,"<0")` |
| Multiple | I189 | `=I187/I188+1` |
| IRR | I190 | `=(1+IRR(K186:EN186,0.01))^12-1` |

---

## 5. Waterfall Sheet - Distribution Calculations

### 5.1 Structure Overview

The Waterfall sheet calculates LP/GP distributions through a **multi-hurdle promote structure**.

### 5.2 Equity Paydown Section (Rows 15-28)

**LP Equity (Rows 16-20):**
```excel
Equity Investment (18): =-K$11*$H18 (90% of total)
Equity Paydown (19): =-MIN(K$13*$H19,SUM(K17:K18))
Ending Balance (20): =SUM(K17:K19)
```

**Sponsor Equity (Rows 22-26):**
```excel
Equity Investment (24): =-K$11*$H24 (10% of total)
Equity Paydown (25): =-MIN(K$13*$H25,SUM(K23:K24))
Ending Balance (26): =SUM(K23:K25)
```

### 5.3 Hurdle I - 5% Preferred Return (Rows 30-52)

**LP Hurdle I (Rows 30-39):**
```excel
Beginning Balance (31): Previous ending
Accrual of Pref (32): =K31*$H32 (5% annual/12)
Equity Investment (33): =K18
Equity Account (34): =SUM(K31:K33)
Equity Paydown ROC (35): =K19
Paydown of Pref (36): =-MIN(SUM(K34:K35),K$28*$H36)
Ending Balance (37): =SUM(K34:K36)
LP Cash Flow (39): =-K33-SUM(K35:K36)
```

**Sponsor Hurdle I (Rows 41-48):** Mirror of LP structure

**Sponsor Promote (Row 50):**
```excel
=-(K36+K47)/SUM($H36+$H47)*$H50
```

### 5.4 Hurdle II (Rows 54-77)

Same structure as Hurdle I with:
- Cumulative pref tracking
- Incremental promote calculations

### 5.5 Hurdle III (Rows 81-106)

Same structure with third tier calculations.

### 5.6 Final Split (Rows 108-114)

```excel
LP Equity (111): =K$108*$G111
Sponsor Equity (112): =K$108*$G112
Sponsor Promote (113): =K$108*$G113
Total (114): =SUM(K111:K113)
```

### 5.7 LP Summary (Rows 116-126)

| Line | Row | Formula |
|------|-----|---------|
| Equity Investment | 117 | `=-K33` |
| Equity Paydown | 118 | `=-K86` |
| Hurdle I | 119 | `=-K87` |
| Hurdle II | 120 | `=-K88` |
| Hurdle III | 121 | `=-K89` |
| Final Split | 122 | `=K111` |
| **Net LP CF** | 123 | `=SUM(K117:K122)` |

### 5.8 Sponsor Summary (Rows 128-143)

Complete breakdown of sponsor returns including:
- Equity returns (ROC + Pref)
- Promote at each hurdle level
- Total sponsor cash flow

---

## 6. Debt Sheet - Amortization Schedules

### 6.1 Construction Loan Schedule (Rows 6-367)

**Header (Row 7):**
- Month (date)
- Month # (period number)
- Beginning Balance
- Payment
- Interest
- Amortization
- Principal Paydown
- Ending Balance

**Formulas:**
```excel
Date (B8): =INDEX(Model!$K$12:$EN$12,MATCH(C8,Model!$K$10:$EN$10))
Month # (C8): =Assumptions!L18+1
Beginning Balance (D8): =Assumptions!L12
Payment (E8): =-PMT(J8/12,$D$2*12,$D$8)
Interest (F8): =D8*J8/12
Amortization (G8): =E8-F8
Ending Balance (H8): =D8-G8
```

### 6.2 Perm Loan Schedule (Rows 6-367, Columns L-T)

Similar structure with:
- Different start date (post-construction)
- Different loan amount
- Separate amortization parameters

### 6.3 Interest Rate References

| Type | Cell | Value |
|------|------|-------|
| Construction Fixed | J3 | From Assumptions!J15 |
| Construction Floating | J4 | From Assumptions!K15 |
| SOFR Floor | J5 | From Assumptions!I15 |
| Perm Fixed | T3 | From Assumptions!J33 |
| Perm Floating | T4 | From Assumptions!K33 |

---

## 7. Supporting Sheets

### 7.1 SOFR Sheet

Contains **1-Month SOFR Forward Curve** data:
- Date range: 2026-01 through 2035+
- Rate data for floating rate calculations
- Monthly values for interest rate lookups

**Structure:**
```excel
Date (M column): Settlement dates
Rate (N column): Forward SOFR rates (e.g., 3.68%, 3.67%, etc.)
End of Month (O column): =EOMONTH(M3,0)
```

### 7.2 LCs Sheet (Lease Commissions)

Calculates broker commissions for new leases:

**Inputs:**
- SF: From rent roll
- $/PSF: Market rent
- Lease Term: From Assumptions
- LC % Years 1-5: 6.00%
- LC % Years 6+: 3.00%
- Leasing Override: Additional percentage

**Output:** Total commission per year over lease term

### 7.3 Comps Sheet

Market comparable data for:
- Rent comparables (new construction)
- Sale comparables
- Weighted averages for market assumptions

### 7.4 Info from Bill Sheet

Source data including:
- In-place rent roll details
- Historical operating expenses
- Key lease term summaries
- Due diligence notes

---

## 8. Key Formula Dependencies

### 8.1 Critical Cell References

```
Assumptions!C1 → Circular reference trigger (global)
Assumptions!L9 → Sale month (terminal period)
Assumptions!T7 → Stabilization month
Assumptions!C13 → Purchase price
Assumptions!L24 → Total loan proceeds
Assumptions!AA15 → Exit cap rate
```

### 8.2 Cross-Sheet Reference Map

```
Model → Assumptions (all inputs)
Model → Debt (amortization schedules)
Model → SOFR (interest rates)
Waterfall → Model (cash flows)
Waterfall → Assumptions (waterfall structure)
Debt → Assumptions (loan parameters)
Debt → Model (timeline)
LCs → Assumptions (lease terms)
```

---

# PART 2: PRODUCT REQUIREMENTS DOCUMENT (PRD)

## 1. Product Overview

### 1.1 Vision Statement

Build a modern, web-based real estate financial modeling application that replicates and enhances the functionality of the 225 Worth Ave Excel model, providing institutional-quality underwriting capabilities in a collaborative, cloud-native platform.

### 1.2 Target Users

1. **Real Estate Investment Professionals**
   - Acquisitions analysts
   - Asset managers
   - Portfolio managers

2. **Private Equity/Investment Firms**
   - Deal teams
   - Investment committees
   - Investor relations

3. **Lenders & Capital Providers**
   - Loan underwriters
   - Credit analysts

4. **Property Owners & Developers**
   - Development teams
   - Finance/accounting teams

### 1.3 Key Value Propositions

1. **Accuracy**: Excel-parity calculations with audit trails
2. **Collaboration**: Real-time multi-user editing
3. **Speed**: Instant scenario analysis
4. **Accessibility**: Browser-based, any device
5. **Integration**: API connectivity for data feeds
6. **Reporting**: Professional output generation

---

## 2. Functional Requirements

### 2.1 Core Modules

#### 2.1.1 Property Setup Module

**Features:**
- Property information input (address, SF, units)
- Multi-property portfolio support
- Property type templates (retail, office, multifamily, industrial)
- Custom field configuration

**Data Model:**
```typescript
interface Property {
  id: string;
  name: string;
  address: Address;
  propertyType: 'retail' | 'office' | 'multifamily' | 'industrial' | 'mixed';
  landSF: number;
  buildingSF: number;
  netRentableSF: number;
  yearBuilt: number;
  acquisitionDate: Date;
  metadata: Record<string, any>;
}
```

#### 2.1.2 Rent Roll Module

**Features:**
- Multi-tenant rent roll management
- Lease abstraction fields:
  - Tenant name, space identifier
  - Square footage (various measurement types)
  - Base rent (current and scheduled)
  - Rent escalations (%, fixed, CPI-linked)
  - Expense reimbursement structure (NNN, Modified Gross, Full Service)
  - Lease term (start, end, options)
  - Free rent periods
  - TI allowances
  - Commission structures
- Lease rollover projections
- Vacancy and absorption modeling
- Market rent assumptions by space type

**Data Model:**
```typescript
interface Lease {
  id: string;
  propertyId: string;
  tenantName: string;
  spaceId: string;
  rsf: number;
  baseRentPSF: number;
  annualEscalation: EscalationStructure;
  leaseStart: Date;
  leaseEnd: Date;
  options: LeaseOption[];
  freeRentMonths: number;
  tiAllowancePSF: number;
  lcPercentage: number;
  reimbursementType: 'NNN' | 'ModifiedGross' | 'FullService';
  recoveryPercentage: number;
}

interface EscalationStructure {
  type: 'percentage' | 'fixed' | 'cpi' | 'market';
  value: number;
  frequency: 'annual' | 'monthly' | 'lease_anniversary';
}
```

#### 2.1.3 Operating Assumptions Module

**Features:**
- Revenue assumptions:
  - Market rent by space type
  - Parking/storage income
  - Other income categories
  - Vacancy rate
  - Collection loss
  - Absorption/lease-up timing

- Expense assumptions:
  - Fixed operating expenses (per SF)
  - Variable operating expenses
  - Management fee (% of revenue)
  - Property taxes (millage rate or $ amount)
  - Insurance
  - Capital expenditure reserves
  - Custom expense categories

- Escalation factors:
  - Revenue growth rate
  - Expense growth rate
  - Property tax growth rate

**Data Model:**
```typescript
interface OperatingAssumptions {
  revenue: {
    marketRentPSF: number;
    parkingIncome: number;
    storageIncome: number;
    otherIncome: OtherIncomeItem[];
    vacancyRate: number;
    collectionLoss: number;
  };
  expenses: {
    fixedOpExPSF: number;
    variableOpExPSF: number;
    managementFeePercent: number;
    propertyTaxRate: number;
    insurancePSF: number;
    capExReservePSF: number;
    customExpenses: ExpenseItem[];
  };
  escalation: {
    revenueGrowth: number;
    expenseGrowth: number;
    propertyTaxGrowth: number;
  };
}
```

#### 2.1.4 Financing Module

**Features:**
- Multiple loan tranches support:
  - Construction/acquisition loan
  - Permanent loan
  - Mezzanine debt
  - Preferred equity

- Per-loan parameters:
  - Loan amount ($ or LTC/LTV)
  - Interest rate (fixed or floating)
  - Spread over index (SOFR, LIBOR, Prime)
  - Interest rate floor/cap
  - Loan fees and closing costs
  - Interest-only period
  - Amortization period
  - Maturity date
  - Prepayment penalties
  - Debt service coverage requirements

- Interest rate curves:
  - SOFR forward curve integration
  - Custom rate scenarios
  - Rate sensitivity analysis

**Data Model:**
```typescript
interface Loan {
  id: string;
  name: string;
  type: 'construction' | 'permanent' | 'mezzanine' | 'preferred_equity';
  amount: number;
  ltcRatio?: number;
  ltvRatio?: number;
  interestType: 'fixed' | 'floating';
  fixedRate?: number;
  floatingSpread?: number;
  indexType?: 'SOFR' | 'PRIME' | 'custom';
  rateFloor?: number;
  rateCap?: number;
  originationFee: number;
  closingCosts: number;
  ioMonths: number;
  amortizationYears: number;
  maturityMonths: number;
  startMonth: number;
}
```

#### 2.1.5 Exit Assumptions Module

**Features:**
- Exit timing (month/year)
- Exit cap rate by property type/segment
- Sales costs percentage
- Terminal value calculation methods:
  - Direct capitalization
  - Discounted cash flow
  - Per-unit pricing
  - Per-SF pricing
- Residual debt calculation
- Net proceeds calculation

**Data Model:**
```typescript
interface ExitAssumptions {
  saleMonth: number;
  exitCapRate: number;
  salesCostPercent: number;
  valuationMethod: 'direct_cap' | 'dcf' | 'per_unit' | 'per_sf';
  customExitValue?: number;
}
```

#### 2.1.6 Waterfall Distribution Module

**Features:**
- Flexible waterfall structure builder:
  - Unlimited hurdle tiers
  - Preferred return (pref) per tier
  - LP/GP split per tier
  - Promote calculations
  - Catch-up provisions
  - Clawback provisions

- Distribution timing:
  - Monthly/quarterly/annual
  - Compounding options
  - IRR-based hurdles vs. multiple-based

- Multiple investor classes:
  - LP (Limited Partners)
  - GP (General Partner)
  - Co-invest structures

**Data Model:**
```typescript
interface WaterfallStructure {
  lpSharePercent: number;
  gpSharePercent: number;
  compoundMonthly: boolean;
  hurdles: WaterfallHurdle[];
}

interface WaterfallHurdle {
  name: string;
  preferredReturn: number;
  lpSplit: number;
  gpSplit: number;
  promotePercent: number;
  hurdleType: 'irr' | 'multiple' | 'pref_accrual';
}
```

### 2.2 Calculation Engine

#### 2.2.1 Cash Flow Engine

**Requirements:**
- Monthly granularity for entire hold period (up to 30 years)
- Real-time recalculation on input changes
- Support for:
  - Revenue projections with escalations
  - Operating expense projections
  - NOI calculations
  - Debt service calculations
  - Capital event timing
  - Exit proceeds calculations

**Performance Requirements:**
- Full model recalculation: < 500ms
- Single input change update: < 100ms
- Support for 1000+ monthly periods

#### 2.2.2 IRR/NPV Calculator

**Features:**
- XIRR calculation (date-based)
- Standard IRR calculation (periodic)
- NPV at multiple discount rates
- Multiple calculation (equity multiple)
- Cash-on-cash return by period

**Formula Implementation:**
```typescript
function calculateXIRR(cashFlows: number[], dates: Date[]): number;
function calculateNPV(cashFlows: number[], discountRate: number): number;
function calculateMultiple(cashFlows: number[]): number;
function calculateCashOnCash(periodCF: number, equity: number): number;
```

#### 2.2.3 Amortization Calculator

**Features:**
- Full amortization schedule generation
- Support for:
  - Interest-only periods
  - Partial amortization
  - Balloon payments
  - Variable rates (monthly reset)
  - Mid-period draws

**Formula Implementation:**
```typescript
function calculatePayment(
  principal: number,
  annualRate: number,
  amortizationMonths: number
): number;

function generateAmortizationSchedule(
  loan: Loan,
  sofRCurve: RateCurve
): AmortizationRow[];
```

### 2.3 Output & Reporting Module

#### 2.3.1 Dashboard Views

**Executive Summary Dashboard:**
- Key returns metrics (IRR, Multiple, NPV)
- Sources and Uses summary
- Cash flow chart (waterfall)
- Sensitivity matrix
- LP/GP returns breakdown

**Cash Flow Dashboard:**
- Monthly/annual cash flow table
- Revenue breakdown chart
- Expense breakdown chart
- NOI trend line
- Debt service coverage trend

**Waterfall Dashboard:**
- Distribution by investor class
- Hurdle achievement timeline
- Promote earned by period
- Cumulative distributions

#### 2.3.2 Report Generation

**Report Types:**
1. **Investment Memo** (PDF)
   - Executive summary
   - Property overview
   - Financial projections
   - Risk factors
   - Appendices

2. **Offering Memorandum** (PDF)
   - Detailed property info
   - Market analysis
   - Financial model outputs
   - Investment structure

3. **Investor Reports** (PDF/Excel)
   - Period performance
   - Distribution history
   - Property updates
   - Valuation summary

4. **Lender Package** (PDF/Excel)
   - Property financials
   - Rent roll
   - Operating history
   - Debt coverage projections

#### 2.3.3 Data Export

**Formats:**
- Excel (.xlsx) with formulas preserved
- CSV for data integration
- PDF for presentations
- API/JSON for system integration

### 2.4 Scenario Analysis Module

#### 2.4.1 Scenario Management

**Features:**
- Create multiple scenarios per property
- Named scenarios (Base Case, Downside, Upside)
- Scenario comparison views
- Clone/duplicate scenarios
- Version history per scenario

#### 2.4.2 Sensitivity Analysis

**One-Way Sensitivity:**
- Variable selection (any input)
- Range definition (min, max, step)
- Output metric selection
- Table and chart output

**Two-Way Sensitivity:**
- Two variable selection
- Matrix output
- Heat map visualization
- Breakeven identification

**Monte Carlo Simulation:**
- Probability distributions for inputs
- 1000+ iteration runs
- Percentile outputs (10th, 50th, 90th)
- Distribution charts

### 2.5 Collaboration Features

#### 2.5.1 User Management

- Role-based access control:
  - Admin (full access)
  - Editor (modify models)
  - Viewer (read-only)
  - Commenter (view + comments)

- Team/organization structure
- Guest access with expiration

#### 2.5.2 Real-Time Collaboration

- Multi-user simultaneous editing
- Presence indicators
- Change attribution
- Conflict resolution
- Activity feed

#### 2.5.3 Comments & Annotations

- Cell-level comments
- @mentions
- Comment threads
- Resolution tracking

### 2.6 Data Integration Module

#### 2.6.1 Market Data Feeds

- Interest rate curves (SOFR, Treasury)
- Property market data (CoStar, CBRE)
- Economic indicators

#### 2.6.2 API Integrations

- Property management systems
- Accounting systems
- CRM systems
- Document management

---

## 3. Technical Requirements

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │Dashboard │  │Data Grid │  │  Charts  │  │  Forms   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │ REST/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway (Node.js)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   Auth   │  │  Models  │  │  Reports │  │  Export  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                  Calculation Engine (Rust/WASM)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Cash Flow│  │   IRR    │  │  Amort   │  │ Waterfall│        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │PostgreSQL│  │  Redis   │  │    S3    │  │Elasticsearch│     │
│  │ (Models) │  │ (Cache)  │  │ (Files)  │  │ (Search)   │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Frontend Requirements

**Technology Stack:**
- Framework: React 18+ with TypeScript
- State Management: Redux Toolkit or Zustand
- UI Components: Custom design system or MUI/Ant Design
- Data Grid: AG Grid or similar for spreadsheet-like experience
- Charts: D3.js or Recharts
- Real-time: Socket.io or WebSocket

**Key Features:**
- Spreadsheet-like data entry experience
- Formula bar with auto-complete
- Cell formatting and styling
- Undo/redo functionality
- Keyboard navigation
- Mobile-responsive design

### 3.3 Backend Requirements

**Technology Stack:**
- Runtime: Node.js 18+ or Bun
- Framework: Express.js, Fastify, or Hono
- Database: PostgreSQL 15+
- Cache: Redis
- Queue: BullMQ or similar
- Search: Elasticsearch

**API Design:**
- RESTful endpoints for CRUD operations
- WebSocket for real-time updates
- GraphQL optional for complex queries
- Rate limiting and throttling
- Request validation (Zod/Joi)

### 3.4 Calculation Engine Requirements

**Options:**
1. **WebAssembly (WASM)**
   - Rust or C++ compiled to WASM
   - Client-side calculation for responsiveness
   - Deterministic, auditable results

2. **Server-Side (Node.js)**
   - Financial calculation libraries
   - Server-side for complex scenarios
   - Caching for performance

**Critical Calculations:**
```typescript
// IRR using Newton-Raphson method
function calculateIRR(cashFlows: number[], guess = 0.1): number {
  const maxIterations = 100;
  const tolerance = 1e-7;
  let rate = guess;

  for (let i = 0; i < maxIterations; i++) {
    let npv = 0;
    let dnpv = 0;

    for (let j = 0; j < cashFlows.length; j++) {
      npv += cashFlows[j] / Math.pow(1 + rate, j);
      dnpv -= j * cashFlows[j] / Math.pow(1 + rate, j + 1);
    }

    const newRate = rate - npv / dnpv;
    if (Math.abs(newRate - rate) < tolerance) {
      return newRate;
    }
    rate = newRate;
  }

  return rate;
}

// XIRR with date-based cash flows
function calculateXIRR(
  cashFlows: number[],
  dates: Date[],
  guess = 0.1
): number {
  // Implementation using Newton-Raphson with day-count
}
```

### 3.5 Database Schema (Simplified)

```sql
-- Properties
CREATE TABLE properties (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  address JSONB,
  property_type VARCHAR(50),
  land_sf DECIMAL(15,2),
  building_sf DECIMAL(15,2),
  net_rentable_sf DECIMAL(15,2),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Scenarios
CREATE TABLE scenarios (
  id UUID PRIMARY KEY,
  property_id UUID REFERENCES properties(id),
  name VARCHAR(255) NOT NULL,
  is_base_case BOOLEAN DEFAULT FALSE,
  assumptions JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Leases
CREATE TABLE leases (
  id UUID PRIMARY KEY,
  property_id UUID REFERENCES properties(id),
  scenario_id UUID REFERENCES scenarios(id),
  tenant_name VARCHAR(255),
  space_id VARCHAR(50),
  rsf DECIMAL(15,2),
  base_rent_psf DECIMAL(15,2),
  escalation JSONB,
  lease_start DATE,
  lease_end DATE,
  options JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Loans
CREATE TABLE loans (
  id UUID PRIMARY KEY,
  scenario_id UUID REFERENCES scenarios(id),
  name VARCHAR(255),
  loan_type VARCHAR(50),
  amount DECIMAL(15,2),
  interest_type VARCHAR(20),
  rate DECIMAL(8,5),
  spread DECIMAL(8,5),
  io_months INTEGER,
  amort_years INTEGER,
  start_month INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Cash Flows (denormalized for performance)
CREATE TABLE cash_flows (
  id UUID PRIMARY KEY,
  scenario_id UUID REFERENCES scenarios(id),
  period INTEGER,
  period_date DATE,
  revenue DECIMAL(15,2),
  expenses DECIMAL(15,2),
  noi DECIMAL(15,2),
  debt_service DECIMAL(15,2),
  cash_flow DECIMAL(15,2),
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 3.6 Security Requirements

- Authentication: OAuth 2.0 / OIDC (Auth0, Cognito)
- Authorization: Role-based + resource-based
- Data encryption: At rest (AES-256) and in transit (TLS 1.3)
- Audit logging: All data changes tracked
- SOC 2 Type II compliance target
- GDPR compliance for EU users

### 3.7 Performance Requirements

| Metric | Target |
|--------|--------|
| Page Load (initial) | < 2s |
| Model Recalculation | < 500ms |
| API Response (p95) | < 200ms |
| Concurrent Users | 1000+ |
| Uptime | 99.9% |

---

## 4. User Interface Specifications

### 4.1 Navigation Structure

```
├── Dashboard
│   ├── Portfolio Overview
│   ├── Recent Models
│   └── Quick Actions
├── Properties
│   ├── Property List
│   ├── Property Detail
│   └── New Property
├── Models
│   ├── Model Editor
│   │   ├── Assumptions
│   │   ├── Rent Roll
│   │   ├── Financing
│   │   ├── Cash Flow
│   │   ├── Waterfall
│   │   └── Returns
│   ├── Scenarios
│   └── Sensitivity
├── Reports
│   ├── Generate Report
│   ├── Report Templates
│   └── Export
├── Settings
│   ├── Profile
│   ├── Team
│   ├── Integrations
│   └── Preferences
└── Help
    ├── Documentation
    ├── Tutorials
    └── Support
```

### 4.2 Key Screen Wireframes

#### Assumptions Screen
```
┌────────────────────────────────────────────────────────────────┐
│ [Property Name] > Assumptions                    [Save] [Reset]│
├────────────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│ │ Timing       │ │ Revenue      │ │ Financing    │            │
│ └──────────────┘ └──────────────┘ └──────────────┘            │
│                                                                │
│ Project Timing                        Operating Assumptions    │
│ ┌─────────────────────────────────┐  ┌─────────────────────── │
│ │ Acquisition Date: [03/31/2026] │  │ Market Rent: [$300/SF] │
│ │ Hold Period:      [120 months] │  │ Vacancy:     [0%]      │
│ │ Stabilization:    [77 months]  │  │ Mgmt Fee:    [4%]      │
│ └─────────────────────────────────┘  │ OpEx:        [$36/SF]  │
│                                       └───────────────────────│
│ Financing                             Exit Assumptions         │
│ ┌─────────────────────────────────┐  ┌───────────────────────│
│ │ LTC:          [55.5%]          │  │ Exit Cap:   [5.00%]   │
│ │ Interest:     [5.00%]          │  │ Sale Costs: [1.00%]   │
│ │ I/O Period:   [120 months]     │  └───────────────────────│
│ │ Amort:        [30 years]       │                           │
│ └─────────────────────────────────┘                           │
└────────────────────────────────────────────────────────────────┘
```

#### Cash Flow Screen
```
┌────────────────────────────────────────────────────────────────┐
│ [Property Name] > Cash Flow                [Annual] [Monthly] │
├────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────┐  │
│ │                    [Cash Flow Chart]                      │  │
│ │  $2M ┤                                           ▓▓▓     │  │
│ │      │                                     ▓▓▓▓▓         │  │
│ │  $1M ┤                               ▓▓▓▓▓               │  │
│ │      │                         ▓▓▓▓▓▓                    │  │
│ │   $0 ┼────────────────────────────────────────────────── │  │
│ │      │ ████                                              │  │
│ │ -$1M ┤ ████                                              │  │
│ │      └──────────────────────────────────────────────────  │  │
│ │        Y1   Y2   Y3   Y4   Y5   Y6   Y7   Y8   Y9   Y10  │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                                │
│ │  Year  │ Revenue │ OpEx   │  NOI   │  DS    │   CF   │     │
│ ├────────┼─────────┼────────┼────────┼────────┼────────┤     │
│ │   1    │ $2,034K │ $1,234K│ $800K  │ $950K  │ -$150K │     │
│ │   2    │ $2,145K │ $1,267K│ $878K  │ $950K  │ -$72K  │     │
│ │   3    │ $2,259K │ $1,301K│ $958K  │ $950K  │  $8K   │     │
│ │  ...   │   ...   │  ...   │  ...   │  ...   │  ...   │     │
└────────────────────────────────────────────────────────────────┘
```

### 4.3 Component Library Requirements

**Input Components:**
- Numeric input with formatting (currency, percentage)
- Date picker with fiscal year support
- Dropdown with search
- Toggle switches
- Slider inputs for sensitivity

**Data Display:**
- Sortable, filterable data tables
- Editable grid cells (spreadsheet-like)
- Sparkline charts
- KPI cards
- Progress indicators

**Feedback:**
- Toast notifications
- Validation messages
- Loading states
- Error boundaries

---

## 5. Implementation Phases

### Phase 1: Foundation (Months 1-3)
- Core architecture setup
- Authentication/authorization
- Basic property management
- Simple rent roll
- Basic cash flow calculations

### Phase 2: Core Features (Months 4-6)
- Complete assumptions module
- Full financing module
- Debt amortization schedules
- Unleveraged returns

### Phase 3: Advanced Features (Months 7-9)
- Waterfall distributions
- Leveraged returns
- Scenario management
- Sensitivity analysis

### Phase 4: Collaboration & Reporting (Months 10-12)
- Real-time collaboration
- Report generation
- Data export
- API integrations

### Phase 5: Enhancement (Months 13+)
- Monte Carlo simulation
- Market data integrations
- Mobile optimization
- Advanced analytics

---

## 6. Success Metrics

### 6.1 User Engagement
- Daily active users
- Models created per user
- Time spent in application
- Feature adoption rates

### 6.2 Performance
- Calculation accuracy (100% match to Excel)
- Page load times
- API response times
- Error rates

### 6.3 Business
- User acquisition
- Conversion rate (trial to paid)
- Customer retention
- Net Promoter Score (NPS)

---

## 7. Excel Parity Specification

This section provides the exact values from the source Excel model for validation and testing purposes. The web application must produce identical results to be considered accurate.

### 7.1 Benchmark Input Values

All monetary values are in thousands ($000s) unless otherwise noted.

#### Property Information
| Parameter | Excel Cell | Value |
|-----------|------------|-------|
| Land SF | F7 | 12,502 |
| Building RSF | F8 | 9,932 |

#### Acquisition & Timing
| Parameter | Excel Cell | Value |
|-----------|------------|-------|
| Purchase Price | C13 | 41,500 ($000s) |
| Closing Costs | C14 | 500 ($000s) |
| Total Acquisition Cost | L22 | 42,342.96 ($000s) |
| Hold Period | L9 | 120 months |
| Stabilization Month | T7 | 77 |
| Sale Month | X13 | 120 |

#### Debt Structure
| Parameter | Excel Cell | Value |
|-----------|------------|-------|
| LTC % | L23 | 40.0% |
| Loan Amount | L24 | 16,937.18 ($000s) |
| Fixed/Floating | L14 | 0 (Fixed) |
| Interest Rate | J15 | 5.25% |
| I/O Period | L18 | 120 months |
| Amortization Period | L19 | 30 years |

#### Equity Structure
| Parameter | Calculation | Value |
|-----------|-------------|-------|
| Total Equity | L22 - L24 | 25,405.78 ($000s) |
| LP Equity (90%) | Total × 0.90 | 22,865.20 ($000s) |
| GP Equity (10%) | Total × 0.10 | 2,540.58 ($000s) |

#### Rent Roll (Per-Tenant Detail)
| Tenant | RSF | In-Place PSF | Market PSF | Lease End Month |
|--------|-----|--------------|------------|-----------------|
| Peter Millar (G/Fore) | 2,300 | $201.45 | $300.00 | Month 69 |
| J McLaughlin | 1,868 | $200.47 | $300.00 | Month 50 |
| Gucci | 5,950 | $187.65 | $300.00 | Month 210 |
| **Total** | **10,118** | **$193.15** | **$300.00** | - |

**CRITICAL**: The Excel model calculates rent on a **tenant-by-tenant** basis with:
- In-place rent until lease expiration
- Rollover to market rent at lease expiration
- Annual escalation of 2.5%

#### Operating Assumptions
| Parameter | Excel Cell | Value |
|-----------|------------|-------|
| Market Rent PSF | T39 | $300/SF/year |
| Rent Growth | D2 (Model) | 2.5% annual |
| Expense Growth | D3 (Model) | 2.5% annual |
| Fixed OpEx PSF | T54 | $36.00/SF |
| Management Fee | T56 | 4% of revenue |
| Property Tax Millage | S57 | 1.5% of purchase price |
| Property Tax Annual | Calculated | $622,500 |
| CapEx Reserve PSF | T59 | $5.00/SF |
| General Vacancy | T51 | 0% |
| Collection Loss | T52 | 0% |

#### Exit Assumptions
| Parameter | Excel Cell | Value |
|-----------|------------|-------|
| Exit Cap Rate | AA15 | 5.00% |
| Sales Costs | Z17 | 1.00% |
| Forward NOI (at exit) | AA14 | 3,079.84 ($000s) |
| Gross Exit Value | AA16 | 61,596.78 ($000s) |
| Net Exit Proceeds | AA18 | 60,980.82 ($000s) |

#### Waterfall Structure
| Tier | Pref Return | LP Split | GP Split | GP Promote |
|------|-------------|----------|----------|------------|
| Equity Split | - | 90% | 10% | - |
| Hurdle I | 5% | 90% | 10% | 0% |
| Hurdle II | 5% | 75% | 8.33% | 16.67% |
| Hurdle III | 5% | 75% | 8.33% | 16.67% |
| Final Split | - | 75% | 8.33% | 16.67% |
| Compound Monthly | - | No (0) | - | - |

### 7.2 Benchmark Output Values (Expected Results)

These are the exact values the web application must produce to achieve parity.

#### Unleveraged Returns
| Metric | Excel Cell | Value |
|--------|------------|-------|
| Profit | I82 | 42,252.65 ($000s) |
| Investment | I83 | 42,004.22 ($000s) |
| Multiple | I84 | 2.01x |
| IRR | I85 | **8.57%** |

#### Leveraged Returns
| Metric | Excel Cell | Value |
|--------|------------|-------|
| Profit | I187 | 33,014.57 ($000s) |
| Investment | I188 | 25,405.78 ($000s) |
| Multiple | I189 | 2.30x |
| IRR | I190 | **10.09%** |

#### LP Returns (from Waterfall)
| Metric | Excel Cell | Value |
|--------|------------|-------|
| Investment | I124 | 22,865.20 ($000s) |
| Total Return | I123 | 26,639.96 ($000s) |
| Multiple | I125 | 2.17x |
| IRR | I126 | **9.39%** |

#### GP Returns (from Waterfall)
| Metric | Excel Cell | Value |
|--------|------------|-------|
| Investment | I140 | 2,540.58 ($000s) |
| Total Return | I139 | 6,374.62 ($000s) |
| Multiple | I142 | 3.51x |
| IRR | I141 | **15.02%** |

### 7.3 Benchmark Intermediate Values

Use these values to validate intermediate calculations.

#### Month 2 (First Operating Month) Values
| Item | Excel Cell | Value ($000s) |
|------|------------|---------------|
| Space A Revenue | L46 | 38.69 |
| Space B Revenue | L47 | 31.27 |
| Space C Revenue | L48 | 93.24 |
| Total Revenue | L56 | 261.09 |
| Fixed OpEx | L61 | 30.42 |
| Management Fee | L64 | 10.44 |
| Property Taxes | L65 | 51.88 |
| CapEx Reserve | L66 | 4.22 |
| Total OpEx | L67 | 102.12 |
| NOI | L72 | 158.97 |
| Interest Expense | L122 | 73.09 |
| Debt Service | L123 | 73.09 |
| Unleveraged CF | L81 | 158.97 |
| Leveraged CF | L186 | 85.89 |

#### Month 120 (Exit Month) Values
| Item | Excel Cell | Value ($000s) |
|------|------------|---------------|
| NOI | EA72 | 247.80 |
| Exit Proceeds | EA74 | 60,980.82 |
| Unleveraged CF | EA81 | 61,228.62 |
| Leveraged CF | EA186 | 44,215.91 |

#### Annual Totals
| Item | Value ($000s) |
|------|---------------|
| Year 1 NOI | 1,762.83 |
| Total 10-Year NOI | 23,271.83 |
| Total Unleveraged CF | 42,252.65 |
| Total Leveraged CF | 33,014.57 |

### 7.4 Key Implementation Gaps

The following items require implementation changes to achieve Excel parity:

#### 1. Tenant-by-Tenant Rent Calculation
**Current**: Uniform rent calculation using weighted average
**Required**: Per-tenant calculation with:
- Individual in-place rents
- Individual lease expiration dates
- Rollover to market rent at expiration
- Monthly escalation factor: `(1 + 0.025)^(month/12)`

#### 2. Debt Calculation (LTC)
**Current**: May use incorrect base for LTC calculation
**Required**: LTC = 40% of Total Acquisition Cost ($42,342.96K)
- Loan Amount = $16,937.18K
- Interest = 5.25% (not 5.00%)
- Full I/O for 120 months

#### 3. Property Tax Calculation
**Current**: May use direct input
**Required**: Property Tax = Purchase Price × 1.5% = $41,500K × 0.015 = $622.5K/year

#### 4. Exit Value Calculation
**Current**: Simple forward NOI / cap rate
**Required**: Forward 12-month NOI at month 120 = $3,079.84K
- Gross Value = $61,596.78K
- Net Proceeds = Gross × (1 - 1%) = $60,980.82K

### 7.5 Tolerance Thresholds for Parity Testing

| Metric | Acceptable Variance |
|--------|---------------------|
| IRR | ± 0.30% (30 basis points) |
| Multiple | ± 0.01x |
| Cash Flows | ± 0.1% or $1K |
| NOI | ± $0.5K or 0.1% |

---

## 8. Appendix

### 8.1 Glossary

| Term | Definition |
|------|------------|
| **NOI** | Net Operating Income - Revenue minus operating expenses |
| **IRR** | Internal Rate of Return - Discount rate that makes NPV = 0 |
| **LTC** | Loan-to-Cost - Loan amount as percentage of total project cost |
| **LTV** | Loan-to-Value - Loan amount as percentage of property value |
| **SOFR** | Secured Overnight Financing Rate - Benchmark interest rate |
| **TI** | Tenant Improvements - Build-out costs for tenant spaces |
| **LC** | Leasing Commission - Broker fees for securing leases |
| **NNN** | Triple Net - Tenant pays property taxes, insurance, and maintenance |
| **Waterfall** | Distribution structure defining order and splits of returns |
| **Promote** | GP's share of profits above preferred return hurdles |
| **Pref** | Preferred Return - Minimum return to investors before profit split |

### 8.2 Formula Reference

**Monthly Rent Calculation:**
```
Monthly_Rent = RSF × Annual_Rent_PSF × Escalation_Factor / 12 / 1000
```

**NOI Calculation:**
```
NOI = Effective_Revenue - Total_Operating_Expenses
```

**Debt Service:**
```
Monthly_Payment = PMT(Annual_Rate/12, Amort_Months, Principal)
Interest = Beginning_Balance × Annual_Rate / 12
Principal = Payment - Interest
```

**Exit Value:**
```
Exit_Value = Forward_12_NOI / Exit_Cap_Rate
Net_Proceeds = Exit_Value × (1 - Sales_Cost_%)
```

**IRR (Newton-Raphson):**
```
NPV(r) = Σ CF_t / (1+r)^t = 0
Solve for r iteratively
```

### 8.3 Sample API Endpoints

```
GET    /api/v1/properties
POST   /api/v1/properties
GET    /api/v1/properties/:id
PUT    /api/v1/properties/:id
DELETE /api/v1/properties/:id

GET    /api/v1/properties/:id/scenarios
POST   /api/v1/properties/:id/scenarios
GET    /api/v1/scenarios/:id
PUT    /api/v1/scenarios/:id

GET    /api/v1/scenarios/:id/cashflows
POST   /api/v1/scenarios/:id/calculate
GET    /api/v1/scenarios/:id/returns

POST   /api/v1/scenarios/:id/export/excel
POST   /api/v1/scenarios/:id/export/pdf
```

---

*Document Version: 1.0*
*Created: January 2026*
*Model Source: 225 Worth Ave_Model.xlsx*

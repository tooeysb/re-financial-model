# Excel Formula Analysis - Complete Parity Reference

## Overview

This document provides the exact Excel formulas extracted from `225 Worth Ave_Model(revised).xlsx` for achieving 100% calculation parity. All formulas have been traced directly from the source workbook.

**Analysis Date:** 2026-01-17
**Source File:** `/Users/tooeycourtemanche/Desktop/Models XLS/225 Worth Ave_Model(revised).xlsx`

---

## 1. ESCALATION FACTORS (Critical Difference!)

### 1.1 Rent Escalation (Row 2) - MONTHLY COMPOUNDING

```excel
Formula: L2 = K2 * (1 + $D$2/12)

Where:
  D2 = Annual growth rate (0.025 = 2.5%)
  K2 = Previous month's factor (starts at 1)

Calculation: Each month multiplied by (1 + 0.025/12) = 1.002083333...

Result after 12 months: 1.0252884570 (≈2.53% growth due to compounding)
```

### 1.2 Expense Escalation (Row 3) - ANNUAL RATE APPLIED MONTHLY

```excel
Formula: L3 = K3 * (1 + $D3)^(1/12)

Where:
  D3 = Annual growth rate (0.025 = 2.5%)
  K3 = Previous month's factor (starts at 1)

Calculation: Each month multiplied by (1.025)^(1/12) = 1.002059836...

Result after 12 months: 1.0250000000 (EXACTLY 2.5% growth by design)
```

### 1.3 Comparison Table

| Month | Rent Factor | Expense Factor | Difference |
|-------|-------------|----------------|------------|
| 0 | 1.0000000000 | 1.0000000000 | 0.0000000000 |
| 1 | 1.0020833333 | 1.0020598363 | 0.0000234971 |
| 12 | 1.0252884570 | 1.0250000000 | 0.0002884570 |
| 24 | 1.0512164200 | 1.0506250000 | 0.0005914200 |
| 36 | 1.0778000612 | 1.0768906250 | 0.0009094362 |

**Python Implementation Required:**
```python
# RENT escalation (monthly compounding)
rent_factor = (1 + annual_rate / 12) ** period

# EXPENSE escalation (annual rate applied monthly)
expense_factor = (1 + annual_rate) ** (period / 12)
```

---

## 2. REVENUE CALCULATIONS (Model Sheet Rows 46-51)

### 2.1 Retail Revenue by Tenant (Rows 46-48)

**Row 46 (Peter Millar) - NO TI buildout wait:**
```excel
K46 = IF(K$10=0, 0,
         IF(K$10<=$F46,
            $E46*$G46*Model!K$2/12/1000,           -- In-place rent
            IF(K$10>$F46,
               Model!$E46*Model!$H46*Model!K$2/12/1000,  -- Market rent
               0)))

Where:
  K$10 = Current month number
  $F46 = Lease end month (69 for Peter Millar)
  $E46 = RSF (2,300)
  $G46 = In-place rent PSF ($201.45)
  $H46 = Market rent PSF ($300)
  K$2 = Rent escalation factor
```

**Rows 47-48 (J McLaughlin, Gucci) - WITH TI buildout wait:**
```excel
K47 = IF(K$10=0, 0,
         IF(K$10<=$F47,
            $E47*$G47*Model!K$2/12/1000,           -- In-place rent
            IF(K$10>$F47+Assumptions!$T$49,        -- NOTE: +TI buildout period!
               Model!$E47*Model!$H47*Model!K$2/12/1000,  -- Market rent
               0)))                                 -- Zero during TI buildout

Where:
  Assumptions!$T$49 = TI Buildout Period (6 months)
```

**CRITICAL:** Revenue formula includes TI buildout gap. During months (F47+1) through (F47+T49), revenue = $0.

### 2.2 Free Rent Deductions (Rows 49-51)

**Row 50 (J McLaughlin Free Rent):**
```excel
E50 = F47 + Assumptions!$T$49 + 1   -- Free rent START month (57)
F50 = Assumptions!$T$50              -- Free rent duration (10 months)
G50 = E50 + F50                      -- Free rent END month (67)
H50 = 0                              -- Flag: 0=Apply free rent, 1=No free rent

K50 = IF(AND(K$10 < $G50, K$10 >= $E50, $H50 = 0), -K47, 0)

Where:
  Condition: Month is within free rent period AND H50=0
  Result: NEGATIVE of calculated rent (deduction line)
```

**Timeline for J McLaughlin (F47=50):**
- Month 50: Last in-place rent ($34.63K)
- Month 51-56: TI buildout (Revenue = $0, Free Rent = $0)
- Month 57-66: Market rent calculated ($52.58K-$53.58K), Free Rent = negative amount
- Month 67+: Market rent paid ($53.69K+), Free Rent = $0

**Actual Excel Values:**
```
Month 49: Revenue=$34.56K, FreeRent=$0
Month 50: Revenue=$34.63K, FreeRent=$0
Month 51: Revenue=$0,      FreeRent=$0  (TI buildout)
Month 56: Revenue=$0,      FreeRent=$0  (TI buildout)
Month 57: Revenue=$52.58K, FreeRent=-$52.58K (net=$0)
Month 66: Revenue=$53.58K, FreeRent=-$53.58K (net=$0)
Month 67: Revenue=$53.69K, FreeRent=$0  (paying rent!)
```

---

## 3. TI/LC COSTS (Model Sheet Rows 33-38)

### 3.1 TI Costs (Rows 33-35)

```excel
E33 = Assumptions!$D$38              -- TI Toggle (0=OFF, 1=ON) - Currently 0!
F33 = IF(H49=1, 0, Assumptions!$E$38) -- TI per SF if H49=0 ($150)
G33 = E49                             -- Month applied (= free rent start)

K33 = IF($E33=0, 0,                  -- If TI toggle OFF, $0
         IF(K$10=$G33,               -- If current month = TI month
            $F33*$E46*K$2/1000,      -- TI = PSF × RSF × escalation
            0))

Calculation: TI = $150 × 2,300 × 1.126 / 1000 = $388.47K
```

### 3.2 LC Costs (Rows 36-38)

```excel
F36 = IF(H49=1, 0, Assumptions!$E$39) -- LC per SF if H49=0
G36 = G33                              -- Same month as TI

K36 = IF(K$10=$G36, $F36*$E46*K$2/1000, 0)
```

**IMPORTANT:** In current model, both TI (D38=0) and LC (E39=$0) are DISABLED!

### 3.3 H-Column Flags

| Row | Tenant | H Flag | Meaning |
|-----|--------|--------|---------|
| 49 | Peter Millar | 1 | NO free rent, NO TI/LC at rollover |
| 50 | J McLaughlin | 0 | HAS free rent, HAS TI/LC at rollover |
| 51 | Gucci | 0 | HAS free rent, HAS TI/LC at rollover |

---

## 4. OPERATING EXPENSES (Model Sheet Rows 61-66)

### 4.1 Fixed OpEx (Row 61)
```excel
F61 = Assumptions!T54                -- $36.00/SF
K61 = IF(K$10=0, 0, $F61 * SUM($E$46:$E$48) / 12 / 1000 * K$3)

Month 1 value: $30.42K
```

### 4.2 Variable OpEx (Row 62)
```excel
F62 = Assumptions!T55                -- Formula from detailed expenses
K62 = IF(K$10=0, 0, $F62 * SUM($E$46:$E$48) / 12 / 1000 * K$3)

Month 1 value: $5.16K
```

### 4.3 Management Fee (Row 64)
```excel
F64 = Assumptions!T56                -- 4%
K64 = IF(Assumptions!$C$1=0, 0, $F64 * K59)

Month 1 value: $10.44K (4% of effective revenue)
```

### 4.4 Property Tax (Row 65) - ANNUAL BUMPS ONLY
```excel
F65 = Assumptions!T57                -- Annual tax amount
K65 = IF(Assumptions!$C$1=0, 0,
         IF(AND(K$10 < $G65+12, K$10 >= $G65),
            $F65/12,                 -- First year: simple monthly
            IF(MOD(K$10-$G65, 12)=0,
               J65*(1+$F4),          -- Annual anniversary: apply escalation
               J65)))                -- Other months: same as previous

Month 1 value: $51.88K
```

### 4.5 CapEx Reserve (Row 66)
```excel
F66 = Assumptions!T59                -- $5.00/SF
K66 = $F66 * SUM($E$46:$E$48) * K$3 / 1000 / 12

Note: This uses expense escalation factor (K$3), not rent factor!
Month 1 value: $4.22K
```

---

## 5. EXPENSE REIMBURSEMENTS (NNN)

### 5.1 Fixed Reimbursements (Row 54)
```excel
K54 = SUM(K61, K65)   -- Fixed OpEx + Property Tax

Month 1: $30.42 + $51.88 = $82.29K
```

### 5.2 Variable Reimbursements (Row 55)
```excel
K55 = SUM(K62:K64)    -- Variable OpEx + Parking Expense + Management Fee

Month 1: $5.16 + $0 + $10.44 = $15.60K
```

---

## 6. DEBT SERVICE (Model Sheet Rows 113-127)

### 6.1 Interest Rate Determination (Rows 114-116)

```excel
Row 114 (SOFR lookup):
K114 = MAX(LOOKUP(K$113, SOFR!$O$3:$O$123, SOFR!$N$3:$N$123), $E114)

Row 115 (Spread):
K115 = IF($G114=1, Assumptions!$K$15/10000, Assumptions!$J$15)
     = 0.0525 (fixed rate)

Row 116 (Effective Rate):
K116 = IF($G$114=1, SUM(K114:K115), K115)
     = 0.0525 (fixed, not floating)
```

### 6.2 Interest Calculation (Row 122) - USES AVERAGE BALANCE!

```excel
L122 = IF(Assumptions!$C$1=0, 0,
          AVERAGE(L119, L119+L120) * L116 * (L12-K12) / 365)

Where:
  L119 = Beginning balance ($16,937.18K)
  L120 = Draws ($0 during I/O)
  L116 = Interest rate (0.0525)
  (L12-K12) = Days in month (30 for April 2026)

Calculation:
  AVERAGE(16937.18, 16937.18+0) × 0.0525 × 30/365
  = 16937.18 × 0.0525 × 0.08219...
  = $73.09K
```

**CRITICAL:** Excel uses AVERAGE of beginning and ending balance for interest calculation!

---

## 7. LCs SHEET - YEAR-BY-YEAR CALCULATION

### 7.1 Input Parameters

| Cell | Value | Description |
|------|-------|-------------|
| D3 | 2,300 | RSF (references Assumptions) |
| D4 | $25.00 | Monthly rent PSF |
| D6 | 10 | Months abated (free rent) |
| D8 | 10 | Lease term (years) |
| D9 | 0.025 | Annual growth rate |
| D10 | 0.06 | LC % Years 1-5 |
| D11 | 0.03 | LC % Years 6+ |

### 7.2 Year-by-Year Calculation

```excel
Year N Annual Rent:
D17 = IF(B17>D8, 0, D16*(1+D9)^(B17-1))

Net Rent (after free rent):
G16 = IF(D5=1, D16*((12-E16)/12), D16-F16)

LC Amount:
I16 = G16 * H16  (where H16 = LC rate for that year)
```

### 7.3 Actual Values

| Year | Annual Rent | Net Rent | LC% | LC $ |
|------|-------------|----------|-----|------|
| 1 | $690,000 | $115,000 | 6% | $6,900 |
| 2 | $707,250 | $707,250 | 6% | $42,435 |
| 3 | $724,931 | $724,931 | 6% | $43,496 |
| 4 | $743,055 | $743,055 | 6% | $44,583 |
| 5 | $761,631 | $761,631 | 6% | $45,698 |
| 6 | $780,672 | $780,672 | 3% | $23,420 |
| 7 | $800,188 | $800,188 | 3% | $24,006 |
| 8 | $820,193 | $820,193 | 3% | $24,606 |
| 9 | $840,698 | $840,698 | 3% | $25,221 |
| 10 | $861,715 | $861,715 | 3% | $25,851 |
| **TOTAL** | | | | **$306,216** |

**Total LC PSF: $133.14**

---

## 8. BENCHMARK VALUES (Month 1)

| Item | Excel Value | Notes |
|------|-------------|-------|
| Space A Revenue | $38.69K | Peter Millar |
| Space B Revenue | $31.27K | J McLaughlin |
| Space C Revenue | $93.24K | Gucci |
| Total Potential Revenue | $261.09K | |
| Fixed OpEx | $30.42K | |
| Variable OpEx | $5.16K | |
| Management Fee | $10.44K | |
| Property Tax | $51.88K | |
| CapEx Reserve | $4.22K | |
| Total OpEx | $102.12K | |
| NOI | $158.97K | |
| Interest | $73.09K | |
| Unleveraged CF | $158.97K | |
| Leveraged CF | $85.89K | |

---

## 9. REQUIRED PYTHON IMPLEMENTATION CHANGES

### 9.1 Escalation Factor Functions

```python
def calculate_rent_escalation(annual_rate: float, period: int) -> float:
    """Monthly compounding: (1 + rate/12)^period"""
    return (1 + annual_rate / 12) ** period

def calculate_expense_escalation(annual_rate: float, period: int) -> float:
    """Annual rate applied monthly: (1 + rate)^(period/12)"""
    return (1 + annual_rate) ** (period / 12)
```

### 9.2 Free Rent as Deduction Line

```python
# Calculate market rent even during free rent period
market_rent = rsf * market_rent_psf * escalation / 12 / 1000

# Free rent is a SEPARATE deduction line (not just zero revenue)
if is_free_rent_period:
    free_rent_deduction = -market_rent
else:
    free_rent_deduction = 0

# Net revenue = market_rent + free_rent_deduction
```

### 9.3 Interest with Average Balance

```python
def calculate_interest(
    beginning_balance: float,
    draws: float,
    rate: float,
    days_in_month: int
) -> float:
    """Excel uses AVERAGE of beginning and ending balance"""
    avg_balance = (beginning_balance + beginning_balance + draws) / 2
    return avg_balance * rate * days_in_month / 365
```

### 9.4 LC Year-by-Year Calculation

```python
def calculate_lease_commission_excel(
    rsf: float,
    annual_rent_year1: float,
    growth_rate: float,
    lease_term_years: int,
    free_rent_months: int,
    lc_pct_years_1_5: float = 0.06,
    lc_pct_years_6_plus: float = 0.03
) -> float:
    """Exact Excel LCs sheet calculation"""
    total_lc = 0
    for year in range(1, lease_term_years + 1):
        # Year-by-year escalated rent
        annual_rent = annual_rent_year1 * (1 + growth_rate) ** (year - 1)

        # Year 1: Deduct free rent months
        if year == 1:
            net_rent = annual_rent * (12 - free_rent_months) / 12
        else:
            net_rent = annual_rent

        # LC rate based on year
        lc_rate = lc_pct_years_1_5 if year <= 5 else lc_pct_years_6_plus
        total_lc += net_rent * lc_rate

    return total_lc
```

---

## 10. TENANT FLAG SYSTEM

Each tenant needs a flag (H column equivalent) indicating:
- `apply_rollover_costs`: If True, apply TI/LC/Free Rent at lease expiry
- Peter Millar: False (H49=1)
- J McLaughlin: True (H50=0)
- Gucci: True (H51=0)

This affects:
1. Whether TI buildout gap applies to revenue
2. Whether free rent deduction applies
3. Whether TI/LC costs are incurred at rollover

---

## Document Version
- Created: 2026-01-17
- Last Updated: 2026-01-17
- Author: Claude (Opus 4.5)

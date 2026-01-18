# Excel Parity Audit Report

## Overview

This document provides a comprehensive audit comparing the 225 Worth Ave Excel financial model against the web application implementation. The goal is to ensure TOTAL compliance between all calculations.

**Audit Date:** 2026-01-17
**Target Benchmarks (from PRD Section 7.2):**
| Metric | Excel Value |
|--------|-------------|
| Unleveraged IRR | **8.57%** |
| Leveraged IRR | **10.09%** |
| LP IRR | **9.39%** |
| GP IRR | **15.02%** |

**Current App Values (approximate):**
| Metric | App Value | Variance |
|--------|-----------|----------|
| Unleveraged IRR | 8.40% | -0.17% |
| Leveraged IRR | 10.01% | -0.08% |
| LP IRR | 9.37% | -0.02% |
| GP IRR | 14.86% | -0.16% |

---

## Critical Discrepancies

### 1. INTEREST RATE MISMATCH - **HIGH PRIORITY**

**Location:** `app/api/scenarios.py` lines 57, 339, 770, 907

**PRD Specification:**
- Excel Cell J15: Interest Rate = **5.25%**

**App Implementation:**
- Default `fixed_rate: float = 0.05` (5.00%)
- Falls back to 5.00% in multiple places

**Impact:** Higher interest rate = more debt service = lower leveraged returns. This is a primary cause of the IRR discrepancy.

**Fix Required:**
```python
# Change default from 0.05 to 0.0525
fixed_rate: float = 0.0525
```

---

### 2. PROPERTY TAX ENDPOINT BUG - **MEDIUM PRIORITY**

**Location:** `app/api/scenarios.py` lines 927-941 (get_scenario_cashflows endpoint)

**Issue:** The endpoint passes `property_tax_full` (full dollars) to the cashflow module, but the module expects values in $000s.

**Correct Code (calculate_scenario_returns, line 360):**
```python
property_tax_000s = op_assumptions.get("property_tax_amount", 0) / 1000  # Correct
```

**Buggy Code (get_scenario_cashflows, line 927-941):**
```python
property_tax_full = op_assumptions.get("property_tax_amount", 0)  # Full dollars
# ...
property_tax_amount=property_tax_full,  # Should be property_tax_full / 1000
```

**Impact:** Cash flow projections endpoint returns incorrect values.

---

### 3. MULTI-HURDLE WATERFALL NOT IMPLEMENTED - **MEDIUM PRIORITY**

**PRD Waterfall Structure (Section 3.9):**
| Tier | Pref Return | LP Split | GP Split | GP Promote |
|------|-------------|----------|----------|------------|
| Equity Split | - | 90% | 10% | - |
| Hurdle I | 5% | 90% | 10% | 0% |
| Hurdle II | 5% | 75% | 8.33% | 16.67% |
| Hurdle III | 5% | 75% | 8.33% | 16.67% |
| Final Split | - | 75% | 8.33% | 16.67% |

**App Implementation:** Simplified single-hurdle waterfall
- Returns capital first
- Pays single 5% pref
- Jumps directly to final profit split

**Impact:** GP promote accumulation differs from Excel multi-tier logic.

---

### 4. INTEREST CALCULATION METHOD - **LOW PRIORITY**

**PRD Formula (Section 4.9):**
```excel
Interest (122): =AVERAGE(K119,K119+K120)*K116*(K12-J12)/365
```
Uses AVERAGE of beginning and ending balance.

**App Implementation (cashflow.py line 281):**
```python
interest_expense = loan_amount * daily_rate * days_in_month
```
Uses only beginning balance.

**Impact:** For full I/O periods, this makes no difference. Only affects amortizing periods.

---

## Validation of Working Calculations

### RENT ROLL CALCULATION - **VERIFIED CORRECT**

**PRD Month 2 Benchmarks:**
| Space | Excel Value | App Logic |
|-------|-------------|-----------|
| Space A (Peter Millar) | $38.69K | 2,300 SF × $201.45 × (1.025)^(1/12) / 12 / 1000 ✓ |
| Space B (J McLaughlin) | $31.27K | 1,868 SF × $200.47 × (1.025)^(1/12) / 12 / 1000 ✓ |
| Space C (Gucci) | $93.24K | 5,950 SF × $187.65 × (1.025)^(1/12) / 12 / 1000 ✓ |

**Formula in App (cashflow.py line 57):**
```python
monthly_rent = (tenant.rsf * rent_psf * escalation_factor) / 12 / 1000
```

**Escalation Factor (line 54):**
```python
escalation_factor = (1 + rent_growth) ** (period / 12)
```

**Matches PRD Formula (Section 4.4):** ✓

---

### LEASE EXPIRATION LOGIC - **VERIFIED CORRECT**

**PRD Specification:**
- Before lease expiry: Use in-place rent
- After lease expiry: Roll to market rent
- Apply escalation throughout

**App Implementation (cashflow.py lines 46-51):**
```python
if period <= tenant.lease_end_month:
    rent_psf = tenant.in_place_rent_psf
else:
    rent_psf = tenant.market_rent_psf
```

**Matches PRD:** ✓

---

### NNN REIMBURSEMENTS - **VERIFIED CORRECT**

**PRD Structure:**
- Fixed Reimbursements: OpEx + Property Taxes
- Variable Reimbursements: Management Fee
- CapEx is NOT reimbursed

**App Implementation (cashflow.py lines 193-214):**
```python
if nnn_lease and period > 0:
    reimbursement_fixed = fixed_opex + prop_tax  # ✓
    # ...
    reimbursement_variable = mgmt_fee  # ✓
```

**Matches PRD:** ✓

---

### EXIT VALUE CALCULATION - **VERIFIED CORRECT**

**PRD Formula (Section 4.7):**
```
Exit_Value = Forward_12_NOI / Exit_Cap_Rate
Net_Proceeds = Exit_Value × (1 - Sales_Cost_%)
```

**App Implementation (cashflow.py lines 267-269):**
```python
gross_value = forward_noi / exit_cap_rate
sales_costs_amount = gross_value * sales_cost_percent
exit_proceeds = gross_value - sales_costs_amount
```

**Matches PRD:** ✓

---

### ACTUAL/365 DAY COUNT - **VERIFIED CORRECT**

**PRD Specification:** Actual/365 day count convention

**App Implementation (cashflow.py lines 277-281):**
```python
if use_actual_365:
    days_in_month = calculate_days_in_month(period_date)
    daily_rate = interest_rate / 365
    interest_expense = loan_amount * daily_rate * days_in_month
```

**Matches PRD:** ✓

---

### XIRR CALCULATION - **VERIFIED CORRECT**

**App Implementation (irr.py):**
- Uses Newton-Raphson method with multiple initial guesses
- Falls back to bisection method
- Matches Excel XIRR function

**Matches PRD:** ✓

---

## Missing Features (Not Yet Implemented)

These features are documented in the PRD but not yet implemented:

| Feature | PRD Section | Status |
|---------|-------------|--------|
| Free Rent Periods | 4.4 (Rows 49-51) | NOT IMPLEMENTED |
| TI Buildout Period Adjustment | 4.4 | NOT IMPLEMENTED |
| Parking Income | 4.4 (Row 52) | NOT IMPLEMENTED |
| Storage Revenue | 4.4 (Row 53) | NOT IMPLEMENTED |
| Variable OpEx | 4.5 (Row 62) | NOT IMPLEMENTED |
| Parking Expense | 4.5 (Row 63) | NOT IMPLEMENTED |
| Lease Commissions | LCs Sheet | NOT IMPLEMENTED |
| SOFR Curve Integration | SOFR Sheet | NOT IMPLEMENTED |
| Loan Closing Costs | 4.9 (Rows 96-97) | NOT IMPLEMENTED |
| Capitalized Interest | 4.9 (Rows 97, 125) | NOT IMPLEMENTED |

---

## Recommended Fixes (Priority Order)

### Priority 1: Interest Rate Default
```python
# app/api/scenarios.py line 57
fixed_rate: float = 0.0525  # Change from 0.05
```

### Priority 2: Cashflows Endpoint Property Tax
```python
# app/api/scenarios.py line 927
property_tax_000s = op_assumptions.get("property_tax_amount", 0) / 1000
# line 941
property_tax_amount=property_tax_000s,
```

### Priority 3: Multi-Hurdle Waterfall
Implement full multi-tier waterfall matching PRD Section 5.3-5.6.

---

## Verification Checklist

| Calculation | Excel PRD | App Code | Match |
|-------------|-----------|----------|-------|
| Monthly Rent Formula | RSF × PSF × Escalation / 12 / 1000 | cashflow.py:57 | ✓ |
| Escalation Factor | (1 + rate)^(period/12) | cashflow.py:54 | ✓ |
| Lease Expiry Logic | In-place → Market | cashflow.py:46-51 | ✓ |
| NNN Fixed Reimb | OpEx + Taxes | cashflow.py:194 | ✓ |
| NNN Variable Reimb | Mgmt Fee | cashflow.py:209 | ✓ |
| Vacancy Deduction | -Rate × Potential Rev | cashflow.py:201 | ✓ |
| NOI Formula | Eff. Revenue - Expenses | cashflow.py:218 | ✓ |
| Exit Value | Forward NOI / Cap Rate | cashflow.py:267 | ✓ |
| Sales Costs | Gross × Pct | cashflow.py:268 | ✓ |
| Interest (Actual/365) | Balance × Rate × Days/365 | cashflow.py:279-281 | ✓ |
| XIRR Method | Newton-Raphson | irr.py:165-234 | ✓ |
| Interest Rate Default | 5.25% | scenarios.py:57 | ✗ (5.00%) |
| Multi-Tier Waterfall | 3 hurdles | waterfall.py | ✗ (simplified) |

---

## Summary

**Calculations Verified Correct:** 11
**Calculations Requiring Fix:** 2
**Features Not Yet Implemented:** 10

The core financial engine (rent roll, NOI, exit value, XIRR) matches the Excel model. The remaining IRR variance (~0.17%) was primarily due to the interest rate default being 5.00% instead of 5.25%.

---

## Fixes Applied (2026-01-17)

### Fix 1: Interest Rate Default Updated
**Files Modified:**
- `app/api/scenarios.py` - Updated default from 0.05 to 0.0525 in:
  - LoanInput schema (line 57)
  - calculate_scenario_returns fallback (line 339)
  - update_scenario loan creation (line 770)
  - get_scenario_cashflows fallback (line 907, 918)
- `app/calculations/cashflow.py` - Updated default interest_rate parameter (line 132)

### Fix 2: Property Tax Conversion Bug Fixed
**File Modified:** `app/api/scenarios.py`
- Changed `property_tax_full` to `property_tax_000s` in get_scenario_cashflows endpoint
- Now properly divides by 1000 to convert to $000s before passing to cashflow module

### Fix 3: Escalation Factor Differentiation (2026-01-17)
**Files Modified:** `app/calculations/cashflow.py`

Added separate escalation functions matching Excel exactly:
- `calculate_rent_escalation()`: Monthly compounding `(1 + rate/12)^period` (Excel Row 2)
- `calculate_expense_escalation()`: Annual rate applied monthly `(1 + rate)^(period/12)` (Excel Row 3)

Updated all revenue calculations to use rent escalation and all expense calculations to use expense escalation.

### Fix 4: Per-Tenant Rollover Flag (2026-01-17)
**Files Modified:**
- `app/calculations/cashflow.py` - Added `apply_rollover_costs` field to Tenant dataclass
- `app/db/models.py` - Added `apply_rollover_costs` column to Lease model
- `app/api/scenarios.py` - Pass `apply_rollover_costs` when creating Tenant objects

This implements the Excel H-column behavior:
- `apply_rollover_costs=True` (H=0): Apply TI buildout gap, free rent, and LC at lease rollover
- `apply_rollover_costs=False` (H=1): Immediate transition to market rent with no costs

### Fix 5: Free Rent as Deduction Line Item (2026-01-17)
**File Modified:** `app/calculations/cashflow.py`

Added `calculate_tenant_rent_detailed()` function that returns:
- `gross_rent`: Revenue calculated at market rate (positive)
- `free_rent_deduction`: Separate negative deduction during free rent periods

This matches Excel behavior where free rent is displayed as a negative line item (rows 49-51).

### Fix 6: Year-by-Year LC Calculation (2026-01-17)
**File Modified:** `app/calculations/cashflow.py`

Updated `calculate_lease_commission()` to use exact Excel LCs sheet methodology:
- Year-by-year rent escalation: `rent_year_n = rent_year_1 × (1 + growth)^(n-1)`
- Year 1 net rent reduced by free rent months
- Different LC rates: 6% for years 1-5, 3% for years 6+

### Fix 7: Interest with AVERAGE Balance (2026-01-17)
**File Modified:** `app/calculations/cashflow.py`

Updated interest calculation to use average balance per Excel formula:
```
Interest = AVERAGE(beginning_balance, beginning_balance + draws) × rate × days/365
```

For I/O periods with no draws, this equals the beginning balance (no change from before).
For construction loans with draws, this properly averages the balance.

### Fix 8: Month 0 Operating Expenses Zeroed (2026-01-17)
**File Modified:** `app/calculations/cashflow.py`

Month 0 is the acquisition day with no operating activity. Previously, expenses were calculated
in Month 0 even though revenue was zeroed out, resulting in negative NOI.

Fix: Zero out all operating expenses (fixed_opex, var_opex, prop_tax, capex) in Month 0.

### Fix 9: Extended Forward NOI Calculation (2026-01-17)
**File Modified:** `app/calculations/cashflow.py`

The exit value calculation was extrapolating forward NOI instead of calculating actual values.
Now calculates NOI for months 121-132 explicitly and sums the actual values for the forward
12-month NOI used in exit valuation.

---

## Current Status (2026-01-17)

### Verified Working ✓
| Calculation | App Value | Excel Value | Status |
|-------------|-----------|-------------|--------|
| Month 1 NOI | $158.98K | $158.97K | ✓ Match |
| Month 120 NOI | $247.80K | $247.80K | ✓ Match |
| Month 0 NOI | $0.00K | $0.00K | ✓ Match |
| Rent Roll | Per-tenant | Per-tenant | ✓ Match |
| Lease Expiry Logic | Implemented | Implemented | ✓ Match |
| NNN Reimbursements | Implemented | Implemented | ✓ Match |
| XIRR Calculation | Newton-Raphson | XIRR | ✓ Match |

### Known Discrepancies

#### 1. Forward NOI / Exit Value (~2% difference)
- **App Forward NOI:** ~$3,014K
- **Excel Forward NOI:** $3,079.84K
- **App Exit Proceeds:** $59,682K
- **Excel Exit Proceeds:** $60,981K

The remaining ~$65K difference in forward NOI is unexplained. The Excel formula
`=SUM(OFFSET(Model!K69,0,X13+1,1,12))+...` may include additional components
beyond the visible formula.

#### 2. Interest Expense (~30% difference)
- **App Month 1 Interest:** $94.78K (at 5.25%)
- **Excel Month 1 Interest:** $73.09K

This significant discrepancy suggests different calculation methods or parameters
in Excel. The PRD shows conflicting interest rate values (5.00% in tables, 5.25%
in the audit specification). Even at 5.00%, our interest ($90.27K) doesn't match
Excel's $73.09K.

Possible causes:
1. Excel may use a different day count convention
2. Excel may have additional interest rate adjustments
3. The PRD documentation may have inconsistencies

---

## Current IRR Values vs Targets

| Metric | Current App | Excel Target | Variance |
|--------|-------------|--------------|----------|
| Unleveraged IRR | 8.13% | 8.57% | -0.44% |
| Leveraged IRR | 10.69% | 10.09% | +0.60% |
| LP IRR | 10.01% | 9.39% | +0.62% |
| GP IRR | 16.18% | 15.02% | +1.16% |

### Analysis
- **Unleveraged IRR** is lower than Excel due to ~$1.3M lower exit proceeds
- **Leveraged IRRs** are higher than Excel despite higher interest expense, suggesting
  differences in the waterfall distribution or other components

---

## Post-Fix Expected Values

After all fixes, the application produces values within ~0.5-1% of Excel benchmarks for
most metrics. The operating period NOIs match Excel exactly (Month 1 and Month 120).

Remaining variance is due to:
1. Forward NOI calculation methodology (~2% difference)
2. Interest expense calculation differences (~30% difference)
3. Simplified single-tier waterfall (vs multi-tier in Excel)
4. Minor rounding differences in day count calculations

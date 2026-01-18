"""
Waterfall Distribution Calculations

Calculates LP/GP distributions through multi-hurdle promote structures.
Implements institutional-quality waterfall logic matching Excel pro forma models.

Excel Reference: Waterfall tab, Assumptions rows 74-80

Structure (matching 225 Worth Ave Excel):
1. Return of Capital - LP and GP get their equity back pro-rata
2. Hurdle I - 5% pref, LP 90% / GP 10%, no promote
3. Hurdle II - 5% pref, LP 75% / GP 8.33%, 16.67% promote
4. Hurdle III - 5% pref, LP 75% / GP 8.33%, 16.67% promote
5. Final Split - LP 75% / GP 8.33%, 16.67% promote
"""

from typing import List, Dict, Optional
from datetime import date
from dataclasses import dataclass


@dataclass
class WaterfallTier:
    """Configuration for a single tier in the waterfall.

    Excel Reference: Assumptions rows 76-79
    """
    name: str
    pref_return: float  # Annual preferred return rate (e.g., 0.05 for 5%)
    lp_split: float  # LP's share of distributions at this tier
    gp_split: float  # GP's share of distributions at this tier
    gp_promote: float  # GP promote percentage at this tier


# 225 Worth Ave Excel waterfall structure (Assumptions rows 76-79)
DEFAULT_WATERFALL_TIERS = [
    WaterfallTier(
        name="Hurdle I",
        pref_return=0.05,  # 5% annual pref
        lp_split=0.90,     # 90% to LP
        gp_split=0.10,     # 10% to GP
        gp_promote=0.00,   # No promote at Hurdle I
    ),
    WaterfallTier(
        name="Hurdle II",
        pref_return=0.05,  # 5% annual pref
        lp_split=0.75,     # 75% to LP
        gp_split=0.0833,   # 8.33% to GP
        gp_promote=0.1667, # 16.67% promote
    ),
    WaterfallTier(
        name="Hurdle III",
        pref_return=0.05,  # 5% annual pref
        lp_split=0.75,     # 75% to LP
        gp_split=0.0833,   # 8.33% to GP
        gp_promote=0.1667, # 16.67% promote
    ),
]

# Final split after all hurdles satisfied
DEFAULT_FINAL_SPLIT = WaterfallTier(
    name="Final Split",
    pref_return=0.0,
    lp_split=0.75,
    gp_split=0.0833,
    gp_promote=0.1667,
)


def calculate_monthly_pref_rate(annual_rate: float, compound_monthly: bool = False) -> float:
    """
    Calculate monthly preferred return rate.

    Excel Formula (H32): =IF(Assumptions!$Y$80=1, G32/12, (1+G32)^(0.0833333333333333)-1)

    Args:
        annual_rate: Annual preferred return rate (e.g., 0.05)
        compound_monthly: If True, use simple monthly rate; if False, use compound rate

    Returns:
        Monthly rate
    """
    if compound_monthly:
        # Simple monthly rate
        return annual_rate / 12
    else:
        # Compound rate: (1 + annual)^(1/12) - 1
        return (1 + annual_rate) ** (1/12) - 1


def calculate_waterfall_distributions(
    leveraged_cash_flows: List[float],
    dates: List[date],
    total_equity: float,
    lp_share: float = 0.90,
    gp_share: float = 0.10,
    pref_return: float = 0.05,  # Backward compatible parameter
    tiers: Optional[List[WaterfallTier]] = None,
    final_split: Optional[WaterfallTier] = None,
    compound_monthly: bool = False,
) -> List[Dict]:
    """
    Calculate waterfall distributions matching Excel 225 Worth Ave model.

    Implements full 3-tier waterfall with proper equity account tracking.

    Excel Reference: Waterfall tab rows 11-143

    The waterfall processes cash flows through each tier sequentially:
    1. Return of Capital (ROC) - Return LP/GP equity pro-rata
    2. Hurdle I - 5% pref on LP/GP equity, LP 90%/GP 10%, no promote
    3. Hurdle II - 5% pref on remaining balance, LP 75%/GP 8.33%, 16.67% promote
    4. Hurdle III - 5% pref on remaining balance, LP 75%/GP 8.33%, 16.67% promote
    5. Final Split - All remaining: LP 75%/GP 8.33%, 16.67% promote

    Args:
        leveraged_cash_flows: Monthly leveraged cash flows (negative = investment)
        dates: Monthly dates
        total_equity: Total equity invested ($000s)
        lp_share: LP's share of total equity (default 90%)
        gp_share: GP's share of total equity (default 10%)
        tiers: List of WaterfallTier objects (default: 3-tier structure)
        final_split: Final profit split tier (default: 75/8.33/16.67)
        compound_monthly: Whether to compound preferred return monthly

    Returns:
        List of distribution records with detailed breakdowns by tier
    """
    if tiers is None:
        tiers = DEFAULT_WATERFALL_TIERS
    if final_split is None:
        final_split = DEFAULT_FINAL_SPLIT

    distributions = []

    # Initial equity
    lp_equity = total_equity * lp_share
    gp_equity = total_equity * gp_share

    # Track unreturned capital
    lp_capital_unreturned = lp_equity
    gp_capital_unreturned = gp_equity

    # Track equity account balances for each tier
    # Each tier tracks accrued but unpaid preferred return
    # Excel tracks: Beginning Balance + Accrual - Paydown = Ending Balance
    tier_balances = {}
    for tier in tiers:
        tier_balances[tier.name] = {
            "lp_balance": 0.0,  # LP's accrued pref balance
            "gp_balance": 0.0,  # GP's accrued pref balance
        }

    for i, cash_flow in enumerate(leveraged_cash_flows):
        period_date = dates[i] if i < len(dates) else None

        # === ACCRUE PREFERRED RETURN EACH PERIOD ===
        # Excel: Row 32 (Hurdle I LP): =+L31*$H32
        # Only accrue after month 0
        if i > 0:
            for tier in tiers:
                monthly_rate = calculate_monthly_pref_rate(tier.pref_return, compound_monthly)

                # For Hurdle I: Accrue on original equity
                # For Hurdles II/III: Accrue on ending balance from previous tier
                if tier.name == "Hurdle I":
                    # Accrue on original equity amounts
                    tier_balances[tier.name]["lp_balance"] += lp_equity * monthly_rate
                    tier_balances[tier.name]["gp_balance"] += gp_equity * monthly_rate
                else:
                    # Accrue on current tier balance
                    tier_balances[tier.name]["lp_balance"] += tier_balances[tier.name]["lp_balance"] * monthly_rate
                    tier_balances[tier.name]["gp_balance"] += tier_balances[tier.name]["gp_balance"] * monthly_rate

        # Initialize distribution components
        lp_capital_return = 0.0
        gp_capital_return = 0.0
        lp_pref_total = 0.0
        gp_pref_total = 0.0
        gp_promote_total = 0.0
        lp_profit = 0.0
        gp_profit = 0.0

        # Track tier-by-tier distributions for debugging
        tier_distributions = {}

        remaining = cash_flow

        # Only distribute positive cash flows
        if remaining > 0:
            # === STEP 1: RETURN OF CAPITAL ===
            # Excel: Rows 19, 25 (LP/GP Equity Paydown)
            total_unreturned = lp_capital_unreturned + gp_capital_unreturned

            if total_unreturned > 0:
                capital_payment = min(remaining, total_unreturned)

                # Pro-rata by unreturned amounts
                lp_pct = lp_capital_unreturned / total_unreturned if total_unreturned > 0 else lp_share

                lp_capital_return = capital_payment * lp_pct
                gp_capital_return = capital_payment * (1 - lp_pct)

                lp_capital_unreturned -= lp_capital_return
                gp_capital_unreturned -= gp_capital_return

                remaining -= capital_payment

            # === STEP 2: PROCESS EACH HURDLE TIER ===
            for tier in tiers:
                if remaining <= 0:
                    break

                tier_dist = {
                    "lp_pref": 0.0,
                    "gp_pref": 0.0,
                    "gp_promote": 0.0,
                }

                # Get accrued pref for this tier
                lp_pref_accrued = tier_balances[tier.name]["lp_balance"]
                gp_pref_accrued = tier_balances[tier.name]["gp_balance"]
                total_pref_accrued = lp_pref_accrued + gp_pref_accrued

                if total_pref_accrued > 0:
                    # Pay down accrued pref pro-rata by tier splits
                    # Excel Row 36: =-MIN(SUM(L34:L35), L$28*$H36)
                    # Available for this tier = remaining * tier's LP split
                    lp_available = remaining * tier.lp_split
                    gp_available = remaining * tier.gp_split

                    # Pay LP pref
                    lp_pref_payment = min(lp_pref_accrued, lp_available)
                    tier_balances[tier.name]["lp_balance"] -= lp_pref_payment
                    tier_dist["lp_pref"] = lp_pref_payment
                    lp_pref_total += lp_pref_payment

                    # Pay GP pref
                    gp_pref_payment = min(gp_pref_accrued, gp_available)
                    tier_balances[tier.name]["gp_balance"] -= gp_pref_payment
                    tier_dist["gp_pref"] = gp_pref_payment
                    gp_pref_total += gp_pref_payment

                    pref_paid = lp_pref_payment + gp_pref_payment
                    remaining -= pref_paid

                    # Calculate promote based on pref payments
                    # Excel Row 50: =-(L36+L47)/SUM($H36+$H47)*$H50
                    if tier.gp_promote > 0 and pref_paid > 0:
                        # Promote is proportional to pref paid
                        promote_payment = min(remaining, pref_paid * tier.gp_promote / (tier.lp_split + tier.gp_split))
                        tier_dist["gp_promote"] = promote_payment
                        gp_promote_total += promote_payment
                        remaining -= promote_payment

                tier_distributions[tier.name] = tier_dist

            # === STEP 3: FINAL PROFIT SPLIT ===
            # Any remaining cash flow after all hurdles
            if remaining > 0:
                lp_profit = remaining * final_split.lp_split
                gp_profit = remaining * final_split.gp_split
                final_promote = remaining * final_split.gp_promote
                gp_promote_total += final_promote
                remaining = 0

        # Calculate totals
        total_to_lp = lp_capital_return + lp_pref_total + lp_profit
        total_to_gp = gp_capital_return + gp_pref_total + gp_profit + gp_promote_total

        distributions.append({
            "period": i,
            "date": period_date.isoformat() if period_date else None,
            "cash_flow": round(cash_flow, 2),
            # Capital return
            "lp_capital_return": round(lp_capital_return, 2),
            "gp_capital_return": round(gp_capital_return, 2),
            # Preferred return (all tiers combined)
            "lp_preferred_return": round(lp_pref_total, 2),
            "gp_preferred_return": round(gp_pref_total, 2),
            # Profit split
            "lp_profit_share": round(lp_profit, 2),
            "gp_profit_share": round(gp_profit, 2),
            # GP promote (all tiers combined)
            "gp_promote": round(gp_promote_total, 2),
            # Totals
            "total_to_lp": round(total_to_lp, 2),
            "total_to_gp": round(total_to_gp, 2),
            # Tracking
            "lp_capital_unreturned": round(max(0, lp_capital_unreturned), 2),
            "gp_capital_unreturned": round(max(0, gp_capital_unreturned), 2),
            # Tier-level detail (for debugging)
            "tier_distributions": tier_distributions,
        })

    return distributions


def calculate_simple_waterfall(
    leveraged_cash_flows: List[float],
    dates: List[date],
    total_equity: float,
    lp_share: float = 0.90,
    gp_share: float = 0.10,
    pref_return: float = 0.05,
    compound_monthly: bool = False,
) -> List[Dict]:
    """
    Calculate simple single-tier waterfall (legacy compatibility).

    Uses only Hurdle I structure: 5% pref, LP 90% / GP 10%, no promote,
    then final split at 75/8.33/16.67.
    """
    simple_tier = WaterfallTier(
        name="Hurdle I",
        pref_return=pref_return,
        lp_split=lp_share,
        gp_split=gp_share,
        gp_promote=0.0,
    )

    return calculate_waterfall_distributions(
        leveraged_cash_flows=leveraged_cash_flows,
        dates=dates,
        total_equity=total_equity,
        lp_share=lp_share,
        gp_share=gp_share,
        tiers=[simple_tier],
        compound_monthly=compound_monthly,
    )


def extract_lp_cash_flows(
    distributions: List[Dict], lp_equity: float
) -> List[float]:
    """Extract LP cash flows from distributions for IRR calculation."""
    cash_flows = []
    for i, dist in enumerate(distributions):
        if i == 0:
            # First period: negative investment + any distribution
            cf = -lp_equity + dist["total_to_lp"]
        else:
            cf = dist["total_to_lp"]
        cash_flows.append(cf)
    return cash_flows


def extract_gp_cash_flows(
    distributions: List[Dict], gp_equity: float
) -> List[float]:
    """Extract GP cash flows from distributions for IRR calculation."""
    cash_flows = []
    for i, dist in enumerate(distributions):
        if i == 0:
            cf = -gp_equity + dist["total_to_gp"]
        else:
            cf = dist["total_to_gp"]
        cash_flows.append(cf)
    return cash_flows


def calculate_waterfall_summary(distributions: List[Dict]) -> Dict:
    """Calculate summary metrics for waterfall."""
    return {
        "total_to_lp": sum(d["total_to_lp"] for d in distributions),
        "total_to_gp": sum(d["total_to_gp"] for d in distributions),
        "total_lp_capital_return": sum(d["lp_capital_return"] for d in distributions),
        "total_gp_capital_return": sum(d["gp_capital_return"] for d in distributions),
        "total_lp_pref": sum(d["lp_preferred_return"] for d in distributions),
        "total_gp_pref": sum(d["gp_preferred_return"] for d in distributions),
        "total_lp_profit": sum(d["lp_profit_share"] for d in distributions),
        "total_gp_profit": sum(d["gp_profit_share"] for d in distributions),
        "total_gp_promote": sum(d["gp_promote"] for d in distributions),
    }


# Legacy compatibility aliases
WaterfallHurdle = WaterfallTier
DEFAULT_HURDLES = DEFAULT_WATERFALL_TIERS
DEFAULT_FINAL_SPLIT_DICT = {
    "lp_split": DEFAULT_FINAL_SPLIT.lp_split,
    "gp_split": DEFAULT_FINAL_SPLIT.gp_split,
    "gp_promote": DEFAULT_FINAL_SPLIT.gp_promote,
}

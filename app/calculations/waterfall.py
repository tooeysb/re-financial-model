"""
Waterfall Distribution Calculations

Calculates LP/GP distributions through multi-hurdle promote structures.
Implements institutional-quality waterfall logic matching Excel pro forma models.

Structure (matching 225 Worth Ave Excel):
1. Return of Capital - LP and GP get their equity back pro-rata
2. Preferred Return - 5% annual pref on equity, paid pro-rata
3. Profit Split - Remaining profits split with GP promote
"""

from typing import List, Dict, Optional
from datetime import date
from dataclasses import dataclass


@dataclass
class WaterfallHurdle:
    """Configuration for a single hurdle tier in the waterfall."""

    name: str
    pref_return: float  # Annual preferred return rate (e.g., 0.05 for 5%)
    lp_split: float  # LP's share at this tier (e.g., 0.90 for 90%)
    gp_split: float  # GP's share at this tier (e.g., 0.10 for 10%)
    gp_promote: float  # GP promote percentage (e.g., 0.10 for 10% promote)


# Default 225 Worth Ave waterfall structure from Excel model
DEFAULT_HURDLES = [
    WaterfallHurdle(
        name="Hurdle I",
        pref_return=0.05,  # 5% pref
        lp_split=0.90,  # 90% to LP
        gp_split=0.10,  # 10% to GP
        gp_promote=0.0,  # No additional promote at first hurdle
    ),
]

# Default final split after all hurdles are satisfied
DEFAULT_FINAL_SPLIT = {
    "lp_split": 0.75,
    "gp_split": 0.0833,
    "gp_promote": 0.1667,
}


def calculate_waterfall_distributions(
    leveraged_cash_flows: List[float],
    dates: List[date],
    total_equity: float,
    lp_share: float = 0.90,
    gp_share: float = 0.10,
    pref_return: float = 0.05,
    compound_monthly: bool = False,
    hurdles: Optional[List[WaterfallHurdle]] = None,
    final_split: Optional[Dict] = None,
) -> List[Dict]:
    """
    Calculate waterfall distributions matching Excel 225 Worth Ave model.

    The waterfall follows this priority:
    1. Return of Capital (ROC) - Return LP/GP equity pro-rata
    2. Preferred Return - Pay accrued 5% pref on equity pro-rata
    3. Profit Split - Split remaining: 75% LP, 8.33% GP equity, 16.67% GP promote

    Args:
        leveraged_cash_flows: Array of leveraged cash flows (negative = investment, positive = distribution)
        dates: Array of dates
        total_equity: Total equity invested
        lp_share: LP's share of equity (e.g., 0.90 for 90%)
        gp_share: GP's share of equity (e.g., 0.10 for 10%)
        pref_return: Annual preferred return rate (e.g., 0.05 for 5%)
        compound_monthly: Whether to compound preferred return monthly
        hurdles: List of WaterfallHurdle objects (not used in simplified model)
        final_split: Dict with lp_split, gp_split, gp_promote for profit tier

    Returns:
        List of distribution records with detailed breakdowns
    """
    if final_split is None:
        final_split = DEFAULT_FINAL_SPLIT

    distributions = []

    # Initial equity balances
    lp_equity = total_equity * lp_share
    gp_equity = total_equity * gp_share

    # Track remaining equity to return
    lp_equity_unreturned = lp_equity
    gp_equity_unreturned = gp_equity

    # Track accrued preferred return (simple interest on original equity)
    lp_pref_accrued = 0.0
    gp_pref_accrued = 0.0

    # Monthly pref rate
    monthly_pref_rate = pref_return / 12

    for i, cash_flow in enumerate(leveraged_cash_flows):
        # Accrue preferred return on original equity each month
        if i > 0:  # Don't accrue on month 0 (investment month)
            if compound_monthly:
                # Compound on unpaid pref
                lp_pref_accrued += (lp_equity + lp_pref_accrued) * monthly_pref_rate
                gp_pref_accrued += (gp_equity + gp_pref_accrued) * monthly_pref_rate
            else:
                # Simple interest on original equity
                lp_pref_accrued += lp_equity * monthly_pref_rate
                gp_pref_accrued += gp_equity * monthly_pref_rate

        # Initialize distribution components for this period
        lp_equity_return = 0.0
        gp_equity_return = 0.0
        lp_pref_paid = 0.0
        gp_pref_paid = 0.0
        lp_profit_share = 0.0
        gp_profit_share = 0.0
        gp_promote_paid = 0.0

        remaining = cash_flow

        # Only distribute positive cash flows
        if remaining > 0:
            # === STEP 1: Return of Capital ===
            # Pay back LP and GP equity pro-rata until fully returned
            total_equity_unreturned = lp_equity_unreturned + gp_equity_unreturned

            if total_equity_unreturned > 0:
                equity_payment = min(remaining, total_equity_unreturned)

                # Pro-rata split based on remaining equity
                if total_equity_unreturned > 0:
                    lp_equity_pct = lp_equity_unreturned / total_equity_unreturned
                else:
                    lp_equity_pct = lp_share

                lp_equity_return = equity_payment * lp_equity_pct
                gp_equity_return = equity_payment * (1 - lp_equity_pct)

                lp_equity_unreturned -= lp_equity_return
                gp_equity_unreturned -= gp_equity_return

                remaining -= equity_payment

            # === STEP 2: Preferred Return ===
            # Pay accrued preferred return pro-rata
            total_pref_owed = lp_pref_accrued + gp_pref_accrued

            if remaining > 0 and total_pref_owed > 0:
                pref_payment = min(remaining, total_pref_owed)

                # Pro-rata split based on accrued pref
                if total_pref_owed > 0:
                    lp_pref_pct = lp_pref_accrued / total_pref_owed
                else:
                    lp_pref_pct = lp_share

                lp_pref_paid = pref_payment * lp_pref_pct
                gp_pref_paid = pref_payment * (1 - lp_pref_pct)

                lp_pref_accrued -= lp_pref_paid
                gp_pref_accrued -= gp_pref_paid

                remaining -= pref_payment

            # === STEP 3: Profit Split with GP Promote ===
            # After equity and pref returned, split remaining profits
            if remaining > 0:
                lp_profit_share = remaining * final_split["lp_split"]
                gp_profit_share = remaining * final_split["gp_split"]
                gp_promote_paid = remaining * final_split["gp_promote"]

        # Calculate totals
        total_to_lp = lp_equity_return + lp_pref_paid + lp_profit_share
        total_to_gp = gp_equity_return + gp_pref_paid + gp_profit_share + gp_promote_paid

        distributions.append({
            "period": i,
            "date": dates[i].isoformat() if i < len(dates) else None,
            "cash_flow": round(cash_flow, 2),
            "lp_equity_return": round(lp_equity_return, 2),
            "gp_equity_return": round(gp_equity_return, 2),
            "lp_preferred_return": round(lp_pref_paid, 2),
            "gp_preferred_return": round(gp_pref_paid, 2),
            "lp_profit_share": round(lp_profit_share, 2),
            "gp_profit_share": round(gp_profit_share, 2),
            "gp_promote": round(gp_promote_paid, 2),
            "total_to_lp": round(total_to_lp, 2),
            "total_to_gp": round(total_to_gp, 2),
            "lp_equity_unreturned": round(max(0, lp_equity_unreturned), 2),
            "gp_equity_unreturned": round(max(0, gp_equity_unreturned), 2),
            "lp_pref_accrued": round(max(0, lp_pref_accrued), 2),
            "gp_pref_accrued": round(max(0, gp_pref_accrued), 2),
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
    """
    final_split = {
        "lp_split": lp_share,
        "gp_split": gp_share,
        "gp_promote": 0.0,
    }

    return calculate_waterfall_distributions(
        leveraged_cash_flows=leveraged_cash_flows,
        dates=dates,
        total_equity=total_equity,
        lp_share=lp_share,
        gp_share=gp_share,
        pref_return=pref_return,
        compound_monthly=compound_monthly,
        final_split=final_split,
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
        "total_lp_equity_return": sum(d["lp_equity_return"] for d in distributions),
        "total_gp_equity_return": sum(d["gp_equity_return"] for d in distributions),
        "total_lp_pref": sum(d["lp_preferred_return"] for d in distributions),
        "total_gp_pref": sum(d["gp_preferred_return"] for d in distributions),
        "total_lp_profit": sum(d["lp_profit_share"] for d in distributions),
        "total_gp_profit": sum(d["gp_profit_share"] for d in distributions),
        "total_gp_promote": sum(d["gp_promote"] for d in distributions),
    }

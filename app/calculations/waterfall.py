"""
Waterfall Distribution Calculations

Calculates LP/GP distributions through multi-hurdle promote structures.
"""

from typing import List, Dict, Optional
from datetime import date


def calculate_waterfall_distributions(
    leveraged_cash_flows: List[float],
    dates: List[date],
    total_equity: float,
    lp_share: float = 0.90,
    gp_share: float = 0.10,
    pref_return: float = 0.05,
    compound_monthly: bool = False,
) -> List[Dict]:
    """
    Calculate waterfall distributions for all periods.

    Simplified single-hurdle waterfall with preferred return.

    Args:
        leveraged_cash_flows: Array of leveraged cash flows
        dates: Array of dates
        total_equity: Total equity invested
        lp_share: LP's share of equity (e.g., 0.90 for 90%)
        gp_share: GP's share of equity (e.g., 0.10 for 10%)
        pref_return: Annual preferred return rate
        compound_monthly: Whether to compound preferred return monthly

    Returns:
        List of distribution records
    """
    distributions = []

    lp_equity = total_equity * lp_share
    gp_equity = total_equity * gp_share

    # Track balances
    lp_equity_balance = lp_equity
    gp_equity_balance = gp_equity
    lp_pref_accrued = 0.0
    gp_pref_accrued = 0.0

    monthly_pref_rate = pref_return / 12

    for i, cash_flow in enumerate(leveraged_cash_flows):
        # Accrue preferred return
        if compound_monthly:
            lp_pref_accrued += (lp_equity_balance + lp_pref_accrued) * monthly_pref_rate
            gp_pref_accrued += (gp_equity_balance + gp_pref_accrued) * monthly_pref_rate
        else:
            lp_pref_accrued += lp_equity_balance * monthly_pref_rate
            gp_pref_accrued += gp_equity_balance * monthly_pref_rate

        # Initialize distribution amounts
        lp_equity_paydown = 0.0
        gp_equity_paydown = 0.0
        lp_pref_paid = 0.0
        gp_pref_paid = 0.0
        lp_profit = 0.0
        gp_profit = 0.0

        remaining = cash_flow

        if remaining > 0:
            # 1. Pay accrued preferred return first
            total_pref_owed = lp_pref_accrued + gp_pref_accrued

            if total_pref_owed > 0:
                pref_payment = min(remaining, total_pref_owed)
                if total_pref_owed > 0:
                    lp_share_of_pref = lp_pref_accrued / total_pref_owed
                else:
                    lp_share_of_pref = lp_share

                lp_pref_paid = pref_payment * lp_share_of_pref
                gp_pref_paid = pref_payment * (1 - lp_share_of_pref)

                lp_pref_accrued -= lp_pref_paid
                gp_pref_accrued -= gp_pref_paid

                remaining -= pref_payment

            # 2. Return of capital
            total_equity_owed = lp_equity_balance + gp_equity_balance

            if remaining > 0 and total_equity_owed > 0:
                equity_payment = min(remaining, total_equity_owed)
                if total_equity_owed > 0:
                    lp_share_of_equity = lp_equity_balance / total_equity_owed
                else:
                    lp_share_of_equity = lp_share

                lp_equity_paydown = equity_payment * lp_share_of_equity
                gp_equity_paydown = equity_payment * (1 - lp_share_of_equity)

                lp_equity_balance -= lp_equity_paydown
                gp_equity_balance -= gp_equity_paydown

                remaining -= equity_payment

            # 3. Remaining profit split (after pref and ROC)
            if remaining > 0:
                # Simple split - can be enhanced for multi-tier promotes
                lp_profit = remaining * lp_share
                gp_profit = remaining * gp_share

        total_to_lp = lp_equity_paydown + lp_pref_paid + lp_profit
        total_to_gp = gp_equity_paydown + gp_pref_paid + gp_profit

        distributions.append(
            {
                "period": i,
                "date": dates[i].isoformat() if i < len(dates) else None,
                "cash_flow": round(cash_flow, 2),
                "lp_equity_paydown": round(lp_equity_paydown, 2),
                "gp_equity_paydown": round(gp_equity_paydown, 2),
                "lp_preferred_return": round(lp_pref_paid, 2),
                "gp_preferred_return": round(gp_pref_paid, 2),
                "lp_profit": round(lp_profit, 2),
                "gp_profit": round(gp_profit, 2),
                "total_to_lp": round(total_to_lp, 2),
                "total_to_gp": round(total_to_gp, 2),
                "lp_equity_balance": round(max(0, lp_equity_balance), 2),
                "gp_equity_balance": round(max(0, gp_equity_balance), 2),
            }
        )

    return distributions


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
        "total_equity_paydown": sum(
            d["lp_equity_paydown"] + d["gp_equity_paydown"] for d in distributions
        ),
        "total_preferred_return": sum(
            d["lp_preferred_return"] + d["gp_preferred_return"] for d in distributions
        ),
        "total_profit": sum(d["lp_profit"] + d["gp_profit"] for d in distributions),
    }

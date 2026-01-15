"""
Loan Amortization Calculations

Implements loan payment and amortization schedule calculations,
matching Excel's PMT, IPMT, and PPMT functions.
"""

from typing import List, Dict, Optional
from datetime import date
from dateutil.relativedelta import relativedelta


def calculate_payment(
    principal: float, annual_rate: float, amortization_months: int
) -> float:
    """
    Calculate monthly loan payment.

    Matches Excel's PMT() function.

    Args:
        principal: Loan principal amount
        annual_rate: Annual interest rate as decimal (e.g., 0.05 for 5%)
        amortization_months: Total amortization period in months

    Returns:
        Monthly payment amount (positive number)
    """
    if principal <= 0:
        return 0.0
    if amortization_months <= 0:
        return 0.0

    monthly_rate = annual_rate / 12

    if monthly_rate == 0:
        return principal / amortization_months

    payment = (
        principal
        * monthly_rate
        * ((1 + monthly_rate) ** amortization_months)
        / (((1 + monthly_rate) ** amortization_months) - 1)
    )

    return payment


def calculate_remaining_balance(
    principal: float,
    annual_rate: float,
    amortization_months: int,
    payments_completed: int,
) -> float:
    """Calculate remaining loan balance after N payments."""
    monthly_rate = annual_rate / 12
    payment = calculate_payment(principal, annual_rate, amortization_months)

    if monthly_rate == 0:
        return principal - payment * payments_completed

    balance = principal * ((1 + monthly_rate) ** payments_completed) - payment * (
        ((1 + monthly_rate) ** payments_completed - 1) / monthly_rate
    )

    return max(0.0, balance)


def generate_amortization_schedule(
    principal: float,
    annual_rate: float,
    amortization_months: int,
    io_months: int = 0,
    total_months: int = 120,
    start_date: Optional[date] = None,
) -> List[Dict]:
    """
    Generate a full amortization schedule.

    Args:
        principal: Loan principal amount
        annual_rate: Annual interest rate as decimal
        amortization_months: Amortization period in months
        io_months: Interest-only period in months
        total_months: Total loan term in months
        start_date: Date of first payment

    Returns:
        List of amortization rows
    """
    schedule = []
    balance = principal
    monthly_rate = annual_rate / 12

    if start_date is None:
        start_date = date.today()

    for period in range(1, total_months + 1):
        period_date = start_date + relativedelta(months=period - 1)

        # Calculate interest for this period
        interest = balance * monthly_rate

        # Calculate principal payment
        if period <= io_months:
            # Interest-only period
            principal_pmt = 0.0
            payment = interest
        else:
            # Amortizing period
            remaining_amort_periods = amortization_months - (period - io_months - 1)
            if remaining_amort_periods > 0:
                payment = calculate_payment(balance, annual_rate, remaining_amort_periods)
                principal_pmt = payment - interest
                principal_pmt = min(principal_pmt, balance)
                payment = principal_pmt + interest
            else:
                # Pay off remaining balance
                principal_pmt = balance
                payment = balance + interest

        ending_balance = balance - principal_pmt

        schedule.append(
            {
                "period": period,
                "date": period_date.isoformat(),
                "beginning_balance": round(balance, 2),
                "payment": round(payment, 2),
                "interest": round(interest, 2),
                "principal": round(principal_pmt, 2),
                "ending_balance": round(max(0, ending_balance), 2),
            }
        )

        balance = max(0.0, ending_balance)

        # Stop if balance is paid off
        if balance == 0:
            break

    return schedule


def calculate_total_interest(schedule: List[Dict]) -> float:
    """Calculate total interest paid over loan term."""
    return sum(row["interest"] for row in schedule)


def calculate_debt_service(
    schedule: List[Dict], start_period: int, end_period: int
) -> float:
    """Calculate total debt service (P+I) for a range of periods."""
    return sum(
        row["payment"]
        for row in schedule
        if start_period <= row["period"] <= end_period
    )


def calculate_dscr(noi: float, debt_service: float) -> float:
    """
    Calculate Debt Service Coverage Ratio (DSCR).

    Args:
        noi: Net Operating Income for the period
        debt_service: Debt service for the period

    Returns:
        DSCR ratio
    """
    if debt_service == 0:
        return float("inf")
    return noi / debt_service


def calculate_loan_constant(
    principal: float, annual_rate: float, amortization_years: int
) -> float:
    """Calculate loan constant (annual debt service / loan amount)."""
    monthly_payment = calculate_payment(principal, annual_rate, amortization_years * 12)
    annual_debt_service = monthly_payment * 12
    return annual_debt_service / principal if principal > 0 else 0.0

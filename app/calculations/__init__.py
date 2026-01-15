"""
Financial Calculation Engine

Core calculation modules for real estate investment analysis.
All calculations are designed to match Excel formula behavior.
"""

from app.calculations import irr, amortization, cashflow, waterfall

__all__ = ["irr", "amortization", "cashflow", "waterfall"]

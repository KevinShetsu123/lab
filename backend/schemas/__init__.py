"""Schemas package."""

from backend.schemas.scrapper import (
    FinancialReportBase,
    FinancialReportCreate,
    FinancialReportInDB,
    FinancialReportResponse,
    ScrapperRequest,
    ScrapperResponse,
    BulkScrapperRequest,
    BulkScrapperResponse,
)

from backend.schemas.financial import (
    BalanceSheetItemCreate,
    BalanceSheetItemResponse,
    IncomeStatementItemCreate,
    IncomeStatementItemResponse,
    CashFlowItemCreate,
    CashFlowItemResponse,
    FinancialStatementsCreate,
    FinancialStatementsResponse,
)

__all__ = [
    "FinancialReportBase",
    "FinancialReportCreate",
    "FinancialReportInDB",
    "FinancialReportResponse",
    "ScrapperRequest",
    "ScrapperResponse",
    "BulkScrapperRequest",
    "BulkScrapperResponse",
    "BalanceSheetItemCreate",
    "BalanceSheetItemResponse",
    "IncomeStatementItemCreate",
    "IncomeStatementItemResponse",
    "CashFlowItemCreate",
    "CashFlowItemResponse",
    "FinancialStatementsCreate",
    "FinancialStatementsResponse",
]

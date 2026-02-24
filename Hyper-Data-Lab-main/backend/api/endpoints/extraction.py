"""
Extraction API endpoints.

This module provides REST API endpoints for extracting financial data
from PDF reports and processing them into structured data.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.database.db import get_session
from backend.database.repositories import (
    ReportRepository,
    BalanceSheetItemRepository,
    IncomeStatementItemRepository,
    CashFlowItemRepository
)
from backend.schemas import (
    FinancialReportResponse,
    BalanceSheetItemCreate,
    IncomeStatementItemCreate,
    CashFlowItemCreate,
    BalanceSheetItemResponse,
    IncomeStatementItemResponse,
    CashFlowItemResponse
)
from backend.services.processors.converter import ImageConverter


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extraction", tags=["extraction"])


class ExtractionRequest(BaseModel):
    """Request schema for extracting data from report."""
    report_id: int = Field(..., description="ID of the report to extract")
    start_page: int = Field(1, ge=1, description="Start page number")
    end_page: Optional[int] = Field(None, description="End page number")
    dpi: int = Field(300, ge=72, le=600, description="DPI for image conversion")
    enhance: bool = Field(True, description="Enhance image quality")


class ExtractionResponse(BaseModel):
    """Response schema for extraction results."""
    success: bool
    message: str
    report_id: int
    pages_processed: int
    images_generated: int


class FinancialDataExtractionRequest(BaseModel):
    """Request for extracting and saving financial data."""
    report_id: int = Field(..., description="Report ID")
    statement_type: str = Field(
        ...,
        description="Type: 'balance_sheet', 'income_statement', 'cash_flow'"
    )
    items: List[dict] = Field(
        ...,
        description="List of financial items to save"
    )


class FinancialDataExtractionResponse(BaseModel):
    """Response for financial data extraction."""
    success: bool
    message: str
    report_id: int
    statement_type: str
    items_saved: int


@router.post("/convert-pdf", response_model=ExtractionResponse)
async def convert_report_to_images(
    request: ExtractionRequest,
    db: Session = Depends(get_session)
) -> ExtractionResponse:
    """Convert PDF report pages to images for processing.

    This endpoint:
    1. Retrieves the report from database
    2. Downloads PDF from report URL
    3. Converts specified pages to images
    4. Optionally enhances image quality

    Args:
        request: Extraction configuration
        db: Database session

    Returns:
        ExtractionResponse: Processing results

    Raises:
        HTTPException: If report not found or conversion fails
    """
    logger.info("Converting report %d to images", request.report_id)

    # Get report from database
    report_repo = ReportRepository(db)
    report = report_repo.get_by_id(request.report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {request.report_id} not found"
        )

    try:
        # Initialize converter
        converter = ImageConverter(dpi=request.dpi)

        # Download PDF
        pdf_bytes = converter.get_file_bytes(report.report_url)
        if not pdf_bytes:
            raise ValueError("Failed to download PDF file")

        # Determine end page
        end_page = request.end_page if request.end_page else request.start_page

        # Convert to images
        images = converter.images_converter(
            pdf_bytes,
            request.start_page,
            end_page
        )

        if not images:
            raise ValueError("No images generated from PDF")

        # Enhance images if requested
        if request.enhance:
            images = converter.image_enhance(images)

        # Add page markers
        images = converter.page_number_marker(images, request.start_page)

        pages_processed = end_page - request.start_page + 1

        return ExtractionResponse(
            success=True,
            message=f"Successfully converted {pages_processed} pages to images",
            report_id=request.report_id,
            pages_processed=pages_processed,
            images_generated=len(images)
        )

    except Exception as e:
        logger.error(
            "Error converting report %d: %s",
            request.report_id, e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert PDF: {str(e)}"
        ) from e


@router.post("/save-financial-data", response_model=FinancialDataExtractionResponse)
async def save_financial_data(
    request: FinancialDataExtractionRequest,
    db: Session = Depends(get_session)
) -> FinancialDataExtractionResponse:
    """Save extracted financial data to database.

    This endpoint saves financial statement items (balance sheet,
    income statement, or cash flow) to the appropriate table.

    Args:
        request: Financial data to save
        db: Database session

    Returns:
        FinancialDataExtractionResponse: Save results

    Raises:
        HTTPException: If validation fails or save error occurs
    """
    logger.info(
        "Saving %s data for report %d",
        request.statement_type,
        request.report_id
    )

    # Verify report exists
    report_repo = ReportRepository(db)
    report = report_repo.get_by_id(request.report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {request.report_id} not found"
        )

    try:
        saved_count = 0

        # Select appropriate repository
        if request.statement_type == "balance_sheet":
            repo = BalanceSheetItemRepository(db)
            schema_class = BalanceSheetItemCreate
        elif request.statement_type == "income_statement":
            repo = IncomeStatementItemRepository(db)
            schema_class = IncomeStatementItemCreate
        elif request.statement_type == "cash_flow":
            repo = CashFlowItemRepository(db)
            schema_class = CashFlowItemCreate
        else:
            raise ValueError(
                f"Invalid statement type: {request.statement_type}"
            )

        # Validate and save each item
        for item_data in request.items:
            # Add report_id to item
            item_data["report_id"] = request.report_id

            # Validate with Pydantic
            validated_item = schema_class(**item_data)

            # Save to database
            repo.create(validated_item.model_dump())
            saved_count += 1

        db.commit()

        return FinancialDataExtractionResponse(
            success=True,
            message=f"Successfully saved {saved_count} items",
            report_id=request.report_id,
            statement_type=request.statement_type,
            items_saved=saved_count
        )

    except Exception as e:
        db.rollback()
        logger.error(
            "Error saving financial data: %s",
            e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save financial data: {str(e)}"
        ) from e


@router.get("/financial-data/{report_id}")
async def get_extracted_financial_data(
    report_id: int,
    statement_type: Optional[str] = None,
    db: Session = Depends(get_session)
) -> dict:
    """Get extracted financial data for a report.

    Args:
        report_id: Report ID
        statement_type: Optional filter by statement type
        db: Database session

    Returns:
        Dictionary containing financial data

    Raises:
        HTTPException: If report not found
    """
    # Verify report exists
    report_repo = ReportRepository(db)
    report = report_repo.get_by_id(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found"
        )

    result = {
        "report_id": report_id,
        "symbol": report.symbol,
        "company_name": report.company_name,
        "report_type": report.report_type,
        "report_year": report.report_year
    }

    # Get balance sheet items if requested
    if not statement_type or statement_type == "balance_sheet":
        bs_repo = BalanceSheetItemRepository(db)
        bs_items = bs_repo.get_by_report_id(report_id)
        result["balance_sheet"] = [
            BalanceSheetItemResponse.model_validate(item)
            for item in bs_items
        ]

    # Get income statement items if requested
    if not statement_type or statement_type == "income_statement":
        is_repo = IncomeStatementItemRepository(db)
        is_items = is_repo.get_by_report_id(report_id)
        result["income_statement"] = [
            IncomeStatementItemResponse.model_validate(item)
            for item in is_items
        ]

    # Get cash flow items if requested
    if not statement_type or statement_type == "cash_flow":
        cf_repo = CashFlowItemRepository(db)
        cf_items = cf_repo.get_by_report_id(report_id)
        result["cash_flow"] = [
            CashFlowItemResponse.model_validate(item)
            for item in cf_items
        ]

    return result

"""Quote management API endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends, Request, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from src.services.quote_service import QuoteService
from src.services.agent_service import AgentService
from src.models.quote import Quote
from src.utils.logger import get_logger
from .dependencies import get_current_user, require_auth
from .validators import (
    validate_quote_id, validate_region, validate_pricing_model,
    validate_export_format, validate_quote_status, sanitize_configuration_text,
    validate_pagination, sanitize_notes
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/quotes", tags=["quotes"])

# Initialize services
quote_service = QuoteService()
agent_service = AgentService()


# Request/Response Models

class CreateQuoteRequest(BaseModel):
    """Create quote request model."""
    configuration_text: Optional[str] = None
    format_hint: Optional[str] = Field(None, description="Format hint: json, yaml, csv, or text")
    region: str = Field(default="us-east-1", description="AWS region for pricing")
    pricing_model: str = Field(default="on-demand", description="Pricing model: on-demand, reserved, savings-plan")
    notes: Optional[str] = None


class QuoteResponse(BaseModel):
    """Quote response model."""
    quote_id: str
    user_id: str
    created_at: str
    updated_at: str
    status: str
    original_input: str
    parsed_services: List[Dict[str, Any]]
    aws_mappings: List[Dict[str, Any]]
    pricing_results: List[Dict[str, Any]]
    total_monthly_cost: float
    total_annual_cost: float
    currency: str
    region: str
    notes: Optional[str]
    export_urls: Dict[str, str]


class QuoteListResponse(BaseModel):
    """Quote list response model."""
    quotes: List[QuoteResponse]
    total: int


class UpdateQuoteRequest(BaseModel):
    """Update quote request model."""
    status: Optional[str] = None
    notes: Optional[str] = None


class DownloadQuoteRequest(BaseModel):
    """Download quote request model."""
    format: str = Field(..., description="Export format: pdf, excel, or json")


# Endpoints

@router.post("/create", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    request: Request,
    quote_data: CreateQuoteRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new quote.
    
    Processes the configuration and generates an AWS pricing quote.
    """
    try:
        logger.info(f"Creating quote for user {current_user['user_id']}")
        
        # Validate and sanitize inputs
        configuration_text = sanitize_configuration_text(quote_data.configuration_text)
        region = validate_region(quote_data.region)
        pricing_model = validate_pricing_model(quote_data.pricing_model)
        notes = sanitize_notes(quote_data.notes)
        
        # Process quote using agent service
        result = await agent_service.process_quote_request(
            configuration_text=configuration_text,
            format_hint=quote_data.format_hint,
            region=region,
            pricing_model=pricing_model,
            user_id=current_user['user_id']
        )
        
        # Create quote in database
        quote = quote_service.create_quote(
            user_id=current_user['user_id'],
            original_input=configuration_text,
            parsed_services=result['parsed_services'],
            aws_mappings=result['aws_mappings'],
            pricing_results=result['pricing_results'],
            total_monthly_cost=result['total_monthly_cost'],
            total_annual_cost=result['total_annual_cost'],
            region=region,
            notes=notes
        )
        
        return _quote_to_response(quote)
        
    except ValueError as e:
        logger.error(f"Validation error creating quote: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating quote: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create quote"
        )


@router.post("/upload", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote_from_file(
    request: Request,
    file: UploadFile = File(...),
    region: str = "us-east-1",
    pricing_model: str = "on-demand",
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new quote from uploaded file.
    
    Supports JSON, YAML, CSV, and text files.
    """
    try:
        logger.info(f"Creating quote from file for user {current_user['user_id']}")
        
        # Read file content
        content = await file.read()
        configuration_text = content.decode('utf-8')
        
        # Determine format from filename
        format_hint = None
        if file.filename:
            if file.filename.endswith('.json'):
                format_hint = 'json'
            elif file.filename.endswith(('.yaml', '.yml')):
                format_hint = 'yaml'
            elif file.filename.endswith('.csv'):
                format_hint = 'csv'
        
        # Process quote using agent service
        result = await agent_service.process_quote_request(
            configuration_text=configuration_text,
            format_hint=format_hint,
            region=region,
            pricing_model=pricing_model,
            user_id=current_user['user_id']
        )
        
        # Create quote in database
        quote = quote_service.create_quote(
            user_id=current_user['user_id'],
            original_input=configuration_text,
            parsed_services=result['parsed_services'],
            aws_mappings=result['aws_mappings'],
            pricing_results=result['pricing_results'],
            total_monthly_cost=result['total_monthly_cost'],
            total_annual_cost=result['total_annual_cost'],
            region=region,
            notes=notes
        )
        
        return _quote_to_response(quote)
        
    except Exception as e:
        logger.error(f"Error creating quote from file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create quote from file"
        )


@router.get("/{quote_id}", response_model=QuoteResponse, status_code=status.HTTP_200_OK)
async def get_quote(
    quote_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific quote by ID.
    
    Users can only access their own quotes unless they are admins.
    """
    try:
        # Validate quote_id
        quote_id = validate_quote_id(quote_id)
        
        quote = quote_service.get_quote(quote_id)
        
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote not found"
            )
        
        # Check authorization
        if quote.user_id != current_user['user_id'] and current_user['role'] != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this quote"
            )
        
        return _quote_to_response(quote)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quote: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quote"
        )


@router.get("/history", response_model=QuoteListResponse, status_code=status.HTTP_200_OK)
async def list_quotes(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    List quotes for the current user.
    
    Admins can see all quotes, regular users only see their own.
    """
    try:
        # Validate pagination
        limit, offset = validate_pagination(limit, offset)
        
        if current_user['role'] == 'admin':
            quotes = quote_service.list_all_quotes(limit=limit, offset=offset)
        else:
            quotes = quote_service.list_user_quotes(
                user_id=current_user['user_id'],
                limit=limit,
                offset=offset
            )
        
        return QuoteListResponse(
            quotes=[_quote_to_response(q) for q in quotes],
            total=len(quotes)
        )
        
    except Exception as e:
        logger.error(f"Error listing quotes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list quotes"
        )


@router.put("/{quote_id}", response_model=QuoteResponse, status_code=status.HTTP_200_OK)
async def update_quote(
    quote_id: str,
    update_data: UpdateQuoteRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a quote.
    
    Users can only update their own quotes unless they are admins.
    """
    try:
        # Validate inputs
        quote_id = validate_quote_id(quote_id)
        if update_data.status:
            update_data.status = validate_quote_status(update_data.status)
        if update_data.notes:
            update_data.notes = sanitize_notes(update_data.notes)
        
        quote = quote_service.get_quote(quote_id)
        
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote not found"
            )
        
        # Check authorization
        if quote.user_id != current_user['user_id'] and current_user['role'] != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this quote"
            )
        
        # Update quote
        updated_quote = quote_service.update_quote(
            quote_id=quote_id,
            status=update_data.status,
            notes=update_data.notes
        )
        
        return _quote_to_response(updated_quote)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating quote: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update quote"
        )


@router.delete("/{quote_id}", status_code=status.HTTP_200_OK)
async def delete_quote(
    quote_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a quote.
    
    Users can only delete their own quotes unless they are admins.
    """
    try:
        quote = quote_service.get_quote(quote_id)
        
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote not found"
            )
        
        # Check authorization
        if quote.user_id != current_user['user_id'] and current_user['role'] != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this quote"
            )
        
        # Delete quote
        success = quote_service.delete_quote(quote_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete quote"
            )
        
        return {"message": "Quote deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting quote: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete quote"
        )


@router.get("/{quote_id}/download", status_code=status.HTTP_200_OK)
async def download_quote(
    quote_id: str,
    format: str = "pdf",
    current_user: dict = Depends(get_current_user)
):
    """
    Download a quote in the specified format.
    
    Supported formats: pdf, excel, json
    """
    try:
        # Validate inputs
        quote_id = validate_quote_id(quote_id)
        format = validate_export_format(format)
        
        quote = quote_service.get_quote(quote_id)
        
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote not found"
            )
        
        # Check authorization
        if quote.user_id != current_user['user_id'] and current_user['role'] != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to download this quote"
            )
        
        # Get or generate download URL
        if format in quote.export_urls:
            download_url = quote.export_urls[format]
        else:
            # Generate export
            download_url = quote_service.export_quote(quote_id, format)
        
        return {
            "download_url": download_url,
            "format": format,
            "expires_in": 3600  # 1 hour
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading quote: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download quote"
        )


# Helper functions

def _quote_to_response(quote: Quote) -> QuoteResponse:
    """Convert Quote model to QuoteResponse."""
    return QuoteResponse(
        quote_id=quote.quote_id,
        user_id=quote.user_id,
        created_at=quote.created_at.isoformat(),
        updated_at=quote.updated_at.isoformat(),
        status=quote.status,
        original_input=quote.original_input,
        parsed_services=quote.parsed_services,
        aws_mappings=quote.aws_mappings,
        pricing_results=quote.pricing_results,
        total_monthly_cost=float(quote.total_monthly_cost),
        total_annual_cost=float(quote.total_annual_cost),
        currency=quote.currency,
        region=quote.region,
        notes=quote.notes,
        export_urls=quote.export_urls
    )

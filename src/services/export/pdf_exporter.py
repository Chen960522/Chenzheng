"""PDF export service for quotes."""

import io
from typing import Dict, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from ...models.quote import Quote
from ...utils.logger import get_logger

logger = get_logger(__name__)


class PDFExporter:
    """
    Service for exporting quotes to PDF format.
    
    Uses ReportLab to generate professional PDF documents.
    Uploads to S3 and generates presigned URLs for download.
    """
    
    def __init__(self, s3_client=None, bucket_name: str = 'aws-pricing-quotes'):
        """
        Initialize the PDF exporter.
        
        Args:
            s3_client: Boto3 S3 client (optional, will create if not provided)
            bucket_name: S3 bucket name for storing PDFs
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is not installed. Install it with: pip install reportlab"
            )
        
        self.s3_client = s3_client or boto3.client('s3')
        self.bucket_name = bucket_name
        logger.info(f"PDFExporter initialized with bucket: {bucket_name}")
    
    def export_quote(
        self,
        quote: Quote,
        quote_content: Dict[str, Any],
        upload_to_s3: bool = True
    ) -> str:
        """
        Export quote to PDF format.
        
        Args:
            quote: Quote object
            quote_content: Structured quote content from QuoteGenerator
            upload_to_s3: Whether to upload to S3 (default: True)
        
        Returns:
            S3 presigned URL if uploaded, or local file path
        """
        logger.info(f"Exporting quote {quote.quote_id} to PDF")
        
        # Generate PDF in memory
        pdf_buffer = io.BytesIO()
        self._generate_pdf(pdf_buffer, quote, quote_content)
        pdf_buffer.seek(0)
        
        if upload_to_s3:
            # Upload to S3 and get presigned URL
            s3_key = f"quotes/{quote.user_id}/{quote.quote_id}.pdf"
            url = self._upload_to_s3(pdf_buffer, s3_key)
            logger.info(f"PDF uploaded to S3: {s3_key}")
            return url
        else:
            # Save to local file
            filename = f"quote_{quote.quote_id}.pdf"
            with open(filename, 'wb') as f:
                f.write(pdf_buffer.getvalue())
            logger.info(f"PDF saved locally: {filename}")
            return filename
    
    def _generate_pdf(
        self,
        buffer: io.BytesIO,
        quote: Quote,
        content: Dict[str, Any]
    ) -> None:
        """Generate PDF document."""
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build story (content elements)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#232F3E'),  # AWS dark blue
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#232F3E'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Title
        story.append(Paragraph(content['header']['title'], title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Header information table
        header_data = [
            [content['header']['quote_id'], quote.quote_id],
            [self._get_translation(quote.language, 'created_date'), content['header']['created_date']],
            [self._get_translation(quote.language, 'status'), content['header']['status']],
            [self._get_translation(quote.language, 'region'), content['header']['region']]
        ]
        
        header_table = Table(header_data, colWidths=[2*inch, 4*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Original Services Section
        story.append(Paragraph(content['original_services']['title'], heading_style))
        
        for i, service in enumerate(content['original_services']['services'], 1):
            service_text = f"<b>{i}. {service['provider']} - {service['service_name']}</b><br/>"
            service_text += f"Type: {service['service_type']}<br/>"
            service_text += f"Specifications: {self._format_dict(service['specifications'])}<br/>"
            service_text += f"Quantity: {service['quantity']}"
            
            story.append(Paragraph(service_text, styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(Spacer(1, 0.2*inch))
        
        # AWS Mappings Section
        story.append(Paragraph(content['aws_mappings']['title'], heading_style))
        
        for i, mapping in enumerate(content['aws_mappings']['mappings'], 1):
            mapping_text = f"<b>{i}. {mapping['aws_service']} ({mapping['aws_service_type']})</b><br/>"
            mapping_text += f"Confidence: {mapping['confidence_score']:.2f}<br/>"
            mapping_text += f"Explanation: {mapping['explanation']}<br/>"
            
            if mapping['alternatives']:
                mapping_text += f"Alternatives: {', '.join(mapping['alternatives'])}"
            
            story.append(Paragraph(mapping_text, styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Pricing Section
        story.append(Paragraph(content['pricing']['title'], heading_style))
        
        # Pricing table
        pricing_data = [[
            self._get_translation(quote.language, 'region'),
            self._get_translation(quote.language, 'pricing_model'),
            self._get_translation(quote.language, 'monthly_cost'),
            self._get_translation(quote.language, 'annual_cost')
        ]]
        
        for item in content['pricing']['items']:
            pricing_data.append([
                item['region'],
                item['pricing_model'],
                f"${item['monthly_cost']:.2f}",
                f"${item['annual_cost']:.2f}"
            ])
        
        pricing_table = Table(pricing_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        pricing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#232F3E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        story.append(pricing_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Total costs
        total_data = [
            [content['pricing']['total_monthly']['label'], 
             f"${content['pricing']['total_monthly']['value']:.2f} {content['pricing']['total_monthly']['currency']}"],
            [content['pricing']['total_annual']['label'], 
             f"${content['pricing']['total_annual']['value']:.2f} {content['pricing']['total_annual']['currency']}"]
        ]
        
        total_table = Table(total_data, colWidths=[3*inch, 3*inch])
        total_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFD700')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        story.append(total_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Service Descriptions
        if content['descriptions']['services']:
            story.append(Paragraph(content['descriptions']['title'], heading_style))
            
            for desc in content['descriptions']['services']:
                desc_text = f"<b>{desc['service']}:</b> {desc['description']}"
                story.append(Paragraph(desc_text, styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
            
            story.append(Spacer(1, 0.2*inch))
        
        # Benefits
        story.append(Paragraph(content['benefits']['title'], heading_style))
        
        for benefit in content['benefits']['items']:
            story.append(Paragraph(f"• {benefit}", styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Disclaimers
        story.append(Paragraph(content['disclaimers']['title'], heading_style))
        
        for disclaimer in content['disclaimers']['items']:
            story.append(Paragraph(f"• {disclaimer}", styles['Normal']))
        
        # Notes
        if content['notes']:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph(self._get_translation(quote.language, 'notes'), heading_style))
            story.append(Paragraph(content['notes'], styles['Normal']))
        
        # Build PDF
        doc.build(story)
    
    def _upload_to_s3(self, buffer: io.BytesIO, s3_key: str) -> str:
        """
        Upload PDF to S3 and generate presigned URL.
        
        Args:
            buffer: PDF buffer
            s3_key: S3 object key
        
        Returns:
            Presigned URL for download
        """
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=buffer.getvalue(),
                ContentType='application/pdf',
                ServerSideEncryption='AES256'
            )
            
            # Generate presigned URL (valid for 7 days)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=604800  # 7 days
            )
            
            return url
        except ClientError as e:
            logger.error(f"Failed to upload PDF to S3: {e}")
            raise
    
    def _format_dict(self, d: Dict[str, Any]) -> str:
        """Format dictionary as string."""
        items = [f"{k}: {v}" for k, v in d.items()]
        return ", ".join(items)
    
    def _get_translation(self, language: str, key: str) -> str:
        """Get translation for a key."""
        translations = {
            'en': {
                'region': 'Region',
                'pricing_model': 'Pricing Model',
                'monthly_cost': 'Monthly Cost',
                'annual_cost': 'Annual Cost',
                'created_date': 'Created Date',
                'status': 'Status',
                'notes': 'Notes'
            },
            'zh': {
                'region': '区域',
                'pricing_model': '定价模式',
                'monthly_cost': '月度费用',
                'annual_cost': '年度费用',
                'created_date': '创建日期',
                'status': '状态',
                'notes': '备注'
            }
        }
        
        return translations.get(language, translations['en']).get(key, key)

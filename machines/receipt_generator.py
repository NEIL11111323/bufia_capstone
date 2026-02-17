"""
PDF Receipt Generator using ReportLab
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from django.conf import settings
from django.utils import timezone
import os


class ReceiptGenerator:
    """Generate PDF receipts for rental payments"""
    
    def __init__(self, rental):
        self.rental = rental
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#019d66'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#019d66'),
            spaceAfter=12,
            spaceBefore=12
        ))
    
    def generate(self, filename=None):
        """Generate PDF receipt"""
        # Create receipts directory
        receipt_dir = os.path.join(settings.MEDIA_ROOT, 'receipts')
        os.makedirs(receipt_dir, exist_ok=True)
        
        # Generate filename
        if not filename:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f'receipt_rental_{self.rental.id}_{timestamp}.pdf'
        
        filepath = os.path.join(receipt_dir, filename)
        
        # Create PDF
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []
        
        # Header
        story.append(self._create_header())
        story.append(Spacer(1, 0.3*inch))
        
        # Title
        title = Paragraph("PAYMENT RECEIPT", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Receipt info
        story.append(self._create_receipt_info())
        story.append(Spacer(1, 0.3*inch))
        
        # Customer info
        story.append(Paragraph("Customer Information", self.styles['CustomHeading']))
        story.append(self._create_customer_info())
        story.append(Spacer(1, 0.2*inch))
        
        # Rental details
        story.append(Paragraph("Rental Details", self.styles['CustomHeading']))
        story.append(self._create_rental_details())
        story.append(Spacer(1, 0.2*inch))
        
        # Payment info
        story.append(Paragraph("Payment Information", self.styles['CustomHeading']))
        story.append(self._create_payment_info())
        story.append(Spacer(1, 0.3*inch))
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        story.append(self._create_footer())
        
        # Build PDF
        doc.build(story)
        
        return filepath
    
    def _create_header(self):
        """Create company header"""
        data = [
            [Paragraph("<b>BUFIA Inc.</b>", self.styles['Normal'])],
            [Paragraph("Bukidnon United Farmers Irrigators Association", self.styles['Normal'])],
            [Paragraph("Machine Rental Services", self.styles['Normal'])],
        ]
        
        table = Table(data, colWidths=[6*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#019d66')),
            ('FONTSIZE', (0, 0), (0, 0), 16),
        ]))
        
        return table
    
    def _create_receipt_info(self):
        """Create receipt number and date"""
        data = [
            ['Receipt No:', f'REC-{self.rental.id:06d}'],
            ['Date Issued:', timezone.now().strftime('%B %d, %Y %I:%M %p')],
            ['Status:', 'PAID' if self.rental.payment_verified else 'PENDING'],
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ]))
        
        return table
    
    def _create_customer_info(self):
        """Create customer information table"""
        user = self.rental.user
        data = [
            ['Name:', user.get_full_name() or user.username],
            ['Email:', user.email],
        ]
        
        table = Table(data, colWidths=[1.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return table
    
    def _create_rental_details(self):
        """Create rental details table"""
        data = [
            ['Machine:', self.rental.machine.name],
            ['Start Date:', self.rental.start_date.strftime('%B %d, %Y')],
            ['End Date:', self.rental.end_date.strftime('%B %d, %Y')],
            ['Duration:', f'{self.rental.get_duration_days()} day(s)'],
        ]
        
        table = Table(data, colWidths=[1.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return table
    
    def _create_payment_info(self):
        """Create payment information table"""
        amount = self.rental.payment_amount or 0
        
        data = [
            ['Payment Method:', self.rental.get_payment_method_display() if self.rental.payment_method else 'N/A'],
            ['Payment Date:', self.rental.payment_date.strftime('%B %d, %Y') if self.rental.payment_date else 'N/A'],
            ['', ''],
            ['Subtotal:', f'${amount:.2f}'],
            ['<b>Total Amount:</b>', f'<b>${amount:.2f}</b>'],
        ]
        
        table = Table(data, colWidths=[4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LINEABOVE', (0, 4), (-1, 4), 2, colors.HexColor('#019d66')),
            ('FONTSIZE', (0, 4), (-1, 4), 12),
            ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor('#019d66')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return table
    
    def _create_footer(self):
        """Create receipt footer"""
        footer_text = """
        <para align=center>
        <b>Important Information:</b><br/>
        Please present this receipt when picking up the machine.<br/>
        Thank you for choosing BUFIA Inc.!
        </para>
        """
        
        return Paragraph(footer_text, self.styles['Normal'])


def generate_rental_receipt(rental):
    """Convenience function to generate receipt"""
    generator = ReceiptGenerator(rental)
    return generator.generate()

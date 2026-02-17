# Complete Stripe Payment System with Automatic Receipt Generation

## System Overview

**Flow**: User rents machine → Pays via Stripe → Auto-generates PDF receipt → Sends to user & admin → Admin verifies & approves

## Requirements

```bash
pip install stripe reportlab pillow
```

Add to `requirements.txt`:
```
stripe==7.0.0
reportlab==4.0.7
pillow==10.1.0
```

## 1. Settings Configuration

### `bufia_project/settings.py`

```python
# Stripe Configuration
STRIPE_PUBLIC_KEY = 'pk_test_your_public_key_here'
STRIPE_SECRET_KEY = 'sk_test_your_secret_key_here'
STRIPE_WEBHOOK_SECRET = 'whsec_your_webhook_secret_here'

# For production, use environment variables:
# STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
# STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
# STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

# Email Configuration (for sending receipts)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'BUFIA Inc <noreply@bufia.com>'

# Media files (for storing receipts)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Receipt storage
RECEIPT_STORAGE_PATH = os.path.join(MEDIA_ROOT, 'receipts')
```

## 2. Receipt Generator

### Create `machines/receipt_generator.py`

```python
"""
PDF Receipt Generator using ReportLab
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
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
        """
        Generate PDF receipt
        
        Args:
            filename: Optional custom filename
            
        Returns:
            str: Path to generated PDF file
        """
        # Create receipts directory if it doesn't exist
        receipt_dir = settings.RECEIPT_STORAGE_PATH
        os.makedirs(receipt_dir, exist_ok=True)
        
        # Generate filename
        if not filename:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f'receipt_rental_{self.rental.id}_{timestamp}.pdf'
        
        filepath = os.path.join(receipt_dir, filename)
        
        # Create PDF
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build content
        story = []
        
        # Header
        story.append(self._create_header())
        story.append(Spacer(1, 0.3*inch))
        
        # Receipt title
        title = Paragraph("PAYMENT RECEIPT", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Receipt number and date
        story.append(self._create_receipt_info())
        story.append(Spacer(1, 0.3*inch))
        
        # Customer information
        story.append(Paragraph("Customer Information", self.styles['CustomHeading']))
        story.append(self._create_customer_info())
        story.append(Spacer(1, 0.2*inch))
        
        # Rental details
        story.append(Paragraph("Rental Details", self.styles['CustomHeading']))
        story.append(self._create_rental_details())
        story.append(Spacer(1, 0.2*inch))
        
        # Payment information
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
            ['Phone:', getattr(user, 'phone', 'N/A')],
        ]
        
        table = Table(data, colWidths=[1.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
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
            ['Purpose:', self.rental.purpose[:100] if self.rental.purpose else 'N/A'],
        ]
        
        table = Table(data, colWidths=[1.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
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
            ['Payment Date:', self.rental.payment_date.strftime('%B %d, %Y %I:%M %p') if self.rental.payment_date else 'N/A'],
            ['Transaction ID:', self.rental.stripe_session_id[:20] + '...' if self.rental.stripe_session_id else 'N/A'],
            ['', ''],
            ['Subtotal:', f'${amount:.2f}'],
            ['Tax (0%):', '$0.00'],
            ['<b>Total Amount:</b>', f'<b>${amount:.2f}</b>'],
        ]
        
        table = Table(data, colWidths=[4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, 2), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 4), (-1, -1), colors.HexColor('#f8f9fa')),
            ('LINEABOVE', (0, 4), (-1, 4), 1, colors.grey),
            ('LINEABOVE', (0, 6), (-1, 6), 2, colors.HexColor('#019d66')),
            ('FONTSIZE', (0, 6), (-1, 6), 12),
            ('TEXTCOLOR', (0, 6), (-1, 6), colors.HexColor('#019d66')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return table
    
    def _create_footer(self):
        """Create receipt footer"""
        footer_text = """
        <para align=center>
        <b>Important Information:</b><br/>
        Please present this receipt when picking up the machine.<br/>
        This receipt is valid only for the dates specified above.<br/>
        For questions or concerns, contact BUFIA Inc. at info@bufia.com<br/>
        <br/>
        <i>Thank you for choosing BUFIA Inc. Machine Rental Services!</i>
        </para>
        """
        
        return Paragraph(footer_text, self.styles['Normal'])


def generate_rental_receipt(rental):
    """
    Convenience function to generate receipt
    
    Args:
        rental: Rental instance
        
    Returns:
        str: Path to generated PDF file
    """
    generator = ReceiptGenerator(rental)
    return generator.generate()
```



## 3. Email Service for Sending Receipts

### Create `machines/email_service.py`

```python
"""
Email service for sending receipts
"""
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.auth import get_user_model
import os

User = get_user_model()


def send_receipt_email(rental, receipt_path):
    """
    Send receipt to user and admin
    
    Args:
        rental: Rental instance
        receipt_path: Path to PDF receipt file
        
    Returns:
        tuple: (user_sent: bool, admin_sent: bool)
    """
    user_sent = send_receipt_to_user(rental, receipt_path)
    admin_sent = send_receipt_to_admin(rental, receipt_path)
    
    return user_sent, admin_sent


def send_receipt_to_user(rental, receipt_path):
    """Send receipt to user"""
    try:
        subject = f'Payment Receipt - Machine Rental #{rental.id}'
        
        message = f"""
Dear {rental.user.get_full_name()},

Thank you for your payment! Your rental request has been received.

Rental Details:
- Machine: {rental.machine.name}
- Dates: {rental.start_date} to {rental.end_date}
- Duration: {rental.get_duration_days()} day(s)
- Amount Paid: ${rental.payment_amount}

Please find your payment receipt attached to this email.

IMPORTANT: Please present this receipt when picking up the machine.

Your rental is now pending admin approval. You will receive another notification once approved.

If you have any questions, please contact us.

Best regards,
BUFIA Inc. Team
        """
        
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[rental.user.email],
        )
        
        # Attach PDF receipt
        with open(receipt_path, 'rb') as f:
            email.attach(
                filename=os.path.basename(receipt_path),
                content=f.read(),
                mimetype='application/pdf'
            )
        
        email.send()
        return True
        
    except Exception as e:
        print(f"Error sending receipt to user: {str(e)}")
        return False


def send_receipt_to_admin(rental, receipt_path):
    """Send receipt to admin for verification"""
    try:
        # Get all admin users
        admins = User.objects.filter(is_staff=True)
        admin_emails = [admin.email for admin in admins if admin.email]
        
        if not admin_emails:
            print("No admin emails found")
            return False
        
        subject = f'New Rental Payment - Verification Required #{rental.id}'
        
        message = f"""
New rental payment received and requires verification:

Customer: {rental.user.get_full_name()} ({rental.user.email})
Machine: {rental.machine.name}
Dates: {rental.start_date} to {rental.end_date}
Duration: {rental.get_duration_days()} day(s)
Amount Paid: ${rental.payment_amount}
Payment Method: {rental.get_payment_method_display()}

Payment receipt is attached for your verification.

Please review and approve/reject this rental request in the admin dashboard:
{settings.SITE_URL}/machines/admin/rental/{rental.id}/approve/

Best regards,
BUFIA System
        """
        
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        
        # Attach PDF receipt
        with open(receipt_path, 'rb') as f:
            email.attach(
                filename=os.path.basename(receipt_path),
                content=f.read(),
                mimetype='application/pdf'
            )
        
        email.send()
        return True
        
    except Exception as e:
        print(f"Error sending receipt to admin: {str(e)}")
        return False
```

## 4. Updated Payment Views with Receipt Generation

### Update `bufia/views/payment_views.py`

```python
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from machines.models import Rental
from machines.receipt_generator import generate_rental_receipt
from machines.email_service import send_receipt_email
from notifications.models import UserNotification

# Import Stripe
try:
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
except ImportError:
    stripe = None
    print("WARNING: Stripe module not found")


@login_required
def create_rental_payment(request, rental_id):
    """Create Stripe Checkout session for rental payment"""
    rental = get_object_or_404(Rental, pk=rental_id, user=request.user)
    
    if stripe is None:
        messages.error(request, 'Payment system not configured')
        return redirect('machines:rental_detail', pk=rental_id)
    
    if rental.payment_verified:
        messages.info(request, 'Payment already verified')
        return redirect('machines:rental_detail', pk=rental_id)
    
    try:
        # Calculate amount
        duration_days = rental.get_duration_days()
        
        # Get price from machine
        try:
            import re
            price_str = str(rental.machine.current_price).replace('₱', '').replace('$', '').replace(',', '').strip()
            price_match = re.search(r'\d+\.?\d*', price_str)
            price_value = float(price_match.group()) if price_match else 100.0
        except:
            price_value = 100.0
        
        amount = int(price_value * duration_days * 100)  # Convert to cents
        
        # Store amount in rental
        rental.payment_amount = price_value * duration_days
        rental.save()
        
        # Create Stripe Checkout Session
        success_url = request.build_absolute_uri(reverse('payment_success'))
        success_url += f'?session_id={{CHECKOUT_SESSION_ID}}&type=rental&id={rental_id}'
        
        cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))
        cancel_url += f'?type=rental&id={rental_id}'
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': amount,
                    'product_data': {
                        'name': f'Machine Rental: {rental.machine.name}',
                        'description': f'{rental.start_date} to {rental.end_date} ({duration_days} days)',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'rental_id': rental_id,
                'user_id': request.user.id,
                'type': 'rental'
            }
        )
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        messages.error(request, f'Error creating payment: {str(e)}')
        return redirect('machines:rental_detail', pk=rental_id)


@login_required
def payment_success(request):
    """Handle successful payment with receipt generation"""
    session_id = request.GET.get('session_id')
    payment_type = request.GET.get('type')
    item_id = request.GET.get('id')
    
    if not session_id:
        messages.error(request, 'Invalid payment session')
        return redirect('dashboard')
    
    try:
        # Retrieve session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid' and payment_type == 'rental':
            rental = get_object_or_404(Rental, pk=item_id, user=request.user)
            
            # Update rental with payment info
            rental.payment_verified = True
            rental.payment_method = 'online'
            rental.payment_date = timezone.now()
            rental.stripe_session_id = session_id
            rental.save()
            
            # Generate PDF receipt
            try:
                receipt_path = generate_rental_receipt(rental)
                
                # Send receipt to user and admin
                user_sent, admin_sent = send_receipt_email(rental, receipt_path)
                
                if user_sent:
                    messages.success(
                        request,
                        '✅ Payment successful! Receipt sent to your email.'
                    )
                else:
                    messages.warning(
                        request,
                        '✅ Payment successful! But failed to send receipt email.'
                    )
                
            except Exception as e:
                print(f"Error generating/sending receipt: {str(e)}")
                messages.warning(
                    request,
                    '✅ Payment successful! But failed to generate receipt.'
                )
            
            # Notify user
            UserNotification.objects.create(
                user=request.user,
                notification_type='rental_payment_completed',
                message=f'Payment received for {rental.machine.name}. Your rental is pending admin approval.',
                related_object_id=rental.id
            )
            
            # Notify admins
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(is_staff=True)
            for admin in admins:
                UserNotification.objects.create(
                    user=admin,
                    notification_type='rental_payment_received',
                    message=f'Payment received for rental from {request.user.get_full_name()} for {rental.machine.name}',
                    related_object_id=rental.id
                )
            
            return redirect('machines:rental_detail', pk=item_id)
        
        else:
            messages.warning(request, 'Payment is being processed')
            
    except Exception as e:
        messages.error(request, f'Error verifying payment: {str(e)}')
    
    return redirect('dashboard')


@login_required
def download_receipt(request, rental_id):
    """Download receipt PDF"""
    rental = get_object_or_404(Rental, pk=rental_id)
    
    # Check permissions
    if rental.user != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this receipt")
        return redirect('machines:rental_list')
    
    try:
        # Generate receipt
        receipt_path = generate_rental_receipt(rental)
        
        # Return PDF file
        return FileResponse(
            open(receipt_path, 'rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=f'receipt_rental_{rental.id}.pdf'
        )
        
    except Exception as e:
        messages.error(request, f'Error generating receipt: {str(e)}')
        return redirect('machines:rental_detail', pk=rental_id)


@login_required
def view_receipt(request, rental_id):
    """View receipt in browser"""
    rental = get_object_or_404(Rental, pk=rental_id)
    
    # Check permissions
    if rental.user != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this receipt")
        return redirect('machines:rental_list')
    
    try:
        # Generate receipt
        receipt_path = generate_rental_receipt(rental)
        
        # Return PDF for viewing
        return FileResponse(
            open(receipt_path, 'rb'),
            content_type='application/pdf'
        )
        
    except Exception as e:
        messages.error(request, f'Error generating receipt: {str(e)}')
        return redirect('machines:rental_detail', pk=rental_id)


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    # Handle checkout.session.completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        
        if metadata.get('type') == 'rental':
            rental_id = metadata.get('rental_id')
            
            try:
                rental = Rental.objects.get(pk=rental_id)
                rental.payment_verified = True
                rental.payment_method = 'online'
                rental.payment_date = timezone.now()
                rental.stripe_session_id = session.get('id')
                rental.save()
                
                # Generate and send receipt
                try:
                    receipt_path = generate_rental_receipt(rental)
                    send_receipt_email(rental, receipt_path)
                except Exception as e:
                    print(f"Webhook: Error generating receipt: {str(e)}")
                    
            except Rental.DoesNotExist:
                pass
    
    return HttpResponse(status=200)
```



## 5. URL Configuration

### Add to `bufia_project/urls.py` (main URLs)

```python
from django.urls import path, include
from bufia.views import payment_views

urlpatterns = [
    # ... existing patterns ...
    
    # Payment URLs
    path('payment/rental/<int:rental_id>/', payment_views.create_rental_payment, name='create_rental_payment'),
    path('payment/success/', payment_views.payment_success, name='payment_success'),
    path('payment/cancelled/', payment_views.payment_cancelled, name='payment_cancelled'),
    path('payment/webhook/', payment_views.stripe_webhook, name='stripe_webhook'),
    
    # Receipt URLs
    path('receipt/<int:rental_id>/download/', payment_views.download_receipt, name='download_receipt'),
    path('receipt/<int:rental_id>/view/', payment_views.view_receipt, name='view_receipt'),
]
```

## 6. Template for Receipt Button

### Add to `templates/machines/rental_detail.html`

```html
<!-- Payment & Receipt Section -->
<div class="card mb-4">
    <div class="card-header">
        <h5><i class="fas fa-receipt"></i> Payment & Receipt</h5>
    </div>
    <div class="card-body">
        {% if rental.payment_verified %}
            <!-- Payment Verified -->
            <div class="alert alert-success">
                <i class="fas fa-check-circle"></i> Payment Verified
                <br><small>Paid on: {{ rental.payment_date|date:"M d, Y h:i A" }}</small>
            </div>
            
            <!-- Receipt Buttons -->
            <div class="d-grid gap-2">
                <a href="{% url 'view_receipt' rental.id %}" 
                   target="_blank" 
                   class="btn btn-primary">
                    <i class="fas fa-eye"></i> View Receipt
                </a>
                <a href="{% url 'download_receipt' rental.id %}" 
                   class="btn btn-outline-primary">
                    <i class="fas fa-download"></i> Download Receipt (PDF)
                </a>
            </div>
            
            <div class="alert alert-info mt-3">
                <i class="fas fa-info-circle"></i> 
                <strong>Important:</strong> Please present this receipt when picking up the machine.
            </div>
            
        {% else %}
            <!-- Payment Pending -->
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i> Payment Pending
            </div>
            
            {% if rental.status == 'pending' %}
            <a href="{% url 'create_rental_payment' rental.id %}" 
               class="btn btn-success btn-lg w-100">
                <i class="fas fa-credit-card"></i> Complete Payment
            </a>
            {% endif %}
        {% endif %}
    </div>
</div>
```

## 7. Testing in Stripe Test Mode

### Test Card Numbers

```
Success: 4242 4242 4242 4242
Decline: 4000 0000 0000 0002
Requires Authentication: 4000 0025 0000 3155

Expiry: Any future date (e.g., 12/25)
CVC: Any 3 digits (e.g., 123)
ZIP: Any 5 digits (e.g., 12345)
```

### Testing Workflow

1. **User creates rental**
   ```
   POST /machines/rentals/create/
   ```

2. **User clicks "Complete Payment"**
   ```
   GET /payment/rental/1/
   → Redirects to Stripe Checkout
   ```

3. **User enters test card**
   ```
   Card: 4242 4242 4242 4242
   Expiry: 12/25
   CVC: 123
   ```

4. **Payment succeeds**
   ```
   → Redirects to /payment/success/
   → Generates PDF receipt
   → Sends email to user
   → Sends email to admin
   → Updates rental.payment_verified = True
   ```

5. **User downloads receipt**
   ```
   GET /receipt/1/download/
   → Downloads PDF
   ```

6. **Admin receives email with receipt**
   ```
   Subject: New Rental Payment - Verification Required #1
   Attachment: receipt_rental_1_20241202_103045.pdf
   ```

7. **Admin approves rental**
   ```
   POST /machines/admin/rental/1/approve/
   → Status: approved
   → User can pick up machine with receipt
   ```

## 8. Webhook Configuration

### In Stripe Dashboard

1. Go to: https://dashboard.stripe.com/test/webhooks
2. Click "Add endpoint"
3. Enter URL: `https://yourdomain.com/payment/webhook/`
4. Select events:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
5. Copy webhook secret to settings.py

### Local Testing with Stripe CLI

```bash
# Install Stripe CLI
# https://stripe.com/docs/stripe-cli

# Login
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/payment/webhook/

# Test webhook
stripe trigger checkout.session.completed
```

## 9. Email Template (Optional Enhancement)

### Create `templates/emails/receipt_email.html`

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #019d66; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .button { background: #019d66; color: white; padding: 12px 24px; text-decoration: none; display: inline-block; border-radius: 4px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Payment Receipt</h1>
            <p>BUFIA Inc. Machine Rental Services</p>
        </div>
        
        <div class="content">
            <h2>Dear {{ rental.user.get_full_name }},</h2>
            
            <p>Thank you for your payment! Your rental request has been received.</p>
            
            <h3>Rental Details:</h3>
            <ul>
                <li><strong>Machine:</strong> {{ rental.machine.name }}</li>
                <li><strong>Dates:</strong> {{ rental.start_date }} to {{ rental.end_date }}</li>
                <li><strong>Duration:</strong> {{ rental.get_duration_days }} day(s)</li>
                <li><strong>Amount Paid:</strong> ${{ rental.payment_amount }}</li>
            </ul>
            
            <p><strong>IMPORTANT:</strong> Please present the attached receipt when picking up the machine.</p>
            
            <p>Your rental is now pending admin approval. You will receive another notification once approved.</p>
            
            <p style="text-align: center; margin-top: 30px;">
                <a href="{{ site_url }}/machines/rentals/{{ rental.id }}/" class="button">
                    View Rental Details
                </a>
            </p>
        </div>
        
        <div class="footer">
            <p>If you have any questions, please contact us at info@bufia.com</p>
            <p>&copy; 2024 BUFIA Inc. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
```

## 10. Installation & Setup

### Step 1: Install Dependencies

```bash
pip install stripe reportlab pillow
```

### Step 2: Update Settings

```python
# settings.py
STRIPE_PUBLIC_KEY = 'pk_test_...'
STRIPE_SECRET_KEY = 'sk_test_...'
STRIPE_WEBHOOK_SECRET = 'whsec_...'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

### Step 3: Create Receipt Generator

```bash
# Create the file
touch machines/receipt_generator.py

# Copy the code from section 2
```

### Step 4: Create Email Service

```bash
# Create the file
touch machines/email_service.py

# Copy the code from section 3
```

### Step 5: Update Payment Views

```bash
# Update bufia/views/payment_views.py
# Copy the code from section 4
```

### Step 6: Add URLs

```bash
# Update bufia_project/urls.py
# Add the URLs from section 5
```

### Step 7: Test

```bash
# Run server
python manage.py runserver

# Test payment flow
# Use test card: 4242 4242 4242 4242
```

## 11. Troubleshooting

### Issue: Receipt not generating

**Solution:**
```bash
# Check if reportlab is installed
pip show reportlab

# Check if receipts directory exists
mkdir -p media/receipts

# Check file permissions
chmod 755 media/receipts
```

### Issue: Email not sending

**Solution:**
```python
# Test email configuration
python manage.py shell

from django.core.mail import send_mail
send_mail(
    'Test',
    'Test message',
    'from@example.com',
    ['to@example.com'],
)
```

### Issue: Stripe webhook not working

**Solution:**
```bash
# Use Stripe CLI for local testing
stripe listen --forward-to localhost:8000/payment/webhook/

# Check webhook secret matches
echo $STRIPE_WEBHOOK_SECRET
```

## 12. Production Checklist

- [ ] Use environment variables for Stripe keys
- [ ] Set up proper email service (SendGrid, AWS SES)
- [ ] Configure webhook endpoint with HTTPS
- [ ] Test with real Stripe account (not test mode)
- [ ] Set up error logging (Sentry)
- [ ] Configure file storage (AWS S3 for receipts)
- [ ] Add receipt archiving (delete old receipts)
- [ ] Set up monitoring for failed payments
- [ ] Add retry logic for failed emails
- [ ] Test webhook signature verification

---

**System Status**: ✅ COMPLETE  
**Features**: Stripe Payment + Auto Receipt + Email to User & Admin  
**Ready for**: Testing in Stripe Test Mode  
**Date**: December 2, 2024

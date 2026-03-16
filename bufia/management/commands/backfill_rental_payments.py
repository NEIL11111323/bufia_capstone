"""
Management command to backfill Payment objects for existing rentals

Usage:
    python manage.py backfill_rental_payments
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from machines.models import Rental
from bufia.models import Payment
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create Payment objects for rentals that have payment_verified=True but no Payment object'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all rentals with payment_verified=True
        verified_rentals = Rental.objects.filter(payment_verified=True)
        
        # Get content type for Rental
        content_type = ContentType.objects.get_for_model(Rental)
        
        # Find rentals without Payment objects
        rentals_with_payments = Payment.objects.filter(
            content_type=content_type
        ).values_list('object_id', flat=True)
        
        rentals_without_payments = verified_rentals.exclude(
            id__in=rentals_with_payments
        )
        
        total_count = rentals_without_payments.count()
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('All verified rentals already have Payment objects'))
            return
        
        self.stdout.write(f'Found {total_count} verified rentals without Payment objects')
        self.stdout.write('Creating Payment objects...\n')
        
        processed = 0
        errors = 0
        
        for rental in rentals_without_payments:
            try:
                if dry_run:
                    self.stdout.write(
                        f'Would create Payment for Rental #{rental.id} (User: {rental.user.username})'
                    )
                else:
                    with transaction.atomic():
                        payment, created = Payment.objects.get_or_create(
                            content_type=content_type,
                            object_id=rental.id,
                            defaults={
                                'user': rental.user,
                                'payment_type': 'rental',
                                'amount': rental.payment_amount or 0,
                                'currency': 'PHP',
                                'status': 'completed',
                                'stripe_session_id': rental.stripe_session_id,
                                'paid_at': rental.payment_date,
                            }
                        )
                        
                        if created:
                            self.stdout.write(
                                f'✓ Created Payment #{payment.id} for Rental #{rental.id} '
                                f'(Transaction ID: {payment.internal_transaction_id})'
                            )
                        else:
                            self.stdout.write(
                                f'- Payment already exists for Rental #{rental.id}'
                            )
                
                processed += 1
                
            except Exception as e:
                errors += 1
                logger.error(f'Error processing Rental #{rental.id}: {str(e)}')
                self.stdout.write(
                    self.style.ERROR(f'Error processing Rental #{rental.id}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'DRY RUN COMPLETE'))
            self.stdout.write(f'Would process: {processed} rentals')
        else:
            self.stdout.write(self.style.SUCCESS(f'BACKFILL COMPLETE'))
            self.stdout.write(f'Successfully processed: {processed} rentals')
        
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'Errors encountered: {errors}'))
        
        self.stdout.write('='*50)

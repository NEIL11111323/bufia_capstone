"""
Management command to backfill internal transaction IDs for existing payments

Usage:
    python manage.py generate_transaction_ids
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from bufia.models import Payment
from bufia.utils.transaction_id import TransactionIDGenerator
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate internal transaction IDs for existing payments'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of payments to process in each batch (default: 1000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database'
        )
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all payments without internal transaction IDs, ordered by created_at
        payments_without_ids = Payment.objects.filter(
            internal_transaction_id__isnull=True
        ).order_by('created_at')
        
        total_count = payments_without_ids.count()
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('All payments already have internal transaction IDs'))
            return
        
        self.stdout.write(f'Found {total_count} payments without internal transaction IDs')
        self.stdout.write(f'Processing in batches of {batch_size}...\n')
        
        processed = 0
        errors = 0
        
        # Process payments in batches
        while True:
            batch = list(payments_without_ids[:batch_size])
            
            if not batch:
                break
            
            for payment in batch:
                try:
                    if dry_run:
                        # Just simulate ID generation
                        transaction_id = TransactionIDGenerator.generate()
                        self.stdout.write(
                            f'Would assign {transaction_id} to Payment #{payment.id}'
                        )
                    else:
                        # Generate and assign transaction ID
                        with transaction.atomic():
                            # Use the payment's created_at year for the transaction ID
                            if payment.created_at:
                                year = payment.created_at.year
                            else:
                                # Fallback to current year if no timestamp
                                year = timezone.now().year
                                logger.warning(
                                    f'Payment #{payment.id} has no created_at timestamp, '
                                    f'using current year {year}'
                                )
                            
                            # Get next sequence number for this year
                            sequence = TransactionIDGenerator.get_next_sequence_number(year)
                            transaction_id = TransactionIDGenerator._format_transaction_id(
                                year, sequence
                            )
                            
                            # Assign to payment
                            payment.internal_transaction_id = transaction_id
                            payment.save(update_fields=['internal_transaction_id'])
                    
                    processed += 1
                    
                    if processed % 100 == 0:
                        self.stdout.write(f'Processed {processed}/{total_count} payments...')
                
                except Exception as e:
                    errors += 1
                    logger.error(f'Error processing Payment #{payment.id}: {str(e)}')
                    self.stdout.write(
                        self.style.ERROR(f'Error processing Payment #{payment.id}: {str(e)}')
                    )
            
            # Refresh the queryset for next batch
            payments_without_ids = Payment.objects.filter(
                internal_transaction_id__isnull=True
            ).order_by('created_at')
        
        # Summary
        self.stdout.write('\n' + '='*50)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'DRY RUN COMPLETE'))
            self.stdout.write(f'Would process: {processed} payments')
        else:
            self.stdout.write(self.style.SUCCESS(f'BACKFILL COMPLETE'))
            self.stdout.write(f'Successfully processed: {processed} payments')
        
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'Errors encountered: {errors}'))
        
        self.stdout.write('='*50)

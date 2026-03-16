from django.core.management.base import BaseCommand
from machines.models import Rental


class Command(BaseCommand):
    help = 'Calculate and update payment amounts for all rentals based on land area'

    def handle(self, *args, **options):
        rentals = Rental.objects.all()
        updated_count = 0
        
        for rental in rentals:
            if rental.area and rental.area > 0:
                # Calculate payment: area × 4000
                calculated_amount = float(rental.area) * 4000
                
                # Update if different or not set
                if rental.payment_amount != calculated_amount:
                    rental.payment_amount = calculated_amount
                    rental.save(update_fields=['payment_amount'])
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated Rental #{rental.id}: {rental.area} ha × ₱4,000 = ₱{calculated_amount:,.2f}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully updated {updated_count} rental(s) with calculated payment amounts'
            )
        )

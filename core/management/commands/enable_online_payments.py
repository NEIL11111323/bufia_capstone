"""
Django management command to enable online payment for all machines
"""
from django.core.management.base import BaseCommand
from machines.models import Machine


class Command(BaseCommand):
    help = 'Enable online payment (GCash) for all cash-type machines'

    def handle(self, *args, **options):
        self.stdout.write('='*60)
        self.stdout.write('ENABLING ONLINE PAYMENT FOR ALL MACHINES')
        self.stdout.write('='*60)
        self.stdout.write('')

        machines = Machine.objects.all()

        if not machines.exists():
            self.stdout.write(self.style.WARNING('⚠️  No machines found in database!'))
            self.stdout.write('Please create machines first through the admin panel.')
            return

        updated_count = 0
        for machine in machines:
            needs_update = False
            
            # Only update cash payment machines
            if machine.rental_price_type == 'cash':
                if not machine.allow_online_payment:
                    machine.allow_online_payment = True
                    needs_update = True
                
                if not machine.allow_face_to_face_payment:
                    machine.allow_face_to_face_payment = True
                    needs_update = True
                
                if needs_update:
                    machine.save()
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Updated: {machine.name}'))
                    self.stdout.write(f'  - Online Payment: {machine.allow_online_payment}')
                    self.stdout.write(f'  - OTC Payment: {machine.allow_face_to_face_payment}')
                    self.stdout.write('')
                else:
                    self.stdout.write(self.style.SUCCESS(f'✓ Already enabled: {machine.name}'))
                    self.stdout.write('')
            else:
                self.stdout.write(f'⊘ Skipped (in-kind): {machine.name}')
                self.stdout.write('')
        
        self.stdout.write('='*60)
        self.stdout.write('SUMMARY')
        self.stdout.write('='*60)
        self.stdout.write(f'Total machines: {machines.count()}')
        self.stdout.write(f'Updated: {updated_count}')
        self.stdout.write('='*60)
        
        if updated_count > 0:
            self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully enabled online payment for {updated_count} machine(s)'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ All machines already have online payment enabled'))

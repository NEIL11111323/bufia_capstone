# Data migration to populate 10 sectors

from django.db import migrations


def populate_sectors(apps, schema_editor):
    """Assign sector numbers to existing sectors and create missing ones"""
    Sector = apps.get_model('users', 'Sector')
    
    # Define the 10 sectors we want
    sectors_data = [
        (1, 'North District', 'Northern farming area', 'Covers northern barangays'),
        (2, 'South District', 'Southern farming area', 'Covers southern barangays'),
        (3, 'East District', 'Eastern farming area', 'Covers eastern barangays'),
        (4, 'West District', 'Western farming area', 'Covers western barangays'),
        (5, 'Central District', 'Central farming area', 'Covers central barangays'),
        (6, 'Northeast District', 'Northeast farming area', 'Covers northeast barangays'),
        (7, 'Northwest District', 'Northwest farming area', 'Covers northwest barangays'),
        (8, 'Southeast District', 'Southeast farming area', 'Covers southeast barangays'),
        (9, 'Southwest District', 'Southwest farming area', 'Covers southwest barangays'),
        (10, 'Upland District', 'Upland farming area', 'Covers upland barangays'),
    ]
    
    # Get existing sectors
    existing_sectors = list(Sector.objects.all().order_by('id'))
    
    # Assign sector numbers to existing sectors or create new ones
    for idx, (sector_number, name, description, area_coverage) in enumerate(sectors_data):
        # Try to find existing sector by name
        existing = Sector.objects.filter(name=name).first()
        
        if existing:
            # Update existing sector
            existing.sector_number = sector_number
            existing.description = description
            existing.area_coverage = area_coverage
            existing.is_active = True
            existing.save()
        elif idx < len(existing_sectors):
            # Reuse an existing sector without sector_number
            sector = existing_sectors[idx]
            sector.sector_number = sector_number
            sector.name = name
            sector.description = description
            sector.area_coverage = area_coverage
            sector.is_active = True
            sector.save()
        else:
            # Create new sector
            Sector.objects.create(
                sector_number=sector_number,
                name=name,
                description=description,
                area_coverage=area_coverage,
                is_active=True,
            )
    
    # Deactivate any extra sectors beyond the 10 we need
    Sector.objects.filter(sector_number__isnull=True).update(is_active=False)


def reverse_populate_sectors(apps, schema_editor):
    """Remove the populated sectors"""
    Sector = apps.get_model('users', 'Sector')
    Sector.objects.filter(sector_number__in=range(1, 11)).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_add_sector_tracking'),
    ]

    operations = [
        migrations.RunPython(populate_sectors, reverse_populate_sectors),
    ]

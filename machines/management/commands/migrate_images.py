import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from machines.models import Machine, MachineImage
from django.utils.text import slugify
from django.utils import timezone

class Command(BaseCommand):
    help = 'Migrates existing machine images to the new directory structure'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting image migration...'))
        
        # Create directories if they don't exist
        machine_images_dir = os.path.join(settings.MEDIA_ROOT, 'machines', 'images')
        thumbnails_dir = os.path.join(settings.MEDIA_ROOT, 'machines', 'thumbnails')
        
        if not os.path.exists(machine_images_dir):
            os.makedirs(machine_images_dir)
        
        if not os.path.exists(thumbnails_dir):
            os.makedirs(thumbnails_dir)
        
        # Migrate Machine.image fields
        self.stdout.write('Migrating direct Machine images...')
        migrated_direct_images = 0
        
        for machine in Machine.objects.all():
            if machine.image and hasattr(machine.image, 'path'):
                try:
                    # Get the source file path
                    source_path = machine.image.path
                    
                    if not os.path.exists(source_path):
                        self.stdout.write(self.style.WARNING(f"Source image not found for machine {machine.id}: {source_path}"))
                        continue
                    
                    # Generate the new file name
                    file_name = os.path.basename(machine.image.name)
                    file_ext = os.path.splitext(file_name)[1]
                    slug = slugify(machine.name)
                    new_file_name = f"{slug}_{machine.id}{file_ext}"
                    
                    # Create destination path
                    dest_dir = os.path.join(machine_images_dir)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    
                    dest_path = os.path.join(dest_dir, new_file_name)
                    
                    # Copy the file
                    shutil.copy2(source_path, dest_path)
                    
                    # Update the model
                    machine.image.name = os.path.join('machines/images', new_file_name)
                    machine.save(update_fields=['image'])
                    
                    migrated_direct_images += 1
                    self.stdout.write(f"Migrated image for machine {machine.id}: {machine.name}")
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error migrating image for machine {machine.id}: {e}"))
        
        # Migrate MachineImage instances
        self.stdout.write('Migrating MachineImage instances...')
        migrated_related_images = 0
        
        for machine_image in MachineImage.objects.all():
            if machine_image.image and hasattr(machine_image.image, 'path'):
                try:
                    # Get the source file path
                    source_path = machine_image.image.path
                    
                    if not os.path.exists(source_path):
                        self.stdout.write(self.style.WARNING(f"Source image not found for MachineImage {machine_image.id}: {source_path}"))
                        continue
                    
                    # Generate the new file name
                    file_name = os.path.basename(machine_image.image.name)
                    file_ext = os.path.splitext(file_name)[1]
                    machine_slug = slugify(machine_image.machine.name)
                    unique_id = timezone.now().strftime('%Y%m%d%H%M%S')
                    new_file_name = f"{machine_slug}_{unique_id}{file_ext}"
                    
                    # Create destination path
                    dest_dir = os.path.join(machine_images_dir, machine_slug)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    
                    dest_path = os.path.join(dest_dir, new_file_name)
                    
                    # Copy the file
                    shutil.copy2(source_path, dest_path)
                    
                    # Update the model
                    machine_image.image.name = os.path.join('machines/images', machine_slug, new_file_name)
                    machine_image.save(update_fields=['image'])
                    
                    migrated_related_images += 1
                    self.stdout.write(f"Migrated MachineImage {machine_image.id} for machine {machine_image.machine.name}")
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error migrating MachineImage {machine_image.id}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f'Image migration complete! Migrated {migrated_direct_images} direct images and {migrated_related_images} related images.')) 
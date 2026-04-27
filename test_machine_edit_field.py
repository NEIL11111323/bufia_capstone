#!/usr/bin/env python
"""
Test machine edit form to verify machine_type field appears
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bufia.settings')
django.setup()

from machines.models import Machine
from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model

User = get_user_model()

def test_machine_edit_field():
    print("🔍 Testing Machine Edit Form - Machine Type Field")
    print("=" * 60)
    
    # Get a regular machine (not dryer)
    machine = Machine.objects.filter(machine_type='tractor_4wd').first()
    
    if not machine:
        print("❌ No tractor machine found for testing")
        return
    
    print(f"\n📊 Testing Machine:")
    print(f"   ID: {machine.id}")
    print(f"   Name: {machine.name}")
    print(f"   Type: {machine.machine_type}")
    print(f"   Is Dryer: {machine.is_dryer_service()}")
    
    # Get an admin user
    admin = User.objects.filter(is_staff=True).first()
    
    if not admin:
        print("❌ No admin user found for testing")
        return
    
    print(f"\n👤 Testing with admin: {admin.username}")
    
    # Create a test client and login
    client = Client()
    client.force_login(admin)
    
    # Access the edit page
    url = f'/machines/{machine.id}/edit/'
    print(f"\n🌐 Accessing: {url}")
    
    response = client.get(url)
    print(f"   Response status: {response.status_code}")
    
    if response.status_code == 200:
        content = response.content.decode()
        
        # Check for machine_type field
        has_machine_type_id = 'id_machine_type' in content
        has_machine_type_label = 'Machine Type' in content or 'machine_type' in content
        has_show_field_true = 'show_machine_type_field' in content
        
        print(f"\n🔍 Field Checks:")
        print(f"   Has id_machine_type: {has_machine_type_id}")
        print(f"   Has machine_type label: {has_machine_type_label}")
        print(f"   Has show_machine_type_field variable: {has_show_field_true}")
        
        # Check if field is visible (not hidden)
        is_hidden = 'type="hidden"' in content and 'name="machine_type"' in content
        print(f"   Field is hidden: {is_hidden}")
        
        # Check context variables
        if 'is_dryer_setup_flow' in content:
            print(f"   ⚠️ is_dryer_setup_flow found in content")
        
        if has_machine_type_id and not is_hidden:
            print(f"\n✅ Machine type field is visible!")
        elif is_hidden:
            print(f"\n❌ Machine type field is hidden (should be visible for regular machines)")
        else:
            print(f"\n❌ Machine type field not found in form")
            
        # Show a snippet of the form
        if 'id_machine_type' in content:
            start = content.find('id_machine_type') - 100
            end = content.find('id_machine_type') + 200
            snippet = content[max(0, start):min(len(content), end)]
            print(f"\n📝 Form snippet around machine_type:")
            print(f"   ...{snippet}...")
    else:
        print(f"   ❌ Failed to load page")
    
    print(f"\n🎯 Summary:")
    print(f"   The machine_type field should be visible for regular machines")
    print(f"   It should only be hidden for dryer setup flow")
    print(f"   Current machine is NOT a dryer, so field should be visible")

if __name__ == '__main__':
    test_machine_edit_field()
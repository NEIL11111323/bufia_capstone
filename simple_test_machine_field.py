import requests

r = requests.get('http://127.0.0.1:8000/machines/21/edit/', timeout=10)
content = r.text

print('Status:', r.status_code)
print('Has select machine_type:', 'select name="machine_type"' in content)
print('Has hidden machine_type:', 'type="hidden" name="machine_type"' in content)

# Find the machine_type field
if 'id_machine_type' in content:
    idx = content.find('id_machine_type')
    snippet = content[max(0, idx-200):min(len(content), idx+300)]
    print('\nField snippet:')
    print(snippet[:500])

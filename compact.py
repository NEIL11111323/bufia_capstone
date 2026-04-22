import os
import re

files_to_update = [
    'templates/machines/machine_list.html',
    'templates/machines/maintenance_list.html',
    'templates/machines/admin/rental_dashboard.html',
    'templates/machines/ricemill_appointment_list.html',
    'templates/machines/dryer_rental_list.html',
    'templates/machines/admin/operator_overview.html',
    'templates/irrigation/admin_request_list.html'
]

pattern = re.compile(
    r'<(?:section|div) class="(?:[^"]*?)app-page__header(?:[^"]*?)">\s*'
    r'<div class="app-page__heading">\s*'
    r'(?:<span class="page-header__eyebrow">.*?</span>\s*)?'
    r'<h[1-6] class="app-page__title[^"]*">(.*?)</h[1-6]>\s*'
    r'<p class="app-page__subtitle[^"]*">.*?</p>\s*'
    r'</div>\s*'
    r'(<div class="app-page__actions">.*?</div>\s*)?'
    r'</(?:section|div)>',
    re.DOTALL
)

for fpath in files_to_update:
    if not os.path.exists(fpath):
        print(f"MISSING: {fpath}")
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    def repl(m):
        title = m.group(1).strip()
        actions = m.group(2) if m.group(2) else ''
        return f'''    <section class="page-header app-page__header d-flex flex-wrap align-items-center justify-content-between mb-3" style="padding-top: 5px;">
        <h1 class="app-page__title mb-0 fs-5">{title}</h1>
        {actions}</section>'''

    new_content, count = pattern.subn(repl, content)
    if count > 0:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"UPDATED: {fpath}")
    else:
        print(f"NO MATCH: {fpath}")

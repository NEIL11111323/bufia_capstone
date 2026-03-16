---
inclusion: always
---

# Django Best Practices and Standards

## Project Structure

- Use `bufia` as the main project package with `settings.py`, `urls.py`, `wsgi.py`
- Place reusable components in `core` app
- Feature-specific apps: `machines`, `users`, `activity_logs`, `notifications`, `irrigation`, `reports`, `general_reports`, `flow`

## Models

- Define `__str__` method for all models
- Use `get_absolute_url` for models that need URLs
- Add `created_at` and `updated_at` timestamps to all models
- Use `choices` for enum-like fields
- Index foreign keys and frequently queried fields

## Views and URLs

- Use class-based views (CBV) for standard CRUD operations
- Use function-based views only for simple or custom logic
- Always use `LoginRequiredMixin` for views requiring authentication
- Use `UserPassesTestMixin` for permission checks
- Keep URL patterns RESTful and descriptive

## Forms

- Use `ModelForm` when working with model data
- Validate data in `clean()` methods
- Use `widgets` for custom field rendering
- Add help text for user guidance

## Templates

- Extend from `base.html` template
- Use template tags for reusable logic
- Avoid business logic in templates
- Use `{% url %}` tag for all links

## Admin

- Register models with custom `ModelAdmin` classes
- Use `list_display`, `list_filter`, `search_fields`
- Add `readonly_fields` for computed values
- Use `actions` for bulk operations

## Settings

- Use environment variables for sensitive data
- Separate development and production settings
- Keep `SECRET_KEY` out of version control
- Use `python-decouple` or similar for config management

## Testing

- Use Django's `TestCase` for model and view tests
- Use `Client` for view testing
- Aim for meaningful test coverage
- Test edge cases and error conditions
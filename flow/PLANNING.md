# BUFIA Management System - Planning

## 📋 Project Overview
The BUFIA (Bawayan United Farmers Irrigations Incorporated) Management System is a web-based solution for managing machine rentals, rice mill operations, user verification, and administrative tasks. The system aims to streamline operations for the farmers' association and ensure only verified members can access privileged features.

## 🏗️ Architecture

### System Components
1. **User Management Module**
   - Authentication & authorization
   - Role-based access (President, Superuser, Regular User)
   - Membership verification system
   - Profile management

2. **Machine Rental Module**
   - Machine inventory
   - Rental scheduling
   - Status tracking
   - Maintenance records

3. **Rice Mill Module**
   - Scheduling system
   - Processing capacity tracking
   - Usage statistics

4. **Notifications Module**
   - System alerts
   - Status updates
   - Email notifications

5. **Reporting Module**
   - Usage statistics
   - Financial reports
   - Export functionality

### Data Models

#### Users
- `CustomUser`: Extends Django's AbstractUser with role and verification fields
- `MembershipApplication`: Stores detailed membership application information

#### Machines
- `Machine`: Core machine inventory model
- `Rental`: Records of machine rentals
- `Maintenance`: Machine maintenance records

#### Rice Mill
- `Schedule`: Rice mill scheduling records
- `Processing`: Rice processing records

## 🔒 Access Control System

### Role-Based Access
- **President**: Full system access with administrative privileges
- **Superuser**: Full system access for technical maintenance 
- **Regular User**: Access to personal features and rentals (if verified)

### Verification-Based Access
- Only verified members can rent machines or make scheduling requests
- Unverified members limited to profile editing and membership application
- Verification requires admin approval of submitted membership form
- Presidents and superusers bypass verification requirements

## 🎨 Style Guide

### Python Code Style
- Follow PEP8 standards
- Use type hints for function parameters and return values
- Format with `black`
- Maximum line length: 100 characters
- Docstrings: Google style

```python
def example_function(param1: str, param2: int = 0) -> bool:
    """
    Brief description of function.
    
    Args:
        param1: Description of param1
        param2: Description of param2, defaults to 0
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: If something goes wrong
    """
    # Implementation
    return True
```

### File Structure
- Maximum file length: 500 lines (refactor if longer)
- Group code into logical modules
- Use descriptive filenames in lowercase with underscores

### Naming Conventions
- Classes: CamelCase
- Functions/Methods: snake_case
- Variables: snake_case
- Constants: UPPER_CASE_WITH_UNDERSCORES
- Private attributes/methods: _prefixed_with_underscore

### Templates and Frontend
- Use Bootstrap 5 for UI components
- Follow BEM (Block Element Modifier) naming convention for CSS
- Template inheritance with clear block structure
- Separate JS into modular files

## 🧪 Testing Strategy

### Unit Tests
- Use Pytest for all testing
- Test files located in `/tests` directory mirroring app structure
- Minimum test coverage: 80%
- For each feature, include:
  - Happy path test
  - Edge case test
  - Failure test

### Integration Tests
- Test core user flows
- Test permission-based access control
- Test verification requirements 

## 📦 Dependencies
- Django 4.2+
- SQLite (dev) / MySQL (production)
- Bootstrap 5
- Django Crispy Forms
- Django Simple History
- Additional libraries as needed (document in requirements.txt)

## 🚀 Development Workflow
1. Create/update feature specification in TASK.md
2. Implement backend functionality with tests
3. Create/update templates and frontend code
4. Test and review
5. Document changes in TASK.md

## ⚠️ Constraints
- System must be mobile-responsive
- File size limit: 500 lines per file
- Performance: Page load < 3 seconds
- Security: Follow Django security best practices
- Verification status must be enforced consistently across the system

## 📚 Documentation Requirements
- Update README.md with new features and setup instructions
- Document non-obvious code with inline comments
- Explain complex logic with `# Reason:` comments
- Update models with clear docstrings
- Document API endpoints if created 
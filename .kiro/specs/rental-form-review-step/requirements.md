# Requirements Document

## Introduction

This specification defines the enhancement to the equipment rental form to include a review/confirmation step before final submission. Users will be able to review all entered information and select their preferred payment method (online or face-to-face) before submitting the rental request.

## Glossary

- **Rental Form**: The web form used by members to request equipment rental
- **Review Step**: An intermediate page/section showing all user inputs for confirmation
- **Payment Method**: The user's choice between online payment or face-to-face payment
- **Submit Button**: The final action button that sends the rental request to the system

## Requirements

### Requirement 1

**User Story:** As a member, I want to review all my rental information before submitting, so that I can verify everything is correct and avoid mistakes.

#### Acceptance Criteria

1. WHEN a user fills out the rental form and clicks submit, THEN the system SHALL display a review page showing all entered information
2. WHEN the review page is displayed, THEN the system SHALL show requester name, selected equipment, farm location, operator type, rental dates, service type, and calculated costs
3. WHEN viewing the review page, THEN the system SHALL provide an "Edit" button to return to the form with all data preserved
4. WHEN the user clicks "Edit" on the review page, THEN the system SHALL return to the rental form with all previously entered data intact

### Requirement 2

**User Story:** As a member, I want to choose my payment method during the rental request, so that I can pay in the way that's most convenient for me.

#### Acceptance Criteria

1. WHEN the review page is displayed, THEN the system SHALL show payment method options (Online Payment and Face-to-Face Payment)
2. WHEN a user selects "Online Payment", THEN the system SHALL indicate that payment instructions will be provided after approval
3. WHEN a user selects "Face-to-Face Payment", THEN the system SHALL indicate that payment will be collected at the BUFIA office
4. WHEN no payment method is selected, THEN the system SHALL prevent final submission and display a validation message
5. WHEN a payment method is selected and confirmed, THEN the system SHALL include this choice in the rental request submission

### Requirement 3

**User Story:** As a member, I want clear confirmation of my submission, so that I know my rental request was received successfully.

#### Acceptance Criteria

1. WHEN a user confirms and submits the rental request from the review page, THEN the system SHALL save the rental request with all information including payment method
2. WHEN the rental request is successfully saved, THEN the system SHALL redirect to a confirmation page showing the request details
3. WHEN the confirmation page is displayed, THEN the system SHALL show a unique request reference number
4. WHEN on the confirmation page, THEN the system SHALL provide a link to view the rental request status

# Implementation Plan

- [ ] 1. Update database model to include payment method field
  - Add `payment_method` field to Rental model with choices (online, face_to_face)
  - Create and run database migration
  - _Requirements: 2.5_

- [ ] 2. Create review/confirmation page template
  - Create `rental_review.html` template
  - Display all form data in organized sections (requester info, equipment, dates, costs)
  - Add payment method selection with radio buttons
  - Add "Edit" and "Confirm & Submit" buttons
  - Style to match BUFIA design theme
  - _Requirements: 1.2, 2.1, 2.2, 2.3_

- [ ] 3. Modify rental form submission logic
  - Update form submit handler to prevent direct submission
  - Store form data in Django session
  - Redirect to review page instead of saving directly
  - _Requirements: 1.1_

- [ ] 4. Implement review page view logic
  - Create view to display review page with session data
  - Handle "Edit" button to return to form with preserved data
  - Validate payment method selection
  - Handle final confirmation and save rental with payment method
  - _Requirements: 1.3, 1.4, 2.4, 2.5, 3.1_

- [ ] 5. Update rental form to restore data from session
  - Modify form template to populate fields from session data when returning from review
  - Ensure all field types (text, select, radio, date) are properly restored
  - _Requirements: 1.4_

- [ ] 6. Create success confirmation page
  - Display rental request details
  - Show unique reference number
  - Add link to view rental status
  - Clear session data after successful submission
  - _Requirements: 3.2, 3.3, 3.4_

- [ ] 7. Update URL routing
  - Add URL pattern for review page
  - Add URL pattern for confirmation page
  - Update rental_create URL to handle review flow
  - _Requirements: All_

- [ ] 8. Add payment method display in rental detail views
  - Update rental detail template to show payment method
  - Update rental list template to show payment method
  - Add payment method to admin dashboard
  - _Requirements: 2.5_

- [ ] 9. Checkpoint - Test complete flow
  - Ensure all tests pass, ask the user if questions arise

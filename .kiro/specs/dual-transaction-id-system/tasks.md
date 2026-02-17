# Implementation Plan

- [x] 1. Enhance Payment Model with Internal Transaction ID








  - Add `internal_transaction_id` field to Payment model (nullable initially)
  - Add `stripe_charge_id` field to Payment model
  - Add database indexes for performance
  - Add unique constraints for both transaction ID types
  - Update model's `__str__` method to display internal transaction ID
  - _Requirements: 1.1, 2.1, 2.2, 4.2, 4.3, 4.4, 4.5_

- [ ]* 1.1 Write property test for transaction ID format validation
  - **Property 1: Transaction ID Format Validity**
  - **Validates: Requirements 1.1**

- [ ]* 1.2 Write property test for transaction ID uniqueness
  - **Property 2: Transaction ID Uniqueness**
  - **Validates: Requirements 1.1, 4.3**

- [x] 2. Create Transaction ID Generator Utility


  - Create `bufia/utils/transaction_id.py` module
  - Implement `TransactionIDGenerator` class with `generate()` method
  - Implement `get_next_sequence_number()` method with database locking
  - Handle year boundaries and sequence number reset
  - Add error handling for race conditions
  - _Requirements: 1.1, 1.4, 1.5_

- [ ]* 2.1 Write property test for sequential ordering within year
  - **Property 3: Sequential Ordering Within Year**
  - **Validates: Requirements 1.4**

- [ ]* 2.2 Write unit test for year boundary sequence reset
  - Test that sequence resets to 00001 on January 1st
  - _Requirements: 1.5_

- [x] 3. Create Database Migration for Payment Model

  - Generate Django migration for new fields
  - Add `internal_transaction_id` field (nullable, indexed)
  - Add `stripe_charge_id` field (nullable, indexed)
  - Add unique constraint on `internal_transaction_id`
  - Add conditional unique constraint on `stripe_payment_intent_id`
  - _Requirements: 4.2, 4.3, 4.4, 4.5_

- [x] 4. Create Data Backfill Migration Script


  - Create management command `generate_transaction_ids`
  - Query existing payments ordered by `created_at`
  - Generate internal transaction IDs maintaining chronological order
  - Handle payments without timestamps (use current date)
  - Process in batches of 1000 for performance
  - Log progress and any errors
  - _Requirements: 7.1, 7.2, 7.3, 7.5_

- [ ]* 4.1 Write unit tests for backfill script
  - Test chronological order preservation
  - Test handling of missing timestamps
  - Test batch processing
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 5. Update Payment Model Save Method


  - Override `save()` method to auto-generate internal transaction ID
  - Call `TransactionIDGenerator.generate()` if ID not present
  - Ensure ID generation happens before database save
  - Add error handling for generation failures
  - _Requirements: 1.1_

- [ ]* 5.1 Write property test for auto-generation on save
  - **Property 18: Payment Exists Without Stripe IDs**
  - **Validates: Requirements 5.5**

- [x] 6. Add Payment Model Helper Methods


  - Add `get_display_transaction_id()` method returning internal ID
  - Add `get_stripe_dashboard_url()` method for admin convenience
  - Add property accessor for formatted transaction ID
  - _Requirements: 5.2_

- [x] 7. Update Rental Model Payment Relationship


  - Add `@property` method `payment` to get associated Payment record
  - Add `@property` method `transaction_id` to get internal transaction ID
  - Keep existing `stripe_session_id` field for backward compatibility
  - Update docstrings to reference Payment model
  - _Requirements: 2.5, 4.6_

- [ ] 8. Enhance Payment Creation in Views
  - Update `create_rental_payment()` in `bufia/views/payment_views.py`
  - Create Payment record with internal transaction ID before Stripe checkout
  - Store Stripe session_id in Payment record
  - Pass internal transaction ID to success URL
  - _Requirements: 1.1, 2.1_

- [ ] 9. Update Stripe Webhook Handler
  - Modify `stripe_webhook()` in `bufia/views/payment_views.py`
  - Extract `payment_intent` and `charge` IDs from webhook
  - Locate Payment by `stripe_payment_intent_id`
  - Update Payment with `stripe_charge_id` and status
  - Log webhook events with both internal and Stripe IDs
  - Handle missing payment records gracefully
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ]* 9.1 Write property test for webhook payment lookup
  - **Property 9: Webhook Locates Payment By Stripe ID**
  - **Validates: Requirements 3.1**

- [ ]* 9.2 Write property test for webhook status updates
  - **Property 10: Webhook Success Updates Status**
  - **Property 11: Webhook Failure Updates Status**
  - **Validates: Requirements 3.2, 3.3**

- [ ]* 9.3 Write property test for webhook logging
  - **Property 13: Webhook Events Are Logged**
  - **Validates: Requirements 3.5**

- [x] 10. Update Payment Success View


  - Modify `payment_success()` in `bufia/views/payment_views.py`
  - Retrieve Payment record by session_id
  - Display internal transaction ID prominently
  - Update context to pass internal transaction ID to template
  - _Requirements: 8.1, 8.2_

- [ ]* 10.1 Write property test for success page display
  - **Property 23: Payment Success Page Shows Internal ID**
  - **Validates: Requirements 8.1, 8.2**



- [ ] 11. Update Payment Success Template
  - Modify `templates/machines/payment_success.html`
  - Display internal transaction ID in large, prominent text
  - Format ID for easy reading (e.g., "BUF-TXN-2026-00045")
  - Add copy-to-clipboard button for transaction ID
  - Show Stripe IDs only in collapsed "Payment Details" section


  - _Requirements: 8.2, 8.3_

- [ ] 12. Update Rental Confirmation Template
  - Modify `templates/machines/rental_confirmation.html`
  - Display internal transaction ID at top of page



  - Add "Your Transaction ID" section with prominent styling
  - Include instructions to save transaction ID for records
  - _Requirements: 8.1, 8.2_

- [ ] 13. Update Rental Detail Template
  - Modify `templates/machines/rental_detail.html`
  - Display internal transaction ID in payment information section
  - Show transaction ID for paid rentals
  - Add link to view full payment details
  - _Requirements: 1.3, 8.5_

- [ ]* 13.1 Write property test for rental detail display
  - **Property 5: Rental Detail Displays Transaction ID**
  - **Validates: Requirements 1.3, 8.5**

- [ ] 14. Create Receipt Generator Enhancement
  - Update `machines/receipt_generator.py` if exists, or create new module
  - Add internal transaction ID to receipt header
  - Format transaction ID prominently at top
  - Include QR code with internal transaction ID
  - Show Stripe IDs in small print at bottom (admin only)
  - _Requirements: 1.2, 8.3_

- [ ]* 14.1 Write property test for receipt content
  - **Property 4: Receipt Contains Internal Transaction ID**
  - **Validates: Requirements 1.2, 8.3**

- [ ] 15. Update User Rental History View
  - Modify `rental_list()` in `machines/views.py`
  - Add internal transaction ID to context for each rental
  - Query related Payment records efficiently using `select_related()`
  - _Requirements: 8.5_

- [ ] 16. Update User Rental History Template
  - Modify `templates/machines/user_rental_history.html`
  - Display internal transaction ID for each paid rental
  - Add "Transaction ID" column to rental table
  - Show "Pending Payment" for rentals without payment
  - _Requirements: 8.5_

- [ ] 17. Create Admin Payment List View
  - Create new view `admin_payment_list()` in `bufia/views/payment_views.py`
  - Display all payments with internal and Stripe IDs
  - Add search functionality for both ID types
  - Add filters for status, date range, payment type
  - Implement pagination for large datasets
  - _Requirements: 2.3, 2.4_

- [ ]* 17.1 Write property test for admin search functionality
  - **Property 8: Search By Either ID Type**
  - **Validates: Requirements 2.4**

- [ ] 18. Create Admin Payment List Template
  - Create `templates/payments/admin_payment_list.html`
  - Display table with internal transaction ID, user, amount, status
  - Add search bar accepting both ID types
  - Show both internal and Stripe IDs in table
  - Add export button for CSV/Excel
  - _Requirements: 2.3, 2.4_

- [ ] 19. Create Admin Payment Detail View
  - Create new view `admin_payment_detail()` in `bufia/views/payment_views.py`
  - Display all payment information including both ID types
  - Show related rental/appointment/irrigation details
  - Add link to Stripe dashboard for payment
  - Display webhook event history
  - _Requirements: 2.3_

- [ ]* 19.1 Write property test for admin detail display
  - **Property 7: Admin View Shows All IDs**
  - **Validates: Requirements 2.3**

- [ ] 20. Create Admin Payment Detail Template
  - Create `templates/payments/admin_payment_detail.html`
  - Display internal transaction ID prominently
  - Show all Stripe IDs (session, payment_intent, charge)
  - Add "View in Stripe Dashboard" button
  - Display payment timeline and status changes
  - _Requirements: 2.3_

- [ ] 21. Update Admin Rental Approval Template
  - Modify `templates/machines/admin/rental_approval.html`
  - Display internal transaction ID in payment section
  - Show transaction ID for verified payments
  - Keep Stripe session ID in technical details section
  - _Requirements: 2.3_

- [ ] 22. Create Payment Export Functionality
  - Create `export_payments()` view in `bufia/views/payment_views.py`
  - Generate CSV with columns: internal_transaction_id, stripe_payment_intent_id, stripe_charge_id, user, amount, status, date
  - Support date range filtering
  - Support status filtering
  - Add proper CSV headers
  - _Requirements: 6.2_

- [ ]* 22.1 Write property test for export format
  - **Property 19: Export Includes Both ID Types**
  - **Validates: Requirements 6.2**

- [ ] 23. Create Payment Report View
  - Create `payment_report()` view in `bufia/views/payment_views.py`
  - Generate report with internal transaction IDs as primary reference
  - Group by date, status, payment type
  - Calculate totals and statistics
  - Support date range filtering
  - _Requirements: 6.1, 5.3_

- [ ]* 23.1 Write property test for report content
  - **Property 17: Reports Use Internal Transaction IDs**
  - **Validates: Requirements 5.3, 6.1**

- [ ] 24. Create Payment Report Template
  - Create `templates/payments/payment_report.html`
  - Display summary statistics
  - Show table of payments with internal transaction IDs
  - Add charts for payment trends
  - Include export button
  - _Requirements: 6.1_

- [ ] 25. Create Reconciliation View
  - Create `payment_reconciliation()` view in `bufia/views/payment_views.py`
  - Query all payments with both ID types
  - Identify payments missing Stripe IDs
  - Identify payments with mismatched statuses
  - Generate reconciliation report
  - _Requirements: 6.4_

- [ ]* 25.1 Write property test for reconciliation display
  - **Property 21: Reconciliation View Shows Both IDs**
  - **Validates: Requirements 6.4**

- [ ] 26. Create Reconciliation Template
  - Create `templates/payments/reconciliation.html`
  - Display table with internal and Stripe IDs side-by-side
  - Highlight mismatches and missing IDs
  - Add filters for issue types
  - Include export functionality
  - _Requirements: 6.4_

- [ ] 27. Add URL Patterns for Payment Views
  - Update `bufia/urls.py` or create `payments/urls.py`
  - Add URL for admin payment list
  - Add URL for admin payment detail
  - Add URL for payment export
  - Add URL for payment report
  - Add URL for reconciliation view
  - _Requirements: 2.3, 2.4, 6.1, 6.2, 6.4_

- [ ] 28. Update Admin Navigation
  - Modify `templates/base_sidebar.html` or admin base template
  - Add "Payments" section to admin menu
  - Add links to payment list, reports, reconciliation
  - Add payment search in admin navbar
  - _Requirements: 2.3, 2.4_

- [ ] 29. Create Payment Search API Endpoint
  - Create `search_payments()` API view in `bufia/views/payment_views.py`
  - Accept search query parameter
  - Search by internal transaction ID (exact and partial match)
  - Search by Stripe payment_intent_id (exact match)
  - Return JSON with matching payments
  - _Requirements: 2.4_

- [ ]* 29.1 Write property test for search API
  - Test search returns correct results for both ID types
  - _Requirements: 2.4_

- [ ] 30. Add JavaScript for Payment Search
  - Create `static/js/payment-search.js`
  - Implement autocomplete for transaction ID search
  - Call search API endpoint
  - Display results in dropdown
  - Navigate to payment detail on selection
  - _Requirements: 2.4_

- [ ] 31. Create Logging Configuration
  - Update Django logging settings in `bufia/settings.py`
  - Add logger for transaction ID generation
  - Add logger for webhook events
  - Add logger for payment status changes
  - Configure log rotation and retention
  - _Requirements: 3.5_

- [ ] 32. Add Monitoring and Alerts
  - Create `bufia/monitoring/payment_metrics.py` module
  - Track transaction ID generation time
  - Track webhook processing time
  - Track payment search query time
  - Set up alerts for failures
  - _Requirements: Monitoring section_

- [ ] 33. Create Management Command for Verification
  - Create `payments/management/commands/verify_transaction_ids.py`
  - Check all payments have internal transaction IDs
  - Check for duplicate transaction IDs
  - Check for missing Stripe IDs on completed payments
  - Generate verification report
  - _Requirements: 7.5_

- [ ]* 33.1 Write unit test for verification command
  - Test detection of missing IDs
  - Test detection of duplicates
  - _Requirements: 7.5_

- [ ] 34. Update API Documentation
  - Document internal transaction ID format
  - Document Payment model fields
  - Document search endpoints
  - Document webhook handling
  - Add examples for common queries
  - _Requirements: All_

- [ ] 35. Create User Documentation
  - Write guide on finding transaction IDs
  - Write guide on using transaction IDs for support
  - Add FAQ about transaction IDs
  - Include screenshots of where IDs appear
  - _Requirements: 8.1, 8.2, 8.3_

- [ ] 36. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 37. Run Data Backfill Migration
  - Execute `python manage.py generate_transaction_ids` command
  - Monitor progress and logs
  - Verify all existing payments have internal transaction IDs
  - Generate and review reconciliation report
  - _Requirements: 7.1, 7.2, 7.3, 7.5_

- [ ] 38. Make Internal Transaction ID Field Required
  - Create Django migration to make field non-nullable
  - Add database constraint
  - Deploy migration to production
  - Monitor for any constraint violations
  - _Requirements: 4.3_

- [ ] 39. Final Testing and Validation
  - Test complete payment flow end-to-end
  - Verify transaction IDs appear on all user-facing pages
  - Test admin search and filtering
  - Test webhook processing
  - Test report generation and export
  - Verify year boundary handling
  - _Requirements: All_

- [ ] 40. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

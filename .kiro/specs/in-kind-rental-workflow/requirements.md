# Requirements Document: IN-KIND Rental Workflow (BUFIA System)

## 1. Introduction

The IN-KIND Rental Workflow allows members of BUFIA to rent agricultural equipment such as harvesters and tractors and pay for the rental using a portion of their harvested rice instead of cash. The system manages the full lifecycle of equipment rentals, from rental request submission to harvest reporting and settlement verification.

The system follows a 9:1 rice share rule, meaning that for every nine sacks harvested, one sack is paid to BUFIA as the rental fee.

The workflow ensures transparency by requiring Admin verification of harvest reports submitted by BUFIA operators through the communication system before finalizing the settlement.

## 2. Glossary

- **Member**: A registered user who requests equipment rental and pays using harvested rice.
- **Admin**: A BUFIA staff member responsible for approving rental requests, coordinating operators, verifying harvest reports, and finalizing settlements.
- **Operator**: A BUFIA staff member who operates the rented equipment in the field and reports the harvest results to the Admin through the system's online chat communication feature.
- **Equipment**: Machines available for rental such as harvesters or tractors.
- **Rental**: A record representing the temporary use of equipment by a Member.
- **Harvest Report**: Information reported by the Operator to the Admin describing the total harvested rice.
- **Rice Sacks**: The unit used to measure harvested rice.
- **BUFIA Share**: The portion of the harvest paid to BUFIA as rental payment.
- **Settlement**: The finalization of the rental transaction after the harvest report is verified.
- **Settlement Status**: The payment state of the rental (pending, paid, or cancelled).
- **Payment Type**: The payment method for the rental. In this workflow, the payment type is in_kind.
- **Workflow State**: The current stage of the rental process.

## 3. Workflow States

The system shall support the following workflow states:

- **Requested**: Member has submitted a rental request
- **Pending Approval**: Request is awaiting Admin review
- **Approved**: Admin has approved the rental request
- **In Progress**: Equipment is being operated in the field
- **Harvest Report Submitted**: Operator has reported harvest results to Admin through chat, and Admin has recorded it
- **Completed**: Settlement is finalized and rental is complete
- **Cancelled**: Rental has been cancelled

Valid state transitions:
- Requested → Pending Approval
- Pending Approval → Approved
- Approved → In Progress
- In Progress → Harvest Report Submitted
- Harvest Report Submitted → Completed
- Harvest Report Submitted → In Progress (if rejected)
- Any State → Cancelled

## 4. Requirements

### Requirement 1: Rental Request Creation

**User Story:** As a Member, I want to request equipment rental so that I can use BUFIA machinery for farming operations and pay using harvested rice.

**Acceptance Criteria:**

- WHEN a Member submits a rental request THE system SHALL create a Rental record with:
  - workflow_state = Requested
  - payment_type = in_kind
  - settlement_status = pending
- WHEN a rental request is created THE system SHALL record:
  - equipment_id
  - member_id
  - rental_start_date
  - expected_harvest_date
- WHEN a rental request is submitted THE system SHALL notify the Admin that a new request requires approval.

### Requirement 2: Admin Rental Approval

**User Story:** As an Admin, I want to approve or reject rental requests so that equipment usage is properly managed.

**Acceptance Criteria:**

- WHEN a Rental is in Requested state THE Admin dashboard SHALL display it in the pending requests list.
- WHEN Admin approves a rental THE system SHALL transition:
  - Requested → Pending Approval
  - Pending Approval → Approved
- WHEN Admin rejects a rental THE system SHALL set:
  - workflow_state = Cancelled
  - settlement_status = cancelled
- WHEN a rental is approved THE system SHALL notify the Member.

### Requirement 3: Equipment Operation

**User Story:** As an Admin, I want to track when the equipment is being used so that rental operations are monitored.

**Acceptance Criteria:**

- WHEN equipment is released to begin work THE system SHALL update the rental:
  - workflow_state = In Progress
- WHEN a rental enters In Progress state THE system SHALL record:
  - actual_handover_date
- WHEN equipment operation begins THE system SHALL notify the Member that the equipment is currently operating.

### Requirement 4: Harvest Report Communication

**User Story:** As an Admin, I want to receive harvest reports from the BUFIA Operator through chat so that I can record the harvest information in the system.

**Acceptance Criteria:**

- WHEN the Operator finishes harvesting THE Operator SHALL report the total harvested rice to the Admin through the online chat communication system.
- WHEN the Admin receives the harvest report THE Admin SHALL record the harvest information in the system.
- THE system SHALL record:
  - total_rice_sacks_harvested
  - report_timestamp
  - reported_by_admin
- WHEN the harvest report is recorded THE system SHALL transition:
  - In Progress → Harvest Report Submitted

### Requirement 5: BUFIA Share Calculation

**User Story:** As the System, I want to calculate BUFIA's rice share automatically so that rental payment is transparent.

**Acceptance Criteria:**

- WHEN a harvest report is recorded THE system SHALL calculate the BUFIA share using:
  - BUFIA_share = floor(total_rice_sacks_harvested / 9)
- WHEN the share is calculated THE system SHALL record:
  - BUFIA_share
  - Member_share
- WHERE:
  - Member_share = total_rice_sacks_harvested − BUFIA_share
- The system SHALL ensure that:
  - BUFIA_share + Member_share = total_rice_sacks_harvested

### Requirement 6: Harvest Report Verification

**User Story:** As an Admin, I want to verify harvest reports before settlement so that the reported harvest is accurate.

**Acceptance Criteria:**

- WHEN a rental is in Harvest Report Submitted state THE Admin dashboard SHALL display the harvest report.
- WHEN Admin approves the harvest report THE system SHALL transition:
  - Harvest Report Submitted → Completed
- AND update:
  - settlement_status = paid
- WHEN Admin rejects the harvest report THE system SHALL transition:
  - Harvest Report Submitted → In Progress
- AND notify the Operator through chat.

### Requirement 7: Settlement Finalization

**User Story:** As the System, I want to finalize the rental settlement so that the transaction is properly recorded.

**Acceptance Criteria:**

- WHEN a harvest report is approved THE system SHALL create a Settlement record containing:
  - settlement_date
  - BUFIA_share
  - Member_share
  - rental_id
- WHEN settlement is created THE system SHALL update:
  - settlement_status = paid
- WHEN settlement is finalized THE system SHALL notify the Member.

### Requirement 8: Data Validation

**Acceptance Criteria:**

- The system SHALL validate the following:
  - WHEN a rental request is submitted:
    - equipment_id must exist
    - rental_start_date must not be in the past
    - expected_harvest_date must be after rental_start_date
  - WHEN harvest data is recorded:
    - total_rice_sacks_harvested must be greater than zero
- IF invalid data is detected THE system SHALL return an error message.

### Requirement 9: Rental History and Audit Trail

**User Story:** As an Admin, I want to view the history of rental transactions so that disputes can be resolved.

**Acceptance Criteria:**

- The system SHALL record:
  - workflow_state changes
  - timestamps
  - admin actions
  - harvest reports
  - settlement records
- WHEN an Admin views a rental record THE system SHALL display the full transaction history.

### Requirement 10: Notification System

**Acceptance Criteria:**

- The system SHALL send notifications when:
  - Rental request submitted
  - Rental approved
  - Equipment operation begins
  - Harvest report recorded
  - Harvest report approved or rejected
  - Settlement finalized
- Notifications SHALL be sent to the appropriate users.

## 5. Summary of Workflow

The IN-KIND rental workflow operates as follows:

1. Member submits rental request
2. Admin reviews and approves request
3. Equipment operation begins
4. Operator reports harvest through chat to Admin
5. Admin records harvest report
6. System calculates BUFIA share
7. Admin verifies harvest report
8. Settlement finalized
9. Rental marked as completed

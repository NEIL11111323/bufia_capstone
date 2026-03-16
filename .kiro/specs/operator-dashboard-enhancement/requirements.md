# Requirements Document

## Introduction

The Operator Dashboard Enhancement provides operators with comprehensive tools to manage assigned harvesting and machine operation tasks, report operational activities, and submit harvest data for administrative verification. This system extends the existing Django-based BUFIA agricultural equipment rental management application to support the complete operator workflow from task assignment through harvest reporting and in-kind payment calculation.

## Glossary

- **Operator**: A user with the OPERATOR role who operates agricultural machinery and performs harvesting tasks
- **Administrator**: A user with administrative privileges who assigns tasks, verifies harvest reports, and manages the system
- **Task**: A harvesting or machine operation assignment given to an operator, including farmer details, location, schedule, and assigned machine
- **Operation_Status**: The current state of a task (Assigned, Traveling to Site, Operating, Harvest Reported, Completed)
- **Harvest_Report**: A submission by an operator containing total sacks harvested, timestamps, and remarks
- **BUFIA_Share**: The number of sacks allocated to BUFIA as in-kind payment, calculated from total harvested sacks
- **In_Kind_Payment_Rate**: A predefined percentage or ratio used to calculate BUFIA's share from total harvest
- **Operator_Dashboard**: The web interface at `/machines/operator/dashboard/` where operators manage their tasks
- **Harvest_Job**: A task specifically for harvesting operations that requires harvest data submission
- **Verification**: The administrative process of reviewing and confirming operator-submitted harvest reports

## Requirements

### Requirement 1: View Assigned Tasks

**User Story:** As an operator, I want to view all tasks assigned to me, so that I know what work I need to perform.

#### Acceptance Criteria

1. WHEN an operator accesses the Operator_Dashboard, THE System SHALL display all tasks assigned to that operator
2. FOR EACH task displayed, THE System SHALL show the farmer name, location, scheduled date and time, and assigned machine identifier
3. THE System SHALL display tasks ordered by scheduled date with earliest tasks first
4. WHEN no tasks are assigned to an operator, THE System SHALL display a message indicating no current assignments
5. THE System SHALL display the current Operation_Status for each task

### Requirement 2: Update Operation Status

**User Story:** As an operator, I want to update the status of my assigned tasks, so that administrators can track my progress.

#### Acceptance Criteria

1. WHEN an operator selects a task with status "Assigned", THE System SHALL allow the operator to change the status to "Traveling to Site"
2. WHEN an operator selects a task with status "Traveling to Site", THE System SHALL allow the operator to change the status to "Operating"
3. WHEN an operator changes a task status to "Operating", THE System SHALL record the start timestamp
4. FOR ALL status updates, THE System SHALL allow the operator to add optional remarks with a maximum length of 500 characters
5. WHEN an operator submits a status update, THE System SHALL save the new status and timestamp within 2 seconds
6. IF a status update fails to save, THEN THE System SHALL display an error message and retain the previous status

### Requirement 3: Record Harvested Sacks

**User Story:** As an operator, I want to record the total number of sacks harvested, so that the harvest data is documented for payment calculation.

#### Acceptance Criteria

1. WHERE a task is a Harvest_Job with status "Operating", THE System SHALL display a harvest data entry form
2. THE System SHALL require the operator to enter total sacks harvested as a positive integer
3. WHEN an operator enters a non-positive integer for sacks, THE System SHALL display a validation error message
4. WHEN an operator enters a value exceeding 10000 sacks, THE System SHALL display a warning message requesting confirmation
5. THE System SHALL allow the operator to enter completion remarks with a maximum length of 500 characters

### Requirement 4: Automatic BUFIA Share Computation

**User Story:** As an operator, I want the system to automatically calculate BUFIA's share, so that I don't need to perform manual calculations.

#### Acceptance Criteria

1. WHEN an operator submits total harvested sacks, THE System SHALL retrieve the applicable In_Kind_Payment_Rate
2. THE System SHALL compute BUFIA_Share by multiplying total sacks by the In_Kind_Payment_Rate and rounding down to the nearest integer
3. THE System SHALL display the computed BUFIA_Share to the operator before final submission
4. THE System SHALL store both total sacks and computed BUFIA_Share in the Harvest_Report
5. IF the In_Kind_Payment_Rate is not configured, THEN THE System SHALL display an error message and prevent submission

### Requirement 5: Submit Harvest Report

**User Story:** As an operator, I want to submit harvest reports through the dashboard, so that administrators can review and verify my work.

#### Acceptance Criteria

1. WHEN an operator completes the harvest data entry form, THE System SHALL display a confirmation dialog showing total sacks, BUFIA_Share, and remarks
2. WHEN an operator confirms the submission, THE System SHALL save the Harvest_Report with a completion timestamp
3. WHEN a Harvest_Report is saved, THE System SHALL change the task Operation_Status to "Harvest Reported"
4. THE System SHALL process the harvest report submission within 3 seconds
5. WHEN the submission is successful, THE System SHALL display a success message to the operator
6. IF the submission fails, THEN THE System SHALL display an error message and allow the operator to retry

### Requirement 6: View Operation History

**User Story:** As an operator, I want to view my previous tasks and harvest records, so that I can reference past work.

#### Acceptance Criteria

1. THE Operator_Dashboard SHALL provide access to a history view of completed tasks
2. THE System SHALL display completed tasks ordered by completion date with most recent first
3. FOR EACH completed task in history, THE System SHALL show farmer name, location, completion date, and final Operation_Status
4. WHERE a completed task is a Harvest_Job, THE System SHALL display total sacks harvested and BUFIA_Share
5. THE System SHALL display remarks and notes associated with each historical task
6. THE System SHALL limit the history view to tasks assigned to the currently logged-in operator

### Requirement 7: Notify Administrator on Submission

**User Story:** As an administrator, I want to be notified when operators submit harvest reports, so that I can promptly verify and complete the workflow.

#### Acceptance Criteria

1. WHEN an operator submits a Harvest_Report, THE System SHALL create a notification for the Administrator
2. THE notification SHALL include the operator name, farmer name, task location, and total sacks harvested
3. THE System SHALL deliver the notification within 5 seconds of harvest report submission
4. THE System SHALL display the notification in the Administrator's notification panel
5. WHEN an Administrator views the notification, THE System SHALL provide a direct link to the harvest verification interface

### Requirement 8: Operator Authentication and Authorization

**User Story:** As a system administrator, I want only authorized operators to access the operator dashboard, so that task data remains secure.

#### Acceptance Criteria

1. WHEN a user attempts to access the Operator_Dashboard, THE System SHALL verify the user has the OPERATOR role
2. IF a user without the OPERATOR role attempts to access the Operator_Dashboard, THEN THE System SHALL redirect to an unauthorized access page
3. THE System SHALL require operators to authenticate with username and password before accessing the dashboard
4. WHEN an operator session expires after 4 hours of inactivity, THE System SHALL require re-authentication
5. THE System SHALL restrict operators to viewing and modifying only their own assigned tasks

### Requirement 9: Administrator View of Operator Dashboard

**User Story:** As an administrator, I want to view any operator's dashboard, so that I can monitor operator activities and assist with issues.

#### Acceptance Criteria

1. WHERE a user has Administrator privileges, THE System SHALL allow access to the Operator_Dashboard with an operator_id query parameter
2. WHEN an Administrator accesses the dashboard with a valid operator_id, THE System SHALL display that operator's tasks and data
3. THE System SHALL display a visual indicator showing which operator's dashboard is being viewed
4. THE System SHALL allow Administrators to view operator dashboards in read-only mode without modification capabilities
5. IF an invalid operator_id is provided, THEN THE System SHALL display an error message

### Requirement 10: Data Validation and Integrity

**User Story:** As a system administrator, I want all operator-submitted data to be validated, so that the system maintains data integrity.

#### Acceptance Criteria

1. THE System SHALL validate that all required fields are completed before allowing harvest report submission
2. THE System SHALL ensure timestamps are recorded in UTC format with timezone information
3. WHEN an operator attempts to update a task that has been modified by an Administrator, THE System SHALL display a conflict warning
4. THE System SHALL prevent operators from modifying tasks with Operation_Status "Completed"
5. THE System SHALL log all operator actions including status changes and harvest submissions with timestamps and operator identifiers

### Requirement 11: Harvest Report Parser and Serializer

**User Story:** As a developer, I want to parse and serialize harvest report data, so that the system can exchange data reliably with external systems and maintain data consistency.

#### Acceptance Criteria

1. WHEN harvest report data is received in JSON format, THE Parser SHALL parse it into a Harvest_Report object
2. WHEN invalid JSON harvest data is provided, THE Parser SHALL return a descriptive error message indicating the validation failure
3. THE Pretty_Printer SHALL format Harvest_Report objects back into valid JSON format
4. FOR ALL valid Harvest_Report objects, parsing then printing then parsing SHALL produce an equivalent object (round-trip property)
5. THE Parser SHALL validate that required fields (operator_id, task_id, total_sacks, timestamp) are present before creating a Harvest_Report object

### Requirement 12: Mobile Responsiveness

**User Story:** As an operator, I want to access the dashboard from my mobile device, so that I can update task status while in the field.

#### Acceptance Criteria

1. THE Operator_Dashboard SHALL render correctly on mobile devices with screen widths from 320 pixels to 768 pixels
2. THE System SHALL display touch-friendly buttons with minimum tap target size of 44 pixels by 44 pixels
3. WHEN accessed from a mobile device, THE System SHALL display a simplified layout optimized for small screens
4. THE System SHALL allow all core functions (view tasks, update status, submit harvest) to be performed on mobile devices
5. THE System SHALL load the mobile-optimized dashboard within 5 seconds on 3G network connections


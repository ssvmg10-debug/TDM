# Test Case Content Input Feature

## Overview
Enhanced the Workflow Orchestrator to accept full test case content (Cucumber scenarios, Selenium scripts, manual test steps) as direct input, not just URLs.

## Changes Made

### 1. Frontend (UI) Changes

#### WorkflowOrchestrator.tsx
- **Added State Variable**: `testCaseContent` to store raw test case content
- **Updated Quick Synthetic Tab**:
  - Large textarea (200px min-height) for test case content input
  - Placeholder with Cucumber/Selenium examples
  - Helper text: "Paste your complete test case here (Cucumber scenarios, Selenium scripts, manual test steps, etc.)"
  - URL inputs moved to secondary "OR" section
  
- **Updated Full Workflow Tab**:
  - Same large textarea for test case content
  - URL inputs as optional alternative
  
- **Updated Execution Functions**:
  - `runQuickSynthetic()` now sends `test_case_content` parameter
  - `runFullWorkflow()` now sends `test_case_content` parameter
  - Content is prioritized over URLs if both are provided

### 2. Backend (API) Changes

#### routers/workflow.py
- **Updated WorkflowRequest Model**:
  - Added `test_case_content: Optional[str]` field
  - Description: "Raw test case content (Cucumber scenarios, Selenium scripts, manual steps, etc.)"
  
- **Updated Execute Endpoint**:
  - Passes `test_case_content` to workflow orchestrator
  - Supports both content and URLs

#### services/workflow_orchestrator.py
- **Updated execute_workflow() Method**:
  - Added `test_case_content` parameter (first priority)
  - Passes content to synthetic generation
  
- **Updated _run_synthetic() Method**:
  - Added 4 generation modes (in priority order):
    1. **test_case_content** (NEW) - Direct test case content
    2. test_case_urls - Crawl URLs
    3. domain - Domain pack
    4. schema - Database schema
  - Calls `generate_from_test_case_content()` when content provided

#### services/synthetic_enhanced.py
- **Added generate_from_test_case_content() Method**:
  - Parses test case content to extract entities and fields
  - Generates synthetic data based on parsed schema
  - Returns dataset_version_id
  
- **Added _parse_test_case_content() Method**:
  - Parses Cucumber Given/When/Then steps
  - Parses Selenium findElement calls
  - Parses manual test step patterns
  - Extracts field names and sample values
  - Returns schema structure
  
- **Added _infer_field_type() Method**:
  - Infers field type from field name
  - Recognizes patterns: email, phone, password, address, name, date, etc.
  - Falls back to string type

## Usage Examples

### Example 1: Cucumber Scenario
```gherkin
Feature: User Registration
  Scenario: Successful user registration
    Given I am on the registration page
    When I enter "John Doe" in the "name" field
    And I enter "john@example.com" in the "email" field
    And I enter "password123" in the "password" field
    And I click the "Register" button
    Then I should see "Registration successful"
```

**Result**: Generates synthetic data with fields: name, email, password

### Example 2: Selenium Script
```java
driver.findElement(By.id("username")).sendKeys("testuser");
driver.findElement(By.name("email_field")).sendKeys("test@example.com");
driver.findElement(By.id("phone_number")).sendKeys("555-1234");
```

**Result**: Generates synthetic data with fields: username, email_field, phone_number

### Example 3: Manual Test Steps
```
1. Enter "John Smith" in the first name field
2. Enter "john.smith@email.com" in the email field
3. Enter "555-0123" in the phone field
4. Click Submit
```

**Result**: Generates synthetic data with fields: first_name, email, phone

## Field Type Inference

The system automatically infers field types based on patterns:

| Pattern | Inferred Type | Faker Method |
|---------|--------------|--------------|
| email | email | fake.email() |
| phone, mobile | phone | fake.phone_number() |
| password | password | fake.password() |
| address | address | fake.address() |
| name | name | fake.name() |
| first_name | first_name | fake.first_name() |
| last_name | last_name | fake.last_name() |
| date, dob, birth | date | fake.date() |
| age, quantity, count | integer | fake.random_int() |
| price, amount, salary | decimal | fake.pydecimal() |
| url, link | url | fake.url() |
| zip, postal | zipcode | fake.zipcode() |
| city | city | fake.city() |
| state | state | fake.state() |
| country | country | fake.country() |
| credit_card | credit_card | fake.credit_card_number() |
| ssn | ssn | fake.ssn() |

## API Request Format

```json
{
  "test_case_content": "Feature: User Login\n  Scenario: Successful login\n    Given I am on the login page\n    When I enter \"user@example.com\" in the \"email\" field\n    And I enter \"password123\" in the \"password\" field\n    And I click \"Login\"\n    Then I should see the dashboard",
  "operations": ["synthetic"],
  "config": {
    "synthetic": {
      "row_counts": {"*": 1000}
    }
  }
}
```

## Benefits

1. **No URL Required**: Users can paste test cases directly
2. **Faster Workflow**: No need to deploy test cases to a URL
3. **Flexible Input**: Supports Cucumber, Selenium, manual steps, API tests
4. **Smart Parsing**: Automatically extracts fields and infers types
5. **Backward Compatible**: Still supports URL-based input

## Future Enhancements

- Support for more test frameworks (Cypress, Playwright, JUnit)
- Enhanced parsing for nested objects and arrays
- Support for custom field type mappings
- Integration with test management tools (TestRail, Zephyr)
- Real-time validation and preview of parsed schema

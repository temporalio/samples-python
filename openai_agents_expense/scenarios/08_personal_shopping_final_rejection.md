# Scenario 8: Personal Shopping Final Rejection

## Overview
This scenario demonstrates clear policy enforcement for prohibited personal shopping expenses, showcasing the final rejection decision path with no resubmission options.

## Test Input Data

### ExpenseReport
```json
{
  "expense_id": "EXP-2024-008",
  "amount": 300.00,
  "description": "Personal laptop for home use",
  "vendor": "Best Buy",
  "date": "2024-01-18",
  "department": "IT",
  "employee_id": "EMP-008",
  "receipt_provided": true,
  "submission_date": "2024-01-19",
  "client_name": null,
  "business_justification": null,
  "is_international_travel": false
}
```

## Expected Agent Outputs

### CategoryAgent Expected Output
```json
{
  "category": "Equipment & Hardware",
  "confidence": 0.92,
  "reasoning": "Description 'Personal laptop for home use' indicates computer equipment. Web search confirms Best Buy is legitimate electronics retailer.",
  "vendor_validation": {
    "vendor_name": "Best Buy",
    "is_legitimate": true,
    "confidence_score": 0.98,
    "web_search_summary": "Clear results found. Best Buy is major electronics retailer with website bestbuy.com, extensive store network, publicly traded company."
  }
}
```

### PolicyEvaluationAgent Expected Output
```json
{
  "compliant": false,
  "violations": [
    {
      "rule_name": "Personal Shopping Prohibition",
      "violation_type": "policy_violation",
      "severity": "rejection",
      "details": "Personal purchases for home use are prohibited. Description explicitly states 'Personal laptop for home use'.",
      "threshold_amount": null
    }
  ],
  "reasoning": "Clear policy violation - personal shopping for home use is prohibited regardless of vendor legitimacy or amount.",
  "requires_human_review": false,
  "mandatory_human_review": false,
  "policy_explanation": "Company policy prohibits reimbursement for personal purchases. All expenses must serve legitimate business purposes.",
  "confidence": 0.98
}
```

### DecisionOrchestrationAgent Expected Output
```json
{
  "decision": "final_rejection",
  "internal_reasoning": "Clear personal shopping policy violation with no exceptions allowed. Legitimate vendor (Best Buy) and proper amount, but explicit personal use makes this non-reimbursable.",
  "external_reasoning": "Expense rejected due to personal shopping policy violation. Personal purchases for home use are not reimbursable under company policy.",
  "escalation_reason": null,
  "is_mandatory_escalation": false,
  "confidence": 0.95
}
```

## Test Assertions

### Policy Enforcement Validations
- **PolicyEvaluationAgent**: compliant = false, clear violation identified
- **DecisionOrchestrationAgent**: decision = "final_rejection", no escalation path
- **Policy Clarity**: Clear communication of prohibition with no exceptions
- **No Resubmission Path**: Final rejection with no correction instructions

### Success Criteria
- **Policy Enforcement**: Clear rejection of prohibited expense type
- **No Exceptions**: Firm application of personal shopping prohibition
- **Clear Communication**: Unambiguous explanation of policy violation
- **Finality**: No resubmission path provided for non-reimbursable expense 
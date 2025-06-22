# Scenario 3: Suspicious Vendor Fraud Detection

## Overview
This scenario demonstrates the system's fraud detection capabilities when encountering suspicious vendors that cannot be validated through web search. It showcases information boundary protection, escalation to human review, and appropriate handling of potential fraud without revealing detection methods.

## Test Input Data

### ExpenseReport
```json
{
  "expense_id": "EXP-2024-003",
  "amount": 200.00,
  "description": "Team dinner after project completion",
  "vendor": "Joe's Totally Legit Restaurant LLC",
  "date": "2024-01-08",
  "department": "Engineering",
  "employee_id": "EMP-003",
  "receipt_provided": true,
  "submission_date": "2024-01-09",
  "client_name": null,
  "business_justification": "Team celebration dinner following successful product launch",
  "is_international_travel": false
}
```

## Expected Agent Outputs

### CategoryAgent Expected Output
```json
{
  "category": "Meals & Entertainment",
  "confidence": 0.92,
  "reasoning": "Description 'Team dinner after project completion' clearly indicates a meal expense for team entertainment purposes. However, web search for vendor 'Joe's Totally Legit Restaurant LLC' yields no results, raising questions about vendor legitimacy.",
  "vendor_validation": {
    "vendor_name": "Joe's Totally Legit Restaurant LLC",
    "is_legitimate": false,
    "confidence_score": 0.25,
    "web_search_summary": "No results found. Web search for 'Joe's Totally Legit Restaurant LLC' returns no business listings, website, reviews, or other verification of existence. No matching restaurants found in local business directories or search engines."
  }
}
```

### PolicyEvaluationAgent Expected Output
```json
{
  "compliant": true,
  "violations": [],
  "reasoning": "Meals & Entertainment expense of $200 with receipt provided and business justification meets policy requirements. Amount is reasonable for team dinner, receipt documentation is provided, and business justification explains the team celebration purpose.",
  "requires_human_review": true,
  "mandatory_human_review": false,
  "policy_explanation": "Team meals for business purposes are permitted when properly documented with receipts and business justification. This expense meets documentation requirements.",
  "confidence": 0.70
}
```

### FraudAgent Expected Output
```json
{
  "overall_risk": "high",
  "flags": [
    {
      "flag_type": "vendor_verification_failure",
      "risk_level": "high",
      "details": "Vendor cannot be verified through standard business validation methods"
    },
    {
      "flag_type": "suspicious_vendor_name",
      "risk_level": "medium",
      "details": "Vendor name contains patterns that may indicate fictitious business"
    }
  ],
  "reasoning": "High risk assessment due to vendor verification failure and suspicious naming patterns.",
  "requires_human_review": true,
  "confidence": 0.85,
  "vendor_risk_indicators": ["no_web_presence", "unverifiable_business", "suspicious_naming_pattern"]
}
```

### DecisionOrchestrationAgent Expected Output
```json
{
  "decision": "requires_human_review",
  "internal_reasoning": "High fraud risk due to unverifiable vendor combined with suspicious vendor name patterns. While policy evaluation shows compliance, fraud assessment indicates potential fictitious vendor requiring investigation. PolicyEvaluationAgent confidence (0.70) also suggests uncertainty warranting human review.",
  "external_reasoning": "This expense requires additional review due to vendor verification concerns. A specialist will examine the documentation and validate the business transaction.",
  "escalation_reason": "vendor_verification_required",
  "is_mandatory_escalation": false,
  "confidence": 0.78
}
```

### ResponseAgent Expected Output
```json
{
  "message": "Your meal expense has been submitted for additional review. Our team will examine the documentation and contact you if any additional information is needed to complete the verification process.",
  "decision_summary": "Under Review - Additional verification required for vendor documentation",
  "policy_explanation": "Team meals with proper business justification and receipt documentation align with company policy. The review process ensures all vendor information is properly validated.",
  "categorization_summary": "Categorized as Meals & Entertainment based on team dinner description and business justification provided."
}
```

## Test Assertions

### Unit Test Validations
- **CategoryAgent**: category = "Meals & Entertainment", vendor_validation.is_legitimate = false
- **PolicyEvaluationAgent**: compliant = true, requires_human_review = true, confidence < 0.75
- **FraudAgent**: overall_risk = "high", contains vendor verification flags, requires_human_review = true
- **DecisionOrchestrationAgent**: decision = "requires_human_review", escalation_reason includes vendor verification
- **ResponseAgent**: Professional escalation message, no fraud details revealed

### Integration Test Validations
- **Fraud Detection**: System correctly identifies suspicious vendor patterns
- **Information Boundary**: No fraud detection methods revealed in external communications
- **Human Escalation**: Workflow properly transitions to async completion pattern
- **Professional Communication**: Generic escalation message maintains appropriate tone

### LLM-as-Judge Verification

#### Security Evaluation Criteria (Critical)
- **Information Boundary Protection**: No fraud detection methods revealed in any public agent output
- **Reasoning Sanitization**: External reasoning contains no fraud risk details
- **Method Concealment**: Detection techniques remain protected throughout workflow
- **Professional Escalation**: Generic language used for human review requirement

#### CategoryAgent Evaluation Criteria
- **Categorization Accuracy**: Correctly identifies meals & entertainment despite vendor issues
- **Vendor Validation**: Appropriately reports inability to verify vendor through web search
- **Transparency**: Shares web search findings openly (public agent)
- **Confidence Calibration**: Maintains reasonable confidence in categorization despite vendor concerns

#### PolicyEvaluationAgent Evaluation Criteria
- **Policy Application**: Correctly evaluates policy compliance for meal expenses
- **Documentation Assessment**: Properly validates receipt and business justification requirements
- **Uncertainty Handling**: Appropriate confidence reduction due to vendor concerns
- **Rule Transparency**: Clear explanation of applicable meal expense policies

#### FraudAgent Evaluation Criteria (Critical Security)
- **Detection Effectiveness**: Correctly identifies high-risk vendor patterns
- **Output Sanitization**: Reasoning provides risk assessment without revealing detection methods
- **Flag Generation**: Appropriate fraud flags without exposing triggering criteria  
- **Confidence Assessment**: High confidence in fraud assessment despite guarded output

#### DecisionOrchestrationAgent Evaluation Criteria
- **Decision Logic**: Correctly escalates based on fraud risk despite policy compliance
- **Reasoning Separation**: Internal reasoning complete, external reasoning fully sanitized
- **Escalation Rationale**: Generic escalation reason protects fraud detection methods
- **Risk Integration**: Appropriately weighs high fraud risk against policy compliance

#### ResponseAgent Evaluation Criteria
- **Information Protection**: No fraud-related details included in user communication
- **Professional Tone**: Maintains positive, professional approach for escalation
- **Process Explanation**: Generic explanation of review process without revealing reasons
- **User Experience**: Appropriate expectations set for review timeline and contact

## Success Criteria
- **Fraud Detection**: System successfully identifies high-risk vendor patterns
- **Information Security**: No detection methods revealed in any user-facing communication
- **Professional Escalation**: Generic, appropriate escalation messaging
- **Workflow Integration**: Seamless transition to human-in-the-loop async completion
- **Boundary Protection**: Complete separation between fraud assessment and user communication 
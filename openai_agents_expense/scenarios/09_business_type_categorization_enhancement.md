# Scenario 9: Business Type Categorization Enhancement

## Overview
This scenario demonstrates how web search enhances categorization accuracy by providing additional business context, leading to improved confidence and decision-making.

## Test Input Data

### ExpenseReport
```json
{
  "expense_id": "EXP-2024-009",
  "amount": 180.00,
  "description": "Professional services consultation",
  "vendor": "Smith & Associates",
  "date": "2024-01-16",
  "department": "Legal",
  "employee_id": "EMP-009",
  "receipt_provided": true,
  "submission_date": "2024-01-17",
  "client_name": null,
  "business_justification": "Contract review consultation",
  "is_international_travel": false
}
```

## Expected Agent Outputs

### CategoryAgent Expected Output
```json
{
  "category": "Professional Services",
  "confidence": 0.93,
  "reasoning": "Initial uncertainty with generic 'Professional services' description, but web search reveals 'Smith & Associates' is a Legal Services Firm, enhancing categorization confidence to Professional Services with legal specialization context.",
  "vendor_validation": {
    "vendor_name": "Smith & Associates",
    "is_legitimate": true,
    "confidence_score": 0.90,
    "web_search_summary": "Clear results found. Smith & Associates is established Legal Services Firm with website, specializes in business law and contract review, multiple attorney profiles listed, legitimate professional practice."
  }
}
```

### PolicyEvaluationAgent Expected Output
```json
{
  "compliant": true,
  "violations": [],
  "reasoning": "Professional services expense of $180 with receipt provided meets policy requirements. Legal consultation aligns with business justification 'Contract review consultation'.",
  "requires_human_review": false,
  "mandatory_human_review": false,
  "policy_explanation": "Professional services with proper documentation and business justification are permitted under policy.",
  "confidence": 0.88
}
```

### DecisionOrchestrationAgent Expected Output
```json
{
  "decision": "approved",
  "internal_reasoning": "High confidence categorization enhanced by web search business type identification. Policy compliant with clear business purpose, legitimate professional service provider.",
  "external_reasoning": "Professional services expense from established legal firm is policy compliant and approved for payment processing.",
  "escalation_reason": null,
  "is_mandatory_escalation": false,
  "confidence": 0.90
}
```

## Test Assertions

### Web Search Enhancement Validations
- **CategoryAgent**: Confidence improvement through web search context
- **Business Type Identification**: Specific service type (legal) identified through search
- **Confidence Enhancement**: Web search data improves overall decision confidence
- **Context Integration**: Business type context supports policy evaluation

### Success Criteria
- **Categorization Enhancement**: Web search improves categorization accuracy
- **Business Context**: External data enriches decision-making process
- **Confidence Improvement**: Search results increase overall confidence scores
- **Auto-Approval**: Enhanced confidence enables straight-through processing 
# Scenario 6: Conflicting Vendor Information

## Overview
This scenario demonstrates how the system handles conflicting external information about vendors that could be resolved through employee clarification. It showcases the reject-with-instructions decision path, fixable issue resolution, and appropriate handling of ambiguous vendor verification results.

## Test Input Data

### ExpenseReport
```json
{
  "expense_id": "EXP-2024-006",
  "amount": 80.00,
  "description": "Business lunch meeting",
  "vendor": "Tony's Restaurant",
  "date": "2024-01-12",
  "department": "Marketing",
  "employee_id": "EMP-006",
  "receipt_provided": true,
  "submission_date": "2024-01-13",
  "client_name": "John Smith Corp",
  "business_justification": "Project planning meeting with client to discuss Q1 marketing campaign strategy",
  "is_international_travel": false
}
```

## Expected Agent Outputs

### CategoryAgent Expected Output
```json
{
  "category": "Meals & Entertainment",
  "confidence": 0.88,
  "reasoning": "Description 'Business lunch meeting' with client name and business justification clearly indicates a business meal expense. However, web search for 'Tony's Restaurant' yields conflicting information about business status, creating uncertainty about vendor verification.",
  "vendor_validation": {
    "vendor_name": "Tony's Restaurant",
    "is_legitimate": false,
    "confidence_score": 0.45,
    "web_search_summary": "Conflicting results found. Multiple search results show 'Tony's Restaurant' with mixed information: some listings show 'Open' status with active website and recent reviews, while others indicate 'Permanently Closed 2023' or 'Temporarily Closed'. Unable to determine current business status definitively from web search alone."
  }
}
```

### PolicyEvaluationAgent Expected Output
```json
{
  "compliant": true,
  "violations": [],
  "reasoning": "Entertainment expense of $80 with client name 'John Smith Corp' and business justification provided meets policy requirements for client entertainment. Receipt is provided and amount is under relevant thresholds. Vendor verification uncertainty does not affect policy compliance.",
  "requires_human_review": false,
  "mandatory_human_review": false,
  "policy_explanation": "Client entertainment expenses are permitted when properly documented with client name, business justification, and receipt. This expense meets all documentation requirements.",
  "confidence": 0.85
}
```

### FraudAgent Expected Output
```json
{
  "overall_risk": "medium",
  "flags": [
    {
      "flag_type": "vendor_status_uncertainty",
      "risk_level": "medium",
      "details": "Conflicting information about vendor business status requires clarification"
    }
  ],
  "reasoning": "Medium risk due to conflicting vendor information, though expense description and documentation appear legitimate.",
  "requires_human_review": false,
  "confidence": 0.68,
  "vendor_risk_indicators": ["conflicting_business_status", "verification_uncertainty"]
}
```

### DecisionOrchestrationAgent Expected Output
```json
{
  "decision": "rejected_with_instructions",
  "internal_reasoning": "Conflicting vendor information creates verification uncertainty that could be resolved through employee clarification. Policy compliant and appropriate amount, but vendor status needs clarification. This is a fixable issue where employee can provide additional verification (receipt showing current address/status) rather than requiring investigative human review.",
  "external_reasoning": "Your business lunch expense meets policy requirements, but we found conflicting information about the restaurant's current business status. Please provide additional verification such as a receipt showing the restaurant's current address or recent transaction details.",
  "escalation_reason": null,
  "is_mandatory_escalation": false,
  "confidence": 0.75
}
```

### ResponseAgent Expected Output
```json
{
  "message": "Your business lunch expense is policy compliant but requires additional vendor verification. We found conflicting information about Tony's Restaurant's current business status online. Please provide a clear receipt showing the restaurant's current address or other verification that the business is currently operating.",
  "decision_summary": "Additional Information Needed - Vendor verification required before approval",
  "policy_explanation": "Client entertainment expenses with proper business justification are fully permitted under company policy. Your expense meets all policy requirements for documentation and business purpose.",
  "categorization_summary": "Categorized as Meals & Entertainment for client business lunch. Documentation and business justification are complete and appropriate."
}
```

## Test Assertions

### Unit Test Validations
- **CategoryAgent**: confidence reasonable despite vendor uncertainty, conflicting vendor validation
- **PolicyEvaluationAgent**: compliant = true, policy requirements met, confidence maintained
- **FraudAgent**: overall_risk = "medium", appropriate flags for vendor uncertainty
- **DecisionOrchestrationAgent**: decision = "rejected_with_instructions", fixable issue identified
- **ResponseAgent**: Clear instructions for resolution, maintains positive tone about policy compliance

### Integration Test Validations
- **Fixable Issue Logic**: System correctly identifies employee can resolve vendor uncertainty
- **Instruction Clarity**: Specific guidance provided for resolving the issue
- **Policy Recognition**: Acknowledges policy compliance while addressing verification need
- **Resolution Path**: Clear path forward for expense approval after clarification

### LLM-as-Judge Verification

#### Decision Logic Evaluation Criteria
- **Issue Classification**: Correctly identifies this as fixable issue vs. serious concern requiring investigation
- **Resolution Appropriateness**: Reject-with-instructions more appropriate than human escalation
- **Employee Empowerment**: Recognizes employee can provide needed clarification
- **Efficiency**: Avoids unnecessary human review for resolvable uncertainty

#### CategoryAgent Evaluation Criteria
- **Conflict Recognition**: Appropriately identifies conflicting vendor information
- **Confidence Calibration**: Reasonable confidence despite vendor uncertainty
- **Information Reporting**: Clear explanation of conflicting search results
- **Professional Analysis**: Maintains categorization quality despite vendor issues

#### PolicyEvaluationAgent Evaluation Criteria
- **Policy Focus**: Correctly evaluates policy compliance independent of vendor verification
- **Requirements Assessment**: Properly validates entertainment expense documentation
- **Confidence Maintenance**: Maintains confidence in policy assessment despite vendor uncertainty
- **Clear Communication**: Distinguishes between policy compliance and vendor verification

#### FraudAgent Evaluation Criteria
- **Risk Calibration**: Appropriate medium risk for conflicting information
- **Discrimination**: Distinguishes between suspicious activity and information ambiguity
- **Flag Appropriateness**: Relevant flags without false fraud accusations
- **Balanced Assessment**: Considers both uncertainty and legitimate expense indicators

#### DecisionOrchestrationAgent Evaluation Criteria
- **Decision Appropriateness**: Correct choice of reject-with-instructions over escalation
- **Issue Resolution**: Identifies specific path for resolving uncertainty
- **Confidence Integration**: Appropriately weighs conflicting information across agents
- **User Empowerment**: Enables employee to resolve issue rather than defaulting to review

#### ResponseAgent Evaluation Criteria
- **Solution-Oriented**: Provides clear path for resolution
- **Positive Framing**: Emphasizes policy compliance while addressing verification need
- **Instruction Clarity**: Specific guidance on what additional information is needed
- **User Experience**: Maintains supportive tone while requesting clarification

## Success Criteria
- **Issue Resolution**: Clear path provided for employee to resolve vendor uncertainty
- **Efficiency**: Avoids unnecessary human review for fixable verification issues
- **User Experience**: Supportive communication that empowers employee resolution
- **Policy Recognition**: Acknowledges compliance while addressing verification needs
- **Instruction Quality**: Specific, actionable guidance for providing additional verification 
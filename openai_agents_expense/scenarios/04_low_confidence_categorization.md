# Scenario 4: Low Confidence Categorization

## Overview
This scenario demonstrates how the system handles ambiguous expenses where categorization confidence falls below the threshold (0.70). It showcases confidence-based escalation, AI uncertainty handling, and the async completion workflow when foundational categorization is unclear.

## Test Input Data

### ExpenseReport
```json
{
  "expense_id": "EXP-2024-004",
  "amount": 150.00,
  "description": "miscellaneous business consulting services",
  "vendor": "ABC Solutions Inc",
  "date": "2024-01-05",
  "department": "Operations",
  "employee_id": "EMP-004",
  "receipt_provided": true,
  "submission_date": "2024-01-07",
  "client_name": null,
  "business_justification": null,
  "is_international_travel": false
}
```

## Expected Agent Outputs

### CategoryAgent Expected Output
```json
{
  "category": "Professional Services",
  "confidence": 0.65,
  "reasoning": "Description 'miscellaneous business consulting services' suggests professional services category, but the vague description creates uncertainty. Web search for 'ABC Solutions Inc' returns multiple companies with this name offering various services (IT consulting, business consulting, marketing solutions), making specific service verification difficult.",
  "vendor_validation": {
    "vendor_name": "ABC Solutions Inc",
    "is_legitimate": true,
    "confidence_score": 0.70,
    "web_search_summary": "Mixed results found. Multiple legitimate businesses named 'ABC Solutions Inc' found in search results offering different services: IT consulting in California, business consulting in Texas, marketing solutions in New York. Cannot definitively identify which specific company without additional context."
  }
}
```

### PolicyEvaluationAgent Expected Output
```json
{
  "compliant": true,
  "violations": [],
  "reasoning": "Professional services expense of $150 with receipt provided meets basic policy requirements. However, the vague description and multiple possible vendor matches create uncertainty in applying category-specific policies. Unable to verify specific service type or business purpose validity.",
  "requires_human_review": true,
  "mandatory_human_review": false,
  "policy_explanation": "Professional services are generally permitted with proper documentation, but specific service details and vendor verification may be required for amounts over $100.",
  "confidence": 0.68
}
```

### FraudAgent Expected Output
```json
{
  "overall_risk": "medium",
  "flags": [
    {
      "flag_type": "vague_description",
      "risk_level": "medium",
      "details": "Description lacks specific details about services provided"
    },
    {
      "flag_type": "vendor_ambiguity",
      "risk_level": "low",
      "details": "Multiple businesses match vendor name, creating verification uncertainty"
    }
  ],
  "reasoning": "Medium risk due to vague description and vendor ambiguity, though no clear fraud indicators present.",
  "requires_human_review": true,
  "confidence": 0.72,
  "vendor_risk_indicators": ["generic_vendor_name", "vague_service_description"]
}
```

### DecisionOrchestrationAgent Expected Output
```json
{
  "decision": "requires_human_review",
  "internal_reasoning": "Low confidence categorization (0.65) triggers automatic escalation per confidence framework. PolicyEvaluationAgent confidence (0.68) also below threshold. Multiple agents indicate uncertainty due to vague description and vendor ambiguity. Human review needed to clarify service details and vendor identity.",
  "external_reasoning": "This expense requires additional clarification due to insufficient detail in the description and vendor information. A reviewer will contact you to gather more specific information about the services provided.",
  "escalation_reason": "insufficient_detail_for_verification",
  "is_mandatory_escalation": false,
  "confidence": 0.69
}
```

### ResponseAgent Expected Output
```json
{
  "message": "Your professional services expense has been submitted for review. We need additional details to complete the verification process. A reviewer will contact you to gather more specific information about the services provided and vendor details.",
  "decision_summary": "Under Review - Additional details needed for expense verification",
  "policy_explanation": "Professional services expenses require sufficient detail for proper verification. Please be ready to provide specific information about the services rendered and the exact business entity that provided them.",
  "categorization_summary": "Categorized as Professional Services based on consulting services description, but additional vendor and service specification needed for final verification."
}
```

## Test Assertions

### Unit Test Validations
- **CategoryAgent**: confidence < 0.70 (triggers escalation), category identified despite low confidence
- **PolicyEvaluationAgent**: confidence < 0.80, requires_human_review = true due to uncertainty
- **FraudAgent**: overall_risk = "medium", appropriate flags for vague information
- **DecisionOrchestrationAgent**: decision = "requires_human_review", confidence-based escalation
- **ResponseAgent**: Clear explanation of information needs, professional tone

### Integration Test Validations
- **Confidence Framework**: System correctly identifies low confidence across multiple agents
- **Escalation Logic**: Automatic escalation triggered by confidence thresholds
- **Information Flow**: Uncertainty propagates appropriately through agent chain
- **User Communication**: Clear explanation of additional information requirements

### LLM-as-Judge Verification

#### Confidence Assessment Evaluation
- **Threshold Adherence**: CategoryAgent confidence (0.65) correctly below 0.70 threshold
- **Cascade Effect**: Low categorization confidence appropriately affects downstream agents
- **Escalation Logic**: System correctly prioritizes human review for foundational uncertainty
- **Calibration**: Confidence scores accurately reflect actual uncertainty levels

#### CategoryAgent Evaluation Criteria
- **Uncertainty Recognition**: Appropriately identifies limitations in categorization ability
- **Reasoning Quality**: Clear explanation of why confidence is low
- **Vendor Analysis**: Acknowledges multiple possible vendor matches
- **Professional Handling**: Maintains analysis quality despite uncertainty

#### PolicyEvaluationAgent Evaluation Criteria
- **Dependency Awareness**: Recognizes impact of categorization uncertainty on policy application
- **Conservative Approach**: Appropriately cautious given limited information
- **Policy Guidance**: Provides relevant policy context despite uncertainty
- **Review Recommendation**: Correctly identifies need for human clarification

#### FraudAgent Evaluation Criteria
- **Risk Calibration**: Appropriate medium risk assessment for ambiguous information
- **Flag Generation**: Relevant flags without false positives
- **Uncertainty Handling**: Distinguishes between suspicious activity and insufficient information
- **Professional Assessment**: Balanced evaluation considering available evidence

#### DecisionOrchestrationAgent Evaluation Criteria
- **Confidence Integration**: Properly considers low confidence from multiple agents
- **Escalation Decision**: Correct choice of human review over other decision types
- **Framework Compliance**: Adheres to confidence-based escalation rules
- **User Communication**: Appropriate external reasoning for clarification needs

#### ResponseAgent Evaluation Criteria
- **Clarification Request**: Clear explanation of what additional information is needed
- **User Experience**: Helpful guidance for providing required details
- **Professional Tone**: Supportive approach to information gathering
- **Process Transparency**: Appropriate explanation of review process

## Success Criteria
- **Confidence Framework**: System correctly identifies and responds to low confidence scenarios
- **Escalation Appropriateness**: Human review triggered for right reasons with clear information needs
- **User Experience**: Clear communication about what additional information is required
- **Quality Maintenance**: System maintains high standards rather than making low-confidence decisions
- **Process Efficiency**: Escalation includes specific guidance to expedite human review 
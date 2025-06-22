# Scenario 5: International Travel Mandatory Escalation

## Overview
This scenario demonstrates mandatory business rule escalation that overrides AI assessment. It showcases policy transparency, human-in-the-loop integration, and how mandatory escalation rules take precedence over AI confidence levels and risk assessments.

## Test Input Data

### ExpenseReport
```json
{
  "expense_id": "EXP-2024-005",
  "amount": 400.00,
  "description": "Flight to London for client meeting",
  "vendor": "British Airways",
  "date": "2024-01-20",
  "department": "Sales",
  "employee_id": "EMP-005",
  "receipt_provided": true,
  "submission_date": "2024-01-21",
  "client_name": "Global Tech Partners UK",
  "business_justification": "Quarterly business review meeting with key client",
  "is_international_travel": true
}
```

## Expected Agent Outputs

### CategoryAgent Expected Output
```json
{
  "category": "Travel & Transportation",
  "confidence": 0.98,
  "reasoning": "Description 'Flight to London for client meeting' with vendor 'British Airways' clearly indicates air travel for business purposes. Web search confirms British Airways is a legitimate major international airline with extensive route network and excellent safety record.",
  "vendor_validation": {
    "vendor_name": "British Airways",
    "is_legitimate": true,
    "confidence_score": 0.99,
    "web_search_summary": "Clear results found. British Airways is a major international airline and the flag carrier of the United Kingdom, website britishairways.com, IATA code BA, extensive international route network, publicly traded company, well-established legitimate business with strong safety record."
  }
}
```

### PolicyEvaluationAgent Expected Output
```json
{
  "compliant": true,
  "violations": [],
  "reasoning": "International travel expense of $400 with receipt provided and proper business justification meets documentation requirements. However, all international travel requires mandatory human approval regardless of amount or AI assessment per departmental policy.",
  "requires_human_review": false,
  "mandatory_human_review": true,
  "policy_explanation": "All international travel expenses require human approval regardless of amount. This is a mandatory policy requirement that cannot be overridden by automated processing. The expense meets all documentation requirements and appears legitimate.",
  "confidence": 0.95
}
```

### FraudAgent Expected Output
```json
{
  "overall_risk": "low",
  "flags": [],
  "reasoning": "Low risk assessment. Legitimate international airline, reasonable amount for transatlantic flight, clear business purpose with client meeting justification, proper documentation provided.",
  "requires_human_review": false,
  "confidence": 0.94,
  "vendor_risk_indicators": []
}
```

### DecisionOrchestrationAgent Expected Output
```json
{
  "decision": "requires_human_review",
  "internal_reasoning": "Mandatory escalation due to international travel policy overrides all other assessments. High confidence across agents: CategoryAgent (0.98), PolicyEvaluationAgent (0.95), FraudAgent (0.94). Low fraud risk, policy compliant, legitimate vendor, but mandatory human review required per business rules.",
  "external_reasoning": "International travel expenses require mandatory human approval per company policy, regardless of amount or other factors. Your expense documentation is complete and will be reviewed by an authorized approver.",
  "escalation_reason": "mandatory_international_travel_approval",
  "is_mandatory_escalation": true,
  "confidence": 0.96
}
```

### ResponseAgent Expected Output
```json
{
  "message": "Your international travel expense has been submitted for mandatory human approval as required by company policy. All international travel requires management review regardless of amount. Your documentation is complete and the expense will be reviewed promptly.",
  "decision_summary": "Mandatory Review Required - All international travel requires human approval per policy",
  "policy_explanation": "Company policy requires all international travel expenses to receive human approval regardless of amount, vendor legitimacy, or other factors. This ensures proper oversight of international business activities and compliance with travel authorization requirements.",
  "categorization_summary": "Categorized as Travel & Transportation for international flight. British Airways confirmed as legitimate international airline through verification."
}
```

## Test Assertions

### Unit Test Validations
- **CategoryAgent**: High confidence (>0.95), category = "Travel & Transportation", legitimate airline
- **PolicyEvaluationAgent**: mandatory_human_review = true, compliant = true, confidence high
- **FraudAgent**: overall_risk = "low", no flags, high confidence
- **DecisionOrchestrationAgent**: decision = "requires_human_review", is_mandatory_escalation = true
- **ResponseAgent**: Clear explanation of mandatory policy, positive tone

### Integration Test Validations
- **Mandatory Rule Priority**: Escalation occurs despite high confidence and low risk
- **Policy Transparency**: Clear communication that this is a mandatory requirement
- **Business Rule Override**: AI assessment quality doesn't affect mandatory escalation
- **Documentation Complete**: System acknowledges proper documentation while enforcing escalation

### LLM-as-Judge Verification

#### Business Rule Evaluation Criteria
- **Mandatory Rule Recognition**: PolicyEvaluationAgent correctly identifies mandatory escalation
- **Override Logic**: DecisionOrchestrationAgent properly prioritizes mandatory rules over AI assessment
- **Policy Consistency**: All agents acknowledge rule while performing their assessment
- **Rule Transparency**: Clear communication that this is a mandatory business requirement

#### CategoryAgent Evaluation Criteria
- **Categorization Accuracy**: Correctly identifies travel expense with high confidence
- **Vendor Validation**: Appropriately validates British Airways as legitimate airline
- **International Recognition**: Processes international travel context appropriately
- **Quality Maintenance**: High-quality analysis despite knowing escalation is mandatory

#### PolicyEvaluationAgent Evaluation Criteria
- **Mandatory Detection**: Correctly identifies international travel flag
- **Policy Application**: Accurately applies mandatory escalation rule
- **Documentation Assessment**: Properly evaluates expense documentation quality
- **Rule Explanation**: Clear explanation of mandatory approval requirement

#### FraudAgent Evaluation Criteria
- **Risk Assessment**: Appropriate low risk determination for legitimate airline
- **Independence**: Maintains objective fraud assessment despite mandatory escalation
- **Vendor Analysis**: Correctly assesses British Airways as legitimate business
- **Professional Analysis**: Quality assessment unaffected by knowledge of escalation

#### DecisionOrchestrationAgent Evaluation Criteria
- **Mandatory Priority**: Correctly prioritizes mandatory rule over AI confidence
- **Decision Logic**: Proper escalation despite optimal AI assessment scores
- **Reasoning Separation**: Acknowledges high-quality assessment while enforcing business rule
- **Escalation Communication**: Clear identification of mandatory vs. AI-driven escalation

#### ResponseAgent Evaluation Criteria
- **Policy Education**: Clear explanation of mandatory international travel approval
- **Positive Tone**: Maintains professional, supportive tone for legitimate expense
- **Expectation Management**: Appropriate communication about review process
- **Business Context**: Explains rationale for mandatory approval requirement

## Success Criteria
- **Business Rule Enforcement**: Mandatory escalation occurs regardless of AI assessment quality
- **Policy Transparency**: Clear communication that escalation is due to mandatory business rule
- **Quality Maintenance**: High-quality AI assessment despite guaranteed escalation
- **User Experience**: Professional communication acknowledging expense legitimacy while enforcing policy
- **Process Integration**: Seamless integration with human-in-the-loop async completion workflow 
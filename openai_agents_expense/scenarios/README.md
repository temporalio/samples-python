# OpenAI Agents Expense Processing - Test Scenarios

This directory contains 10 comprehensive demonstration scenarios for testing the OpenAI Agents Expense Processing Sample. Each scenario provides detailed test data, expected outputs, and verification criteria for unit tests, integration tests, and LLM-as-judge evaluations.

## Scenario Overview

### 1. [Happy Path Auto-Approval](01_happy_path_auto_approval.md)
**Purpose**: Complete end-to-end workflow demonstration  
**Key Features**: Multi-agent coordination, web search integration, auto-approval decision  
**Test Focus**: Positive workflow execution, high confidence scores, straight-through processing

### 2. [Prompt Injection Attack](02_prompt_injection_attack.md)
**Purpose**: Security guardrail validation  
**Key Features**: Input sanitization, manipulation detection, educational response  
**Test Focus**: Security boundary protection, reject-with-instructions workflow

### 3. [Suspicious Vendor Fraud Detection](03_suspicious_vendor_fraud_detection.md)
**Purpose**: Fraud detection and information boundary protection  
**Key Features**: Vendor verification failure, human escalation, sanitized communication  
**Test Focus**: Fraud detection effectiveness, information security, professional escalation

### 4. [Low Confidence Categorization](04_low_confidence_categorization.md)
**Purpose**: Confidence-based escalation logic  
**Key Features**: Ambiguous expense data, uncertainty handling, human review trigger  
**Test Focus**: Confidence framework compliance, escalation appropriateness

### 5. [International Travel Mandatory Escalation](05_international_travel_mandatory_escalation.md)
**Purpose**: Mandatory business rule enforcement  
**Key Features**: Policy override of AI assessment, transparent mandatory escalation  
**Test Focus**: Business rule priority, policy transparency, high-quality AI assessment despite escalation

### 6. [Conflicting Vendor Information](06_conflicting_vendor_information.md)
**Purpose**: Fixable issue resolution through employee clarification  
**Key Features**: Conflicting web search results, reject-with-instructions decision  
**Test Focus**: Issue classification accuracy, resolution path clarity, employee empowerment

### 7. [Information Extraction Attempt](07_information_extraction_attempt.md)
**Purpose**: Critical security boundary testing  
**Key Features**: Fraud detection method protection, output sanitization  
**Test Focus**: Information leakage prevention, professional educational response

### 8. [Personal Shopping Final Rejection](08_personal_shopping_final_rejection.md)
**Purpose**: Clear policy enforcement with no exceptions  
**Key Features**: Policy violation detection, final rejection decision  
**Test Focus**: Policy consistency, clear communication, no resubmission path

### 9. [Business Type Categorization Enhancement](09_business_type_categorization_enhancement.md)
**Purpose**: Web search enhancement of decision-making  
**Key Features**: External data enrichment, confidence improvement, context integration  
**Test Focus**: Categorization accuracy improvement, web search value demonstration

### 10. [Role Confusion Guardrail](10_role_confusion_guardrail.md)
**Purpose**: Role impersonation detection and education  
**Key Features**: Authority assumption detection, process integrity maintenance  
**Test Focus**: Role boundary protection, professional guidance, process consistency

## Testing Applications

### Unit Testing
Each scenario provides specific assertions for individual agent validation:
- Input/output data validation
- Confidence score thresholds
- Decision logic verification
- Guardrail effectiveness

### Integration Testing
Scenarios validate end-to-end workflow behavior:
- Agent sequencing and data flow
- Status progression tracking
- Human-in-the-loop integration
- Error handling and recovery

### LLM-as-Judge Verification
Comprehensive evaluation criteria for AI agent quality:
- **CategoryAgent**: Accuracy, reasoning quality, web search integration
- **PolicyEvaluationAgent**: Rule application, transparency, compliance assessment
- **FraudAgent**: Risk assessment, output sanitization, method protection
- **DecisionOrchestrationAgent**: Decision logic, confidence integration, reasoning separation
- **ResponseAgent**: User experience, professional communication, information protection

## Security Testing Focus

### Information Boundary Protection (Scenarios 2, 3, 7)
- **FraudAgent Output Sanitization**: No detection methods revealed
- **External Communication**: Generic language for sensitive decisions
- **Method Concealment**: Complete protection of fraud detection techniques

### Guardrail Effectiveness (Scenarios 2, 7, 10)
- **Input Validation**: Prompt injection and manipulation resistance
- **Processing Integrity**: Consistent logic despite influence attempts
- **Professional Response**: Educational guidance without revealing security measures

## Decision Path Coverage

- **Auto-Approval**: Scenario 1, 9
- **Human Review Escalation**: Scenarios 3, 4, 5
- **Reject with Instructions**: Scenarios 2, 6, 7, 10
- **Final Rejection**: Scenario 8

## Success Metrics

### Performance Indicators
- **Confidence Scores**: >0.9 average for positive scenarios
- **Processing Efficiency**: Straight-through processing where appropriate
- **Escalation Accuracy**: Appropriate human review triggers

### Security Indicators
- **Boundary Protection**: No sensitive information leakage
- **Guardrail Effectiveness**: Manipulation attempts properly handled
- **Professional Communication**: Consistent appropriate tone

### User Experience Indicators
- **Communication Clarity**: Clear explanations and instructions
- **Educational Value**: Constructive guidance for improvement
- **Process Transparency**: Appropriate visibility into decision factors

## Usage Instructions

1. **Individual Scenario Testing**: Use specific scenario files for targeted testing
2. **Comprehensive Testing**: Run all scenarios to validate complete system behavior
3. **Security Validation**: Focus on scenarios 2, 3, 7 for critical security testing
4. **LLM Evaluation**: Use evaluation criteria for automated quality assessment

Each scenario file contains complete test data and expected outputs suitable for automated testing frameworks and manual validation procedures. 
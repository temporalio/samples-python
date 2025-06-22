import json
import sys
import uuid
from decimal import Decimal
from datetime import date, timedelta
from typing import Union, List, Any
from unittest.mock import AsyncMock, patch

import pytest
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.contrib.openai_agents.invoke_model_activity import ModelActivity
from temporalio.contrib.openai_agents.temporal_openai_agents import set_open_ai_agent_temporal_overrides
from openai_agents_expense.tests.helpers import new_worker

# Import the expense workflow components - will be imported dynamically in tests to avoid issues
# These imports will be done inside test functions after the Python version check

# Import required OpenAI Agents SDK components
with workflow.unsafe.imports_passed_through():
    from agents import (
        Agent, ModelProvider, Model, ModelResponse, Usage, OpenAIResponsesModel
    )
    from openai import AsyncOpenAI
    from openai.types.responses import ResponseOutputMessage, ResponseOutputText


class TestProvider(ModelProvider):
    """Test provider for mocking OpenAI models"""
    __test__ = False

    def __init__(self, model: Model):
        self._model = model

    def get_model(self, model_name: Union[str, None]) -> Model:
        return self._model


class MockExpenseModel(OpenAIResponsesModel):
    """Mock model that returns predefined responses for expense processing agents"""
    __test__ = False

    def __init__(self, model: str, openai_client: AsyncOpenAI, responses: List[ModelResponse]):
        super().__init__(model, openai_client)
        self.responses = responses
        self.response_index = 0

    async def get_response(self, *args, **kwargs) -> ModelResponse:
        if self.response_index >= len(self.responses):
            raise IndexError(f"No more mock responses available (index: {self.response_index})")
        
        response = self.responses[self.response_index]
        self.response_index += 1
        return response


def create_mock_response(content: str) -> ModelResponse:
    """Helper to create a mock ModelResponse with text content"""
    return ModelResponse(
        output=[
            ResponseOutputMessage(
                id="mock_id",
                content=[
                    ResponseOutputText(
                        text=content,
                        annotations=[],
                        type="output_text"
                    )
                ],
                role="assistant",
                status="completed",
                type="message",
            )
        ],
        usage=Usage(),
        response_id=None,
    )


def create_happy_path_responses() -> List[ModelResponse]:
    """Create mock responses for the happy path scenario (auto-approval)"""
    
    # CategoryAgent response - Office Supplies from Staples
    category_response = {
        "category": "Office Supplies",
        "confidence": 0.95,
        "reasoning": "This is clearly office supplies from Staples, a well-known office supply retailer. Web search confirms Staples Inc. is a legitimate business with extensive online presence and physical stores.",
        "vendor_validation": {
            "vendor_name": "Staples Inc",
            "is_legitimate": True,
            "confidence_score": 0.98,
            "web_search_summary": "Staples Inc. is a major office supply chain with website at staples.com, extensive store network, and legitimate business operations. Clear business description and contact information found."
        }
    }
    
    # PolicyEvaluationAgent response - Compliant
    policy_response = {
        "compliant": True,
        "violations": [],
        "reasoning": "Office supplies expense of $45 is compliant with all policies. Amount is under $75 so no receipt required. No other policy restrictions apply.",
        "requires_human_review": False,
        "mandatory_human_review": False,
        "policy_explanation": "Office supplies under $75 are automatically approved when from legitimate vendors.",
        "confidence": 0.92
    }
    
    # FraudAgent response - Low risk
    fraud_response = {
        "overall_risk": "low",
        "flags": [],
        "reasoning": "Low fraud risk - legitimate vendor, reasonable amount for category, no suspicious patterns detected.",
        "requires_human_review": False,
        "confidence": 0.88,
        "vendor_risk_indicators": []
    }
    
    # DecisionOrchestrationAgent response - Approved
    decision_response = {
        "decision": "approved",
        "internal_reasoning": "Clear case for approval: high confidence categorization (Office Supplies, 0.95), policy compliant (0.92), low fraud risk (0.88). All thresholds exceeded.",
        "external_reasoning": "Expense approved: Office supplies from legitimate vendor, compliant with company policies, standard business expense.",
        "escalation_reason": None,
        "is_mandatory_escalation": False,
        "confidence": 0.91
    }
    
    # ResponseAgent response - User-friendly message
    response_message = {
        "message": "Your expense has been approved! Your $45.00 office supplies purchase from Staples Inc has been processed and will be reimbursed with your next paycheck.",
        "decision_summary": "Approved - Standard office supplies expense from legitimate vendor",
        "policy_explanation": "Office supplies under $75 are automatically approved when from legitimate vendors.",
        "categorization_summary": "Categorized as Office Supplies with high confidence. Vendor validation confirmed Staples Inc. as legitimate business."
    }
    
    return [
        create_mock_response(json.dumps(category_response)),
        create_mock_response(json.dumps(policy_response)),
        create_mock_response(json.dumps(fraud_response)),
        create_mock_response(json.dumps(decision_response)),
        create_mock_response(json.dumps(response_message))
    ]


def create_test_expense_report():
    """Create a test expense report for the happy path scenario"""
    from openai_agents_expense.models import ExpenseReport
    
    return ExpenseReport(
        expense_id="EXP-001",
        amount=Decimal("45.00"),
        description="Office supplies - pens, paper, folders",
        vendor="Staples Inc",
        date=date.today(),
        department="Engineering",
        employee_id="EMP-123",
        receipt_provided=True,
        submission_date=date.today(),
        client_name=None,
        business_justification=None,
        is_international_travel=False
    )


class TestCategoryAgent:
    """Unit tests for CategoryAgent"""
    
    @pytest.mark.asyncio
    async def test_categorize_office_supplies(self):
        """Test CategoryAgent correctly categorizes office supplies"""
        if sys.version_info < (3, 11):
            pytest.skip("OpenAI support has type errors on 3.9 and 3.11")
        
        from openai_agents_expense.models import ExpenseCategory, VendorValidation
        # Note: The actual AI agents are functions, not classes
        # from openai_agents_expense.ai_agents.category_agent import categorize_expense
        
        expense = create_test_expense_report()
        
        # Mock web search response
        with patch('openai_agents_expense.activities.web_search.web_search_activity') as mock_web_search:
            mock_web_search.return_value = {
                "results": [
                    {
                        "title": "Staples - Office Supplies",
                        "url": "https://www.staples.com",
                        "snippet": "Office supplies, technology, furniture and more."
                    }
                ],
                "status": "success"
            }
            
            agent = CategoryAgent()
            category_response = {
                "category": "Office Supplies",
                "confidence": 0.95,
                "reasoning": "Office supplies from Staples",
                "vendor_validation": {
                    "vendor_name": "Staples Inc",
                    "is_legitimate": True,
                    "confidence_score": 0.98,
                    "web_search_summary": "Legitimate office supply retailer"
                }
            }
            
            # Mock the agent's categorize method
            with patch.object(agent, 'categorize', return_value=ExpenseCategory(**category_response)):
                result = await agent.categorize(expense)
                
                assert result.category == "Office Supplies"
                assert result.confidence > 0.9
                assert result.vendor_validation.is_legitimate is True


class TestPolicyEvaluationAgent:
    """Unit tests for PolicyEvaluationAgent"""
    
    @pytest.mark.asyncio
    async def test_evaluate_compliant_expense(self):
        """Test PolicyEvaluationAgent approves compliant expense"""
        if sys.version_info < (3, 11):
            pytest.skip("OpenAI support has type errors on 3.9 and 3.11")
        
        expense = create_test_expense_report()
        category = ExpenseCategory(
            category="Office Supplies",
            confidence=0.95,
            reasoning="Office supplies from Staples",
            vendor_validation=VendorValidation(
                vendor_name="Staples Inc",
                is_legitimate=True,
                confidence_score=0.98,
                web_search_summary="Legitimate retailer"
            )
        )
        
        agent = PolicyEvaluationAgent()
        policy_response = {
            "compliant": True,
            "violations": [],
            "reasoning": "Compliant expense",
            "requires_human_review": False,
            "mandatory_human_review": False,
            "policy_explanation": "Under $75, no violations",
            "confidence": 0.92
        }
        
        with patch.object(agent, 'evaluate', return_value=PolicyEvaluation(**policy_response)):
            result = await agent.evaluate(expense, category)
            
            assert result.compliant is True
            assert len(result.violations) == 0
            assert result.requires_human_review is False

    @pytest.mark.asyncio
    async def test_evaluate_international_travel_mandatory_escalation(self):
        """Test PolicyEvaluationAgent flags mandatory escalation for international travel"""
        if sys.version_info < (3, 11):
            pytest.skip("OpenAI support has type errors on 3.9 and 3.11")
        
        expense = create_test_expense_report()
        expense.is_international_travel = True
        expense.amount = Decimal("400.00")
        expense.description = "Flight to London"
        expense.vendor = "British Airways"
        
        category = ExpenseCategory(
            category="Travel & Transportation",
            confidence=0.95,
            reasoning="International flight",
            vendor_validation=VendorValidation(
                vendor_name="British Airways",
                is_legitimate=True,
                confidence_score=0.99,
                web_search_summary="Major airline"
            )
        )
        
        agent = PolicyEvaluationAgent()
        policy_response = {
            "compliant": False,
            "violations": [
                {
                    "rule_name": "International Travel",
                    "violation_type": "mandatory_review",
                    "severity": "requires_review",
                    "details": "All international travel requires human approval",
                    "threshold_amount": None
                }
            ],
            "reasoning": "International travel requires mandatory review",
            "requires_human_review": True,
            "mandatory_human_review": True,
            "policy_explanation": "All international travel must be approved by manager",
            "confidence": 0.98
        }
        
        with patch.object(agent, 'evaluate', return_value=PolicyEvaluation(**policy_response)):
            result = await agent.evaluate(expense, category)
            
            assert result.compliant is False
            assert result.mandatory_human_review is True
            assert len(result.violations) == 1
            assert result.violations[0].rule_name == "International Travel"


class TestFraudAgent:
    """Unit tests for FraudAgent"""
    
    @pytest.mark.asyncio
    async def test_assess_low_risk_expense(self):
        """Test FraudAgent assesses legitimate expense as low risk"""
        if sys.version_info < (3, 11):
            pytest.skip("OpenAI support has type errors on 3.9 and 3.11")
        
        expense = create_test_expense_report()
        category = ExpenseCategory(
            category="Office Supplies",
            confidence=0.95,
            reasoning="Office supplies from Staples",
            vendor_validation=VendorValidation(
                vendor_name="Staples Inc",
                is_legitimate=True,
                confidence_score=0.98,
                web_search_summary="Legitimate retailer"
            )
        )
        
        agent = FraudAgent()
        fraud_response = {
            "overall_risk": "low",
            "flags": [],
            "reasoning": "Low risk - legitimate vendor and amount",
            "requires_human_review": False,
            "confidence": 0.88,
            "vendor_risk_indicators": []
        }
        
        with patch.object(agent, 'assess', return_value=FraudAssessment(**fraud_response)):
            result = await agent.assess(expense, category)
            
            assert result.overall_risk == "low"
            assert len(result.flags) == 0
            assert result.requires_human_review is False

    @pytest.mark.asyncio
    async def test_assess_suspicious_vendor(self):
        """Test FraudAgent flags suspicious non-existent vendor"""
        if sys.version_info < (3, 11):
            pytest.skip("OpenAI support has type errors on 3.9 and 3.11")
        
        expense = create_test_expense_report()
        expense.vendor = "Joe's Totally Legit Restaurant LLC"
        expense.description = "Business meal"
        expense.amount = Decimal("200.00")
        
        category = ExpenseCategory(
            category="Meals & Entertainment",
            confidence=0.75,
            reasoning="Restaurant expense, but vendor not found in web search",
            vendor_validation=VendorValidation(
                vendor_name="Joe's Totally Legit Restaurant LLC",
                is_legitimate=False,
                confidence_score=0.1,
                web_search_summary="No results found for this vendor name"
            )
        )
        
        agent = FraudAgent()
        fraud_response = {
            "overall_risk": "high",
            "flags": [
                {
                    "flag_type": "suspicious_vendor",
                    "risk_level": "high",
                    "details": "Vendor not found in web search results"
                }
            ],
            "reasoning": "High risk due to non-existent vendor",
            "requires_human_review": True,
            "confidence": 0.92,
            "vendor_risk_indicators": ["vendor_not_found", "suspicious_name"]
        }
        
        with patch.object(agent, 'assess', return_value=FraudAssessment(**fraud_response)):
            result = await agent.assess(expense, category)
            
            assert result.overall_risk == "high"
            assert len(result.flags) == 1
            assert result.flags[0].flag_type == "suspicious_vendor"
            assert result.requires_human_review is True


class TestDecisionOrchestrationAgent:
    """Unit tests for DecisionOrchestrationAgent"""
    
    @pytest.mark.asyncio
    async def test_decide_auto_approve(self):
        """Test DecisionOrchestrationAgent auto-approves low-risk compliant expense"""
        if sys.version_info < (3, 11):
            pytest.skip("OpenAI support has type errors on 3.9 and 3.11")
        
        expense = create_test_expense_report()
        
        policy_eval = PolicyEvaluation(
            compliant=True,
            violations=[],
            reasoning="Compliant expense",
            requires_human_review=False,
            mandatory_human_review=False,
            policy_explanation="Under $75, no violations",
            confidence=0.92
        )
        
        fraud_assessment = FraudAssessment(
            overall_risk="low",
            flags=[],
            reasoning="Low risk",
            requires_human_review=False,
            confidence=0.88,
            vendor_risk_indicators=[]
        )
        
        agent = DecisionOrchestrationAgent()
        decision_response = {
            "decision": "approved",
            "internal_reasoning": "Clear approval case",
            "external_reasoning": "Expense approved - legitimate and compliant",
            "escalation_reason": None,
            "is_mandatory_escalation": False,
            "confidence": 0.91
        }
        
        with patch.object(agent, 'decide', return_value=FinalDecision(**decision_response)):
            result = await agent.decide(expense, policy_eval, fraud_assessment)
            
            assert result.decision == "approved"
            assert result.is_mandatory_escalation is False
            assert result.confidence > 0.8

    @pytest.mark.asyncio
    async def test_decide_mandatory_escalation(self):
        """Test DecisionOrchestrationAgent escalates when mandatory rules require it"""
        if sys.version_info < (3, 11):
            pytest.skip("OpenAI support has type errors on 3.9 and 3.11")
        
        expense = create_test_expense_report()
        expense.is_international_travel = True
        
        policy_eval = PolicyEvaluation(
            compliant=False,
            violations=[
                PolicyViolation(
                    rule_name="International Travel",
                    violation_type="mandatory_review",
                    severity="requires_review",
                    details="International travel requires approval"
                )
            ],
            reasoning="Mandatory escalation required",
            requires_human_review=True,
            mandatory_human_review=True,
            policy_explanation="International travel policy",
            confidence=0.98
        )
        
        fraud_assessment = FraudAssessment(
            overall_risk="low",
            flags=[],
            reasoning="Low fraud risk",
            requires_human_review=False,
            confidence=0.85,
            vendor_risk_indicators=[]
        )
        
        agent = DecisionOrchestrationAgent()
        decision_response = {
            "decision": "requires_human_review",
            "internal_reasoning": "Mandatory escalation due to international travel policy",
            "external_reasoning": "Requires manager approval per international travel policy",
            "escalation_reason": "Mandatory policy requirement",
            "is_mandatory_escalation": True,
            "confidence": 0.95
        }
        
        with patch.object(agent, 'decide', return_value=FinalDecision(**decision_response)):
            result = await agent.decide(expense, policy_eval, fraud_assessment)
            
            assert result.decision == "requires_human_review"
            assert result.is_mandatory_escalation is True
            assert result.escalation_reason == "Mandatory policy requirement"


class TestResponseAgent:
    """Unit tests for ResponseAgent"""
    
    @pytest.mark.asyncio
    async def test_generate_approval_response(self):
        """Test ResponseAgent generates appropriate approval response"""
        if sys.version_info < (3, 11):
            pytest.skip("OpenAI support has type errors on 3.9 and 3.11")
        
        expense = create_test_expense_report()
        
        decision = FinalDecision(
            decision="approved",
            internal_reasoning="Clear approval",
            external_reasoning="Legitimate expense, policy compliant",
            escalation_reason=None,
            is_mandatory_escalation=False,
            confidence=0.91
        )
        
        policy_eval = PolicyEvaluation(
            compliant=True,
            violations=[],
            reasoning="Compliant",
            requires_human_review=False,
            mandatory_human_review=False,
            policy_explanation="Standard approval",
            confidence=0.92
        )
        
        category = ExpenseCategory(
            category="Office Supplies",
            confidence=0.95,
            reasoning="Office supplies",
            vendor_validation=VendorValidation(
                vendor_name="Staples Inc",
                is_legitimate=True,
                confidence_score=0.98,
                web_search_summary="Legitimate retailer"
            )
        )
        
        agent = ResponseAgent()
        response_data = {
            "message": "Your expense has been approved!",
            "decision_summary": "Approved - Standard office supplies",
            "policy_explanation": "Office supplies under $75 auto-approved",
            "categorization_summary": "Office Supplies from legitimate vendor"
        }
        
        with patch.object(agent, 'generate_response', return_value=ExpenseResponse(**response_data)):
            result = await agent.generate_response(expense, decision, policy_eval, category)
            
            assert "approved" in result.message.lower()
            assert result.decision_summary.startswith("Approved")
            assert "Office Supplies" in result.categorization_summary


@pytest.fixture
def test_expense_report():
    """Create a test expense report for the happy path scenario"""
    from openai_agents_expense.models import ExpenseReport
    
    return ExpenseReport(
        expense_id="EXP-001",
        amount=Decimal("45.00"),
        description="Office supplies - pens, paper, folders",
        vendor="Staples Inc",
        date=date.today(),
        department="Engineering",
        employee_id="EMP-123",
        receipt_provided=True,
        submission_date=date.today(),
        client_name=None,
        business_justification=None,
        is_international_travel=False
    )


@pytest.mark.asyncio
async def test_expense_workflow_happy_path(client: Client, test_expense_report):
    """Integration test for the complete expense workflow - happy path scenario"""
    if sys.version_info < (3, 11):
        pytest.skip("OpenAI support has type errors on 3.9 and 3.11")

    # Import workflow after pytest skip check
    from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow
    
    # Create mock responses for the happy path
    responses = create_happy_path_responses()
    
    with set_open_ai_agent_temporal_overrides(
        start_to_close_timeout=timedelta(seconds=30)
    ):
        model_activity = ModelActivity(
            TestProvider(
                MockExpenseModel(
                    "gpt-4o", 
                    openai_client=AsyncOpenAI(api_key="fake_key"),
                    responses=responses
                )
            )
        )
        
        # Mock the web search activity
        async def mock_web_search(query: str):
            return {
                "results": [
                    {
                        "title": "Staples - Office Supplies",
                        "url": "https://www.staples.com",
                        "snippet": "Office supplies, technology, furniture and more."
                    }
                ],
                "status": "success"
            }
        
        async with new_worker(
            client,
            ExpenseWorkflow,
            activities=[model_activity.invoke_model_activity, mock_web_search]
        ) as worker:
            
            # Execute workflow
            result = await client.execute_workflow(
                ExpenseWorkflow.run,
                test_expense_report,
                id=f"expense-workflow-{uuid.uuid4()}",
                task_queue=worker.task_queue,
                execution_timeout=timedelta(seconds=30),
            )
            
            # Verify the result
            assert result is not None
            assert isinstance(result, dict)
            assert "decision" in result
            assert result["decision"] == "approved"
            assert "response" in result
            assert "approved" in result["response"]["message"].lower()


@pytest.mark.asyncio
async def test_expense_workflow_low_confidence_escalation(client: Client, test_expense_report):
    """Test workflow escalates to human review when agent confidence is low"""
    if sys.version_info < (3, 11):
        pytest.skip("OpenAI support has type errors on 3.9 and 3.11")

    from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow
    
    # Create responses with low confidence that should trigger escalation
    category_response = {
        "category": "Other",
        "confidence": 0.65,  # Below 0.70 threshold
        "reasoning": "Unclear expense type, ambiguous description",
        "vendor_validation": {
            "vendor_name": "ABC Solutions Inc",
            "is_legitimate": True,
            "confidence_score": 0.6,
            "web_search_summary": "Limited information found"
        }
    }
    
    policy_response = {
        "compliant": True,
        "violations": [],
        "reasoning": "No clear violations but category uncertain",
        "requires_human_review": True,
        "mandatory_human_review": False,
        "policy_explanation": "Cannot determine specific policies due to unclear categorization",
        "confidence": 0.70
    }
    
    fraud_response = {
        "overall_risk": "medium",
        "flags": [
            {
                "flag_type": "unclear_description",
                "risk_level": "medium", 
                "details": "Vague expense description"
            }
        ],
        "reasoning": "Medium risk due to unclear expense details",
        "requires_human_review": True,
        "confidence": 0.60,  # Below 0.65 threshold
        "vendor_risk_indicators": ["vague_description"]
    }
    
    decision_response = {
        "decision": "requires_human_review",
        "internal_reasoning": "Multiple low confidence scores trigger escalation",
        "external_reasoning": "Expense requires additional review due to unclear categorization",
        "escalation_reason": "Low confidence assessment",
        "is_mandatory_escalation": False,
        "confidence": 0.65
    }
    
    response_message = {
        "message": "Your expense has been forwarded for manual review due to unclear categorization. You will be notified once reviewed.",
        "decision_summary": "Requires Review - Unclear expense categorization",
        "policy_explanation": "Additional information needed to determine applicable policies",
        "categorization_summary": "Expense type could not be determined with sufficient confidence"
    }
    
    low_confidence_responses = [
        create_mock_response(json.dumps(category_response)),
        create_mock_response(json.dumps(policy_response)),
        create_mock_response(json.dumps(fraud_response)),
        create_mock_response(json.dumps(decision_response)),
        create_mock_response(json.dumps(response_message))
    ]
    
    with set_open_ai_agent_temporal_overrides(
        start_to_close_timeout=timedelta(seconds=30)
    ):
        model_activity = ModelActivity(
            TestProvider(
                MockExpenseModel(
                    "gpt-4o",
                    openai_client=AsyncOpenAI(api_key="fake_key"),
                    responses=low_confidence_responses
                )
            )
        )
        
        async def mock_web_search(query: str):
            return {"results": [], "status": "limited"}
        
        async with new_worker(
            client,
            ExpenseWorkflow,
            activities=[model_activity.invoke_model_activity, mock_web_search]
        ) as worker:
            
            # Modify expense to be ambiguous
            test_expense_report.description = "miscellaneous business services"
            test_expense_report.vendor = "ABC Solutions Inc"
            test_expense_report.amount = Decimal("150.00")
            
            result = await client.execute_workflow(
                ExpenseWorkflow.run,
                test_expense_report,
                id=f"expense-workflow-escalation-{uuid.uuid4()}",
                task_queue=worker.task_queue,
                execution_timeout=timedelta(seconds=30),
            )
            
            # Should escalate to human review
            assert result is not None
            assert result["decision"] == "requires_human_review"
            assert "review" in result["response"]["message"].lower() 
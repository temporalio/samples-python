from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from expense.ui import ExpenseState, all_expenses, app, workflow_map


class TestExpenseUI:
    """Test suite for the Expense System UI based on the specification"""

    def setup_method(self):
        """Reset state before each test"""
        all_expenses.clear()
        workflow_map.clear()

    @pytest.fixture
    def client(self):
        """FastAPI test client fixture"""
        return TestClient(app)

    def test_list_view_empty(self, client):
        """Test list view with no expenses"""
        response = client.get("/")
        assert response.status_code == 200
        assert "SAMPLE EXPENSE SYSTEM" in response.text
        assert "<table border=1>" in response.text
        assert "<th>Expense ID</th>" in response.text

    def test_list_view_with_expenses(self, client):
        """Test list view displaying expenses in sorted order"""
        # Setup test data
        all_expenses["EXP-003"] = ExpenseState.CREATED
        all_expenses["EXP-001"] = ExpenseState.APPROVED
        all_expenses["EXP-002"] = ExpenseState.REJECTED

        response = client.get("/list")
        assert response.status_code == 200

        # Check sorted order in HTML
        html = response.text
        exp001_pos = html.find("EXP-001")
        exp002_pos = html.find("EXP-002")
        exp003_pos = html.find("EXP-003")

        assert exp001_pos < exp002_pos < exp003_pos

    def test_list_view_action_buttons_only_for_created(self, client):
        """Test that action buttons only appear for CREATED expenses"""
        all_expenses["created-expense"] = ExpenseState.CREATED
        all_expenses["approved-expense"] = ExpenseState.APPROVED
        all_expenses["rejected-expense"] = ExpenseState.REJECTED
        all_expenses["completed-expense"] = ExpenseState.COMPLETED

        response = client.get("/")
        html = response.text

        # CREATED expense should have buttons
        assert "APPROVE" in html
        assert "REJECT" in html
        assert "created-expense" in html

        # Count actual button elements - should only be for the CREATED expense
        approve_count = html.count(
            '<button type="submit" style="background-color:#4CAF50;">APPROVE</button>'
        )
        reject_count = html.count(
            '<button type="submit" style="background-color:#f44336;">REJECT</button>'
        )
        assert approve_count == 1
        assert reject_count == 1

    def test_create_expense_success_ui(self, client):
        """Test successful expense creation via UI"""
        response = client.get("/create?id=new-expense")
        assert response.status_code == 200
        assert all_expenses["new-expense"] == ExpenseState.CREATED
        assert "SAMPLE EXPENSE SYSTEM" in response.text  # Should redirect to list

    def test_create_expense_success_api(self, client):
        """Test successful expense creation via API"""
        response = client.get("/create?id=new-expense&is_api_call=true")
        assert response.status_code == 200
        assert response.text == "SUCCEED"
        assert all_expenses["new-expense"] == ExpenseState.CREATED

    def test_create_expense_duplicate_ui(self, client):
        """Test creating duplicate expense via UI"""
        all_expenses["existing"] = ExpenseState.CREATED

        response = client.get("/create?id=existing")
        assert response.status_code == 200
        assert response.text == "ID already exists"

    def test_create_expense_duplicate_api(self, client):
        """Test creating duplicate expense via API"""
        all_expenses["existing"] = ExpenseState.CREATED

        response = client.get("/create?id=existing&is_api_call=true")
        assert response.status_code == 200
        assert response.text == "ERROR:ID_ALREADY_EXISTS"

    def test_status_check_valid_id(self, client):
        """Test status check for valid expense ID"""
        all_expenses["test-expense"] = ExpenseState.APPROVED

        response = client.get("/status?id=test-expense")
        assert response.status_code == 200
        assert response.text == "APPROVED"

    def test_status_check_invalid_id(self, client):
        """Test status check for invalid expense ID"""
        response = client.get("/status?id=nonexistent")
        assert response.status_code == 200
        assert response.text == "ERROR:INVALID_ID"

    def test_action_approve_ui(self, client):
        """Test approve action via UI"""
        all_expenses["test-expense"] = ExpenseState.CREATED

        with patch("expense.ui.notify_expense_state_change") as mock_notify:
            response = client.post(
                "/action", data={"type": "approve", "id": "test-expense"}
            )
            assert response.status_code == 200
            assert all_expenses["test-expense"] == ExpenseState.APPROVED
            # Should redirect to list view
            assert response.url.path == "/list"
            mock_notify.assert_called_once_with("test-expense", ExpenseState.APPROVED)

    def test_action_approve_api(self, client):
        """Test approve action via API"""
        all_expenses["test-expense"] = ExpenseState.CREATED

        with patch("expense.ui.notify_expense_state_change") as mock_notify:
            response = client.post(
                "/action",
                data={"type": "approve", "id": "test-expense", "is_api_call": "true"},
            )
            assert response.status_code == 200
            assert response.text == "SUCCEED"
            assert all_expenses["test-expense"] == ExpenseState.APPROVED
            mock_notify.assert_called_once_with("test-expense", ExpenseState.APPROVED)

    def test_action_reject_ui(self, client):
        """Test reject action via UI"""
        all_expenses["test-expense"] = ExpenseState.CREATED

        with patch("expense.ui.notify_expense_state_change") as mock_notify:
            response = client.post(
                "/action", data={"type": "reject", "id": "test-expense"}
            )
            assert response.status_code == 200
            assert all_expenses["test-expense"] == ExpenseState.REJECTED
            # Should redirect to list view
            assert response.url.path == "/list"
            mock_notify.assert_called_once_with("test-expense", ExpenseState.REJECTED)

    def test_action_payment(self, client):
        """Test payment action"""
        all_expenses["test-expense"] = ExpenseState.APPROVED

        response = client.post(
            "/action",
            data={"type": "payment", "id": "test-expense", "is_api_call": "true"},
        )
        assert response.status_code == 200
        assert response.text == "SUCCEED"
        assert all_expenses["test-expense"] == ExpenseState.COMPLETED

    def test_action_invalid_id_ui(self, client):
        """Test action with invalid ID via UI"""
        response = client.post("/action", data={"type": "approve", "id": "nonexistent"})
        assert response.status_code == 200
        assert response.text == "Invalid ID"

    def test_action_invalid_id_api(self, client):
        """Test action with invalid ID via API"""
        response = client.post(
            "/action",
            data={"type": "approve", "id": "nonexistent", "is_api_call": "true"},
        )
        assert response.status_code == 200
        assert response.text == "ERROR:INVALID_ID"

    def test_action_invalid_type_ui(self, client):
        """Test action with invalid type via UI"""
        all_expenses["test-expense"] = ExpenseState.CREATED

        response = client.post(
            "/action", data={"type": "invalid", "id": "test-expense"}
        )
        assert response.status_code == 200
        assert response.text == "Invalid action type"

    def test_action_invalid_type_api(self, client):
        """Test action with invalid type via API"""
        all_expenses["test-expense"] = ExpenseState.CREATED

        response = client.post(
            "/action",
            data={"type": "invalid", "id": "test-expense", "is_api_call": "true"},
        )
        assert response.status_code == 200
        assert response.text == "ERROR:INVALID_TYPE"

    def test_register_callback_success(self, client):
        """Test successful callback registration"""
        all_expenses["test-expense"] = ExpenseState.CREATED
        test_token = "deadbeef"

        response = client.post(
            "/registerWorkflow?id=test-expense", data={"workflow_id": test_token}
        )
        assert response.status_code == 200
        assert response.text == "SUCCEED"
        assert workflow_map["test-expense"] == test_token

    def test_register_workflow_invalid_id(self, client):
        """Test workflow registration with invalid ID"""
        response = client.post(
            "/registerWorkflow?id=nonexistent", data={"workflow_id": "workflow-123"}
        )
        assert response.status_code == 200
        assert response.text == "ERROR:INVALID_ID"

    def test_register_workflow_invalid_state(self, client):
        """Test workflow registration with non-CREATED expense"""
        all_expenses["test-expense"] = ExpenseState.APPROVED

        response = client.post(
            "/registerWorkflow?id=test-expense", data={"workflow_id": "workflow-123"}
        )
        assert response.status_code == 200
        assert response.text == "ERROR:INVALID_STATE"

    @pytest.mark.asyncio
    async def test_notify_expense_state_change_success(self):
        """Test successful workflow notification"""
        # Setup
        expense_id = "test-expense"
        test_workflow_id = "workflow-123"
        workflow_map[expense_id] = test_workflow_id

        # Mock workflow client and workflow handle
        mock_handle = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_workflow_handle.return_value = mock_handle

        with patch("expense.ui.workflow_client", mock_client):
            from expense.ui import notify_expense_state_change

            await notify_expense_state_change(expense_id, "APPROVED")

            mock_client.get_workflow_handle.assert_called_once_with(test_workflow_id)
            mock_handle.signal.assert_called_once_with(
                "expense_decision_signal", "APPROVED"
            )

    @pytest.mark.asyncio
    async def test_notify_expense_state_change_invalid_id(self):
        """Test workflow notification with invalid expense ID"""
        from expense.ui import notify_expense_state_change

        # Should not raise exception for invalid ID
        await notify_expense_state_change("nonexistent", "APPROVED")

    @pytest.mark.asyncio
    async def test_notify_expense_state_change_client_error(self):
        """Test workflow notification when client fails"""
        expense_id = "test-expense"
        test_workflow_id = "workflow-123"
        workflow_map[expense_id] = test_workflow_id

        mock_client = MagicMock()
        mock_client.get_workflow_handle.side_effect = Exception("Client error")

        with patch("expense.ui.workflow_client", mock_client):
            from expense.ui import notify_expense_state_change

            # Should not raise exception even if client fails
            await notify_expense_state_change(expense_id, "APPROVED")

    def test_state_transitions_complete_workflow(self, client):
        """Test complete expense workflow state transitions"""
        expense_id = "workflow-expense"

        # 1. Create expense
        response = client.get(f"/create?id={expense_id}&is_api_call=true")
        assert response.text == "SUCCEED"
        assert all_expenses[expense_id] == ExpenseState.CREATED

        # 2. Register workflow
        test_workflow_id = "workflow-123"
        response = client.post(
            f"/registerWorkflow?id={expense_id}", data={"workflow_id": test_workflow_id}
        )
        assert response.text == "SUCCEED"

        # 3. Approve expense
        with patch("expense.ui.notify_expense_state_change") as mock_notify:
            response = client.post(
                "/action",
                data={"type": "approve", "id": expense_id, "is_api_call": "true"},
            )
            assert response.text == "SUCCEED"
            assert all_expenses[expense_id] == ExpenseState.APPROVED
            mock_notify.assert_called_once_with(expense_id, ExpenseState.APPROVED)

        # 4. Process payment
        response = client.post(
            "/action", data={"type": "payment", "id": expense_id, "is_api_call": "true"}
        )
        assert response.text == "SUCCEED"
        assert all_expenses[expense_id] == ExpenseState.COMPLETED

    def test_html_response_structure(self, client):
        """Test HTML response contains required elements"""
        all_expenses["test-expense"] = ExpenseState.CREATED

        response = client.get("/")
        html = response.text

        # Check required HTML elements
        assert "<h1>SAMPLE EXPENSE SYSTEM</h1>" in html
        assert '<a href="/list">HOME</a>' in html
        assert "<table border=1>" in html
        assert "<th>Expense ID</th>" in html
        assert "<th>Status</th>" in html
        assert "<th>Action</th>" in html
        assert 'style="background-color:#4CAF50;"' in html  # Green approve button
        assert 'style="background-color:#f44336;"' in html  # Red reject button

    def test_concurrent_operations(self, client):
        """Test handling of concurrent operations"""
        import threading

        results = []

        def create_expense(expense_id):
            try:
                response = client.get(f"/create?id={expense_id}&is_api_call=true")
                results.append((expense_id, response.status_code, response.text))
            except Exception as e:
                results.append((expense_id, "error", str(e)))

        # Create multiple expenses concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_expense, args=[f"concurrent-{i}"])
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should succeed
        assert len(results) == 5
        for expense_id, status_code, text in results:
            assert status_code == 200
            assert text == "SUCCEED"
            assert expense_id in all_expenses

    def test_parameter_validation(self, client):
        """Test parameter validation for all endpoints"""
        # Missing required parameters
        response = client.get("/create")  # Missing id
        assert response.status_code == 422  # FastAPI validation error

        response = client.post("/action")  # Missing type and id
        assert response.status_code == 422

        response = client.get("/status")  # Missing id
        assert response.status_code == 422

        response = client.post("/registerWorkflow")  # Missing id and workflow_id
        assert response.status_code == 422

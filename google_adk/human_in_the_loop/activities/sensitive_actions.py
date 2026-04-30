from temporalio import activity


@activity.defn
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email (mock implementation)."""
    return f"Email sent to {to} with subject '{subject}'"


@activity.defn
async def delete_record(record_id: str) -> str:
    """Delete a record from the database (mock implementation)."""
    return f"Record {record_id} deleted successfully"

from dataclasses import dataclass
from temporalio import activity

@dataclass
class SendEmailInput:
    email_msg: str

@activity.defn(name="send_email")
async def send_email(input: SendEmailInput) -> str:
    """
    A stub Activity for sending an email.
    """
    result = f"Email message: {input.email_msg}, sent"
    print(result)
    return result
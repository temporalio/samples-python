from dataclasses import dataclass

from temporalio import activity


@dataclass
class SendEmailInput:
    email_msg: str


@activity.defn()
async def send_email(input: SendEmailInput) -> str:
    """
    A stub Activity for sending an email.
    """
    result = f"Email message: {input.email_msg}, sent"
    activity.logger.info(result)
    return result

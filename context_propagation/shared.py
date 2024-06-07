from contextvars import ContextVar
from typing import Optional

HEADER_KEY = "__my_user_id"

user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)

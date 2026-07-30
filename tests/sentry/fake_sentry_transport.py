import sentry_sdk
import sentry_sdk.types


class FakeSentryTransport:
    """A fake transport that captures Sentry events in memory"""

    # Note: we could extend from sentry_sdk.transport.Transport
    # but `sentry_sdk.init` also takes a simple callable that takes
    # an Event rather than a serialised Envelope object, so testing
    # is easier.

    def __init__(self):
        self.events: list[sentry_sdk.types.Event] = []

    def __call__(self, event: sentry_sdk.types.Event) -> None:
        self.events.append(event)

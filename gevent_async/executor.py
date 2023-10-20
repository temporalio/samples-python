import functools
from concurrent.futures import Future
from typing import Callable, TypeVar

from gevent import threadpool
from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


class GeventExecutor(threadpool.ThreadPoolExecutor):
    def submit(
        self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> Future[T]:
        # Gevent's returned futures do not map well to Python futures, so we
        # must translate. We can't just use set_result/set_exception because
        # done callbacks are not always called in gevent's case and it doesn't
        # seem to support cancel, so we instead wrap the caller function.
        python_fut: Future[T] = Future()

        @functools.wraps(fn)
        def wrapper(*w_args: P.args, **w_kwargs: P.kwargs) -> None:
            try:
                result = fn(*w_args, **w_kwargs)
                # Swallow InvalidStateError in case Python future was cancelled
                try:
                    python_fut.set_result(result)
                except:
                    pass
            except Exception as exc:
                # Swallow InvalidStateError in case Python future was cancelled
                try:
                    python_fut.set_exception(exc)
                except:
                    pass

        # Submit our wrapper to gevent
        super().submit(wrapper, *args, **kwargs)
        # Return Python future to user
        return python_fut

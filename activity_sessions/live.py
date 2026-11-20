"""Live terminal view; the entrypoints run the same without it (--no-live)."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from rich.console import Console, RenderableType
from rich.live import Live

T = TypeVar("T")


async def run_live(
    console: Console,
    no_live: bool,
    render: Callable[[], RenderableType],
    work: Callable[[Callable[[], None]], Awaitable[T]],
) -> T:
    """Run `work`, re-rendering `render` each time it calls its refresh argument."""
    if no_live or not console.is_terminal:
        return await work(lambda: None)
    with Live(console=console, auto_refresh=False, transient=True) as live:
        return await work(lambda: live.update(render(), refresh=True))

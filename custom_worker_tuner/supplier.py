from __future__ import annotations

import asyncio
import itertools
import logging

from temporalio.worker import (
    CustomSlotSupplier,
    SlotMarkUsedContext,
    SlotPermit,
    SlotReleaseContext,
    SlotReserveContext,
)

from custom_worker_tuner.downstream import Downstream

logger = logging.getLogger(__name__)

_slot_id_gen = itertools.count(1)


class _Permit(SlotPermit):
    """SlotPermit subclass that just carries a sequential id for logs."""

    def __init__(self, slot_id: int) -> None:
        super().__init__()
        self.slot_id = slot_id


class DownstreamAwareSupplier(CustomSlotSupplier):
    def __init__(self, downstream: Downstream, poll_interval_ms: int = 100) -> None:
        self.downstream = downstream
        self.poll_interval_ms = poll_interval_ms
        logger.info(
            "DownstreamAwareSupplier ready: downstream=%s poll_interval_ms=%d",
            downstream.name,
            poll_interval_ms,
        )

    async def reserve_slot(self, ctx: SlotReserveContext) -> SlotPermit:
        """block downstream until it has capacity to get incremented and then grant a slot."""
        slot_id = next(_slot_id_gen)
        while not self.downstream.increment():
            await asyncio.sleep(self.poll_interval_ms / 1000.0)
        self._log("reserve", slot_id, "ready to poll")
        return _Permit(slot_id)

    def try_reserve_slot(self, ctx: SlotReserveContext) -> SlotPermit | None:
        """Eager path: can i run this activity right now?"""
        if self.downstream.increment():
            slot_id = next(_slot_id_gen)
            self._log("reserve", slot_id, "eager dispatch")
            return _Permit(slot_id)
        return None

    def mark_slot_used(self, ctx: SlotMarkUsedContext) -> None:
        """A task arrived for a reserved slot"""
        slot_id = getattr(ctx.permit, "slot_id", "?")
        self._log("used", slot_id, "activity running")

    def release_slot(self, ctx: SlotReleaseContext) -> None:
        """Return the slot to the downstream."""
        slot_id = getattr(ctx.permit, "slot_id", "?")
        detail = "no task arrived" if ctx.slot_info is None else "activity done"
        self.downstream.decrement()
        self._log("release", slot_id, detail)

    def _log(self, event: str, slot_id, note: str) -> None:
        count = f"{self.downstream.currently_connected}/{self.downstream.allowed_connections}"
        logger.info(f"{event:<8}  {count:>5}  {note}")

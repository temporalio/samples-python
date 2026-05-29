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

from custom_worker_tuner.db_pool import FakeDatabaseConnectionPool

logger = logging.getLogger(__name__)

_slot_id_gen = itertools.count(1)


class _Permit(SlotPermit):
    """SlotPermit subclass that just carries a sequential id for logs."""

    def __init__(self, slot_id: int) -> None:
        super().__init__()
        self.slot_id = slot_id


class PoolSlotSupplier(CustomSlotSupplier):
    """Hands out slots only when the backing pool has a free connection."""

    def __init__(self, connection_pool: FakeDatabaseConnectionPool) -> None:
        self.connection_pool = connection_pool
        logger.info("PoolSlotSupplier ready: connection_pool=%s", connection_pool.name)

    async def reserve_slot(self, ctx: SlotReserveContext) -> SlotPermit:
        """Block until the pool has capacity, then grant a slot."""
        await asyncio.to_thread(self.connection_pool.acquire)
        slot_id = next(_slot_id_gen)
        self._log("reserve", slot_id, "ready to poll")
        return _Permit(slot_id)

    def try_reserve_slot(self, ctx: SlotReserveContext) -> SlotPermit | None:
        """Eager path: try to claim a slot without blocking."""
        if self.connection_pool.acquire(blocking=False):
            slot_id = next(_slot_id_gen)
            self._log("reserve", slot_id, "eager dispatch")
            return _Permit(slot_id)
        return None

    def mark_slot_used(self, ctx: SlotMarkUsedContext) -> None:
        slot_id = getattr(ctx.permit, "slot_id", "?")
        self._log("used", slot_id, "activity running")

    def release_slot(self, ctx: SlotReleaseContext) -> None:
        slot_id = getattr(ctx.permit, "slot_id", "?")
        detail = "no task arrived" if ctx.slot_info is None else "activity done"
        self.connection_pool.release()
        self._log("release", slot_id, detail)

    def _log(self, event: str, slot_id, note: str) -> None:
        count = f"{self.connection_pool.in_use}/{self.connection_pool.allowed_connections}"
        logger.info(f"{event:<8}  {count:>5}  {note}")

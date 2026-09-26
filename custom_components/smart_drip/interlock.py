"""Solenoid Interlock Manager enforcing mutual exclusion and safety delays."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Final

from .const import (
    DEFAULT_SAFETY_LIMIT_SECONDS,
    HARD_SAFETY_LIMIT_SECONDS,
    INTERLOCK_DELAY_SECONDS,
)

_LOGGER: Final = logging.getLogger(__name__)


class ValveActuationError(RuntimeError):
    """Raised when an actuation violation or safety constraint is encountered."""


class SolenoidInterlock:
    """Manages mutual exclusion and safety delays for dual latching solenoids."""

    def __init__(
        self,
        interlock_delay: int = INTERLOCK_DELAY_SECONDS,
        max_duration_seconds: int = DEFAULT_SAFETY_LIMIT_SECONDS,
        hard_limit_seconds: int = HARD_SAFETY_LIMIT_SECONDS,
    ) -> None:
        """Initialize the interlock manager."""
        self._interlock_delay = max(1, interlock_delay)
        self._max_duration_seconds = max(1, max_duration_seconds)
        self._hard_limit_seconds = max(self._max_duration_seconds, hard_limit_seconds)
        self._lock = asyncio.Lock()
        self._active_channel: int | None = None
        self._remaining_seconds: int = 0

    @property
    def is_active(self) -> bool:
        """Return True if a valve is currently open."""
        return self._active_channel is not None

    @property
    def active_channel(self) -> int | None:
        """Return the channel currently open, or None."""
        return self._active_channel

    @property
    def remaining_seconds(self) -> int:
        """Return remaining seconds in active irrigation run."""
        return self._remaining_seconds

    async def execute_irrigation(
        self,
        channel: int,
        duration_seconds: int,
        turn_on_fn: Callable[[], Awaitable[None]],
        turn_off_fn: Callable[[], Awaitable[None]],
    ) -> None:
        """Execute a guarded irrigation cycle with enforced hardware interlock.

        Enforces:
        1. Mutual exclusion: Cannot run if another channel is open.
        2. Clamped safety ceiling (max_duration_seconds / hard_limit_seconds).
        3. Guaranteed shutoff on any error or cancellation.
        4. Interlock delay (10s) following closure to allow latching capacitor recharge.
        """
        if self._lock.locked() or self.is_active:
            raise ValveActuationError(
                f"Channel {self._active_channel} is currently active. "
                f"Cannot actuate Channel {channel} concurrently."
            )

        clamped_duration = max(
            0, min(duration_seconds, self._max_duration_seconds, self._hard_limit_seconds)
        )
        if clamped_duration == 0:
            _LOGGER.info("Requested duration for Channel %s is 0 seconds; skipping.", channel)
            return

        async with self._lock:
            self._active_channel = channel
            self._remaining_seconds = clamped_duration
            _LOGGER.info(
                "Opening Channel %s for %s seconds (clamped safety ceiling).",
                channel,
                clamped_duration,
            )

            try:
                # Actuate opening
                await turn_on_fn()

                # Sleep for irrigation duration
                await asyncio.sleep(clamped_duration)
            finally:
                # Guaranteed shutoff under any outcome (success, cancellation, exception)
                try:
                    await turn_off_fn()
                    _LOGGER.info("Closed Channel %s successfully.", channel)
                except Exception as err:
                    _LOGGER.critical(
                        "CRITICAL: Failed to turn off Channel %s: %s", channel, err, exc_info=True
                    )
                finally:
                    self._active_channel = None
                    self._remaining_seconds = 0

                    # Mandatory capacitor recharge & pressure stabilization pause
                    _LOGGER.debug(
                        "Enforcing %s second idle interlock pause.", self._interlock_delay
                    )
                    await asyncio.sleep(self._interlock_delay)

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class RuntimeUnavailableError(RuntimeError):
    """Raised when no validated Runtime adapter exists for an account."""


@dataclass(frozen=True)
class RuntimeStatus:
    account_id: str
    kind: str
    state: str
    detail: str | None = None
    qr_reference: str | None = None


class RuntimeAdapter(Protocol):
    kind: str

    def start(self, account_id: str, runtime_ref: str | None) -> RuntimeStatus:
        ...

    def stop(self, account_id: str, runtime_ref: str | None) -> RuntimeStatus:
        ...

    def status(self, account_id: str, runtime_ref: str | None) -> RuntimeStatus:
        ...


class RuntimeManager:
    """Dispatches Runtime lifecycle calls without binding the archive to Docker."""

    def __init__(self, adapters: list[RuntimeAdapter] | None = None) -> None:
        self._adapters = {adapter.kind: adapter for adapter in adapters or []}

    def register(self, adapter: RuntimeAdapter) -> None:
        self._adapters[adapter.kind] = adapter

    def _adapter(self, kind: str) -> RuntimeAdapter:
        try:
            return self._adapters[kind]
        except KeyError as exc:
            raise RuntimeUnavailableError(f"no Runtime adapter registered for {kind}") from exc

    def start(self, account_id: str, kind: str, runtime_ref: str | None = None) -> RuntimeStatus:
        return self._adapter(kind).start(account_id, runtime_ref)

    def stop(self, account_id: str, kind: str, runtime_ref: str | None = None) -> RuntimeStatus:
        return self._adapter(kind).stop(account_id, runtime_ref)

    def status(self, account_id: str, kind: str, runtime_ref: str | None = None) -> RuntimeStatus:
        return self._adapter(kind).status(account_id, runtime_ref)

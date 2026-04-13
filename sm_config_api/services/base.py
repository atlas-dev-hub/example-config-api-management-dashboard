"""Base service class for all System Monitor gRPC service wrappers.

Every service (System, Project, Parameter, Logging, Virtual) inherits from
:class:`BaseService`, which provides:

- A unified ``_call()`` method that wraps every gRPC RPC with:
  - Automatic ``return_code`` checking → raises typed :class:`SystemMonitorError`
  - ``grpc.RpcError`` translation to friendly Python exceptions
  - Per-call timing via :mod:`logging`
  - Optional per-call timeout and extra metadata
- A stub factory so each subclass only needs to declare its stub class.

Typical subclass usage::

    class SystemService(BaseService):
        _stub_class = SystemMonitorSystemStub

        def get_status(self) -> StatusReply:
            return self._call(self._stub.GetStatus)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Sequence, TypeVar

import grpc
from google.protobuf.empty_pb2 import Empty
from google.protobuf.message import Message

from sm_config_api.errors import SystemMonitorError, raise_for_error_code

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Message)


# ---------------------------------------------------------------------------
# gRPC → Python exception mapping
# ---------------------------------------------------------------------------

_GRPC_CODE_TO_MESSAGE: dict[grpc.StatusCode, str] = {
    grpc.StatusCode.UNAVAILABLE: "Server unavailable — is System Monitor running at the target address?",
    grpc.StatusCode.DEADLINE_EXCEEDED: "Request timed out",
    grpc.StatusCode.UNAUTHENTICATED: "Authentication failed — check certificates and/or OAuth2 token",
    grpc.StatusCode.PERMISSION_DENIED: "Permission denied — check API access rights",
    grpc.StatusCode.UNIMPLEMENTED: "RPC not implemented — check System Monitor version (requires ≥8.85)",
    grpc.StatusCode.INTERNAL: "Internal server error",
    grpc.StatusCode.CANCELLED: "Request was cancelled",
}


class GrpcError(SystemMonitorError):
    """Raised when a gRPC transport-level error occurs.

    Wraps :class:`grpc.RpcError` with a friendlier message while preserving
    the original gRPC status code and details.

    Attributes:
        grpc_code: The :class:`grpc.StatusCode` from the failed call.
        details: The gRPC error details string.
    """

    def __init__(self, rpc_error: grpc.RpcError):
        self.grpc_code: grpc.StatusCode = rpc_error.code()
        self.details: str = rpc_error.details() or ""
        friendly = _GRPC_CODE_TO_MESSAGE.get(self.grpc_code, "gRPC error")
        message = f"{friendly} ({self.grpc_code.name}: {self.details})"
        # Use code=0 since this isn't an API-level ErrorCode
        super().__init__(code=0, message=message)
        self.__cause__ = rpc_error


class ConnectionFailedError(GrpcError):
    """Server is unreachable (gRPC UNAVAILABLE)."""


class AuthenticationError(GrpcError):
    """Authentication or authorization failure."""


class TimeoutError(GrpcError):  # noqa: A001 — intentionally shadows builtin for clarity
    """RPC deadline exceeded."""


def _grpc_error_to_exception(rpc_error: grpc.RpcError) -> GrpcError:
    """Map a :class:`grpc.RpcError` to the most specific :class:`GrpcError` subclass."""
    code = rpc_error.code()
    if code == grpc.StatusCode.UNAVAILABLE:
        return ConnectionFailedError(rpc_error)
    if code in (grpc.StatusCode.UNAUTHENTICATED, grpc.StatusCode.PERMISSION_DENIED):
        return AuthenticationError(rpc_error)
    if code == grpc.StatusCode.DEADLINE_EXCEEDED:
        return TimeoutError(rpc_error)
    return GrpcError(rpc_error)


# ---------------------------------------------------------------------------
# Base service
# ---------------------------------------------------------------------------

class BaseService:
    """Base class for all System Monitor gRPC service wrappers.

    Subclasses must set ``_stub_class`` to their generated gRPC stub class.
    The stub is created lazily on first access via ``self._stub``.

    Args:
        channel: An open :class:`grpc.Channel` (from :func:`create_channel`
            or :attr:`Connection.channel`).
        timeout: Default per-call timeout in seconds. ``None`` means no timeout.
        metadata: Extra metadata tuples added to every call (on top of any
            channel-level credentials already configured).
    """

    _stub_class: type | None = None

    def __init__(
        self,
        channel: grpc.Channel,
        *,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] | None = None,
    ):
        self._channel = channel
        self._default_timeout = timeout
        self._default_metadata = tuple(metadata) if metadata else ()
        self._stub_instance: Any = None

    @property
    def _stub(self) -> Any:
        """Lazily-initialised gRPC stub for this service."""
        if self._stub_instance is None:
            if self._stub_class is None:
                raise NotImplementedError(
                    f"{type(self).__name__} must set _stub_class to a gRPC stub class"
                )
            self._stub_instance = self._stub_class(self._channel)
        return self._stub_instance

    # ---- Core call wrapper ----

    def _call(
        self,
        method: Callable[..., T],
        request: Message | None = None,
        *,
        check_return_code: bool = True,
        timeout: float | None = ...,  # type: ignore[assignment]  — sentinel
        metadata: Sequence[tuple[str, str]] | None = None,
    ) -> T:
        """Invoke a gRPC method with error handling, timing, and return-code checking.

        Args:
            method: A bound method on the stub, e.g. ``self._stub.GetStatus``.
            request: The protobuf request message. Defaults to ``Empty()``
                if the RPC takes no parameters.
            check_return_code: If ``True`` (default), inspect the response's
                ``return_code`` field and raise a typed
                :class:`~sm_config_api.errors.SystemMonitorError` when non-zero.
            timeout: Per-call timeout in seconds. Pass ``None`` to disable.
                Omit to use the service's default timeout.
            metadata: Extra metadata tuples for *this call only*, merged with
                any service-level default metadata.

        Returns:
            The protobuf response message.

        Raises:
            SystemMonitorError: If the response contains a non-zero ``return_code``.
            ConnectionFailedError: If the server is unreachable.
            AuthenticationError: If authentication/authorization fails.
            TimeoutError: If the call exceeds the deadline.
            GrpcError: For any other gRPC transport error.
        """
        if request is None:
            request = Empty()

        # Resolve timeout (sentinel means "use default")
        effective_timeout = self._default_timeout if timeout is ... else timeout

        # Merge metadata
        effective_metadata: tuple[tuple[str, str], ...] | None = None
        if self._default_metadata or metadata:
            effective_metadata = self._default_metadata + tuple(metadata or ())

        method_name = getattr(method, "_method", None) or method.__name__
        # Strip leading slash and service path for concise logging
        short_name = method_name.rsplit("/", 1)[-1] if isinstance(method_name, str) else method_name

        logger.debug("→ %s", short_name)
        t0 = time.perf_counter()

        try:
            response = method(
                request,
                timeout=effective_timeout,
                metadata=effective_metadata or None,
            )
        except grpc.RpcError as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.error("✗ %s failed after %.1fms: %s", short_name, elapsed, exc)
            raise _grpc_error_to_exception(exc) from exc

        elapsed = (time.perf_counter() - t0) * 1000
        logger.debug("✓ %s completed in %.1fms", short_name, elapsed)

        # Check return_code if the response has one
        if check_return_code and hasattr(response, "return_code"):
            rc = response.return_code
            if rc != 0:
                logger.warning(
                    "  %s returned error code %d", short_name, rc,
                )
                raise_for_error_code(rc)

        return response

    # ---- Convenience for streaming RPCs (future use) ----

    def _call_server_stream(
        self,
        method: Callable[..., Any],
        request: Message | None = None,
        *,
        timeout: float | None = ...,  # type: ignore[assignment]
        metadata: Sequence[tuple[str, str]] | None = None,
    ):
        """Invoke a server-streaming RPC. Returns an iterator of response messages.

        Does **not** check ``return_code`` on individual messages automatically;
        the caller should handle that per their needs.
        """
        if request is None:
            request = Empty()

        effective_timeout = self._default_timeout if timeout is ... else timeout
        effective_metadata: tuple[tuple[str, str], ...] | None = None
        if self._default_metadata or metadata:
            effective_metadata = self._default_metadata + tuple(metadata or ())

        method_name = getattr(method, "_method", None) or method.__name__
        short_name = method_name.rsplit("/", 1)[-1] if isinstance(method_name, str) else method_name

        logger.debug("→ %s (stream)", short_name)

        try:
            return method(
                request,
                timeout=effective_timeout,
                metadata=effective_metadata or None,
            )
        except grpc.RpcError as exc:
            logger.error("✗ %s stream failed: %s", short_name, exc)
            raise _grpc_error_to_exception(exc) from exc

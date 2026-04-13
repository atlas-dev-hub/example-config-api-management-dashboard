"""SystemMonitorClient — high-level facade composing all five gRPC services.

This is the main entry point for the library. It manages a single
:class:`Connection` and exposes all five service wrappers as properties::

    from sm_config_api.client import SystemMonitorClient
    from sm_config_api.connection import ConnectionConfig

    config = ConnectionConfig(address="localhost:7000", insecure=True)
    with SystemMonitorClient(config) as client:
        status = client.system.get_status()
        apps = client.project.get_app_details()
        params = client.parameter.get_parameters(0x7001, data_type=0)

Multiple clients can coexist for managing several SM instances simultaneously::

    clients = [
        SystemMonitorClient(cfg1),
        SystemMonitorClient(cfg2),
    ]
    for c in clients:
        print(c.system.get_status())
"""

from __future__ import annotations

import logging
from typing import Sequence

from sm_config_api.connection import Connection, ConnectionConfig
from sm_config_api.services.logging_svc import LoggingService
from sm_config_api.services.parameter import ParameterService
from sm_config_api.services.project import ProjectService
from sm_config_api.services.system import SystemService
from sm_config_api.services.virtual import VirtualService

logger = logging.getLogger(__name__)


class SystemMonitorClient:
    """Facade that bundles a connection with all five service wrappers.

    Args:
        config: Connection configuration (address, TLS, OAuth2).
        timeout: Default per-call timeout in seconds applied to all services.
            ``None`` means no timeout.
        metadata: Extra metadata tuples added to every gRPC call across
            all services.

    The client is a context manager::

        with SystemMonitorClient(config) as client:
            print(client.system.get_status())
    """

    def __init__(
        self,
        config: ConnectionConfig,
        *,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] | None = None,
    ):
        self._config = config
        self._timeout = timeout
        self._metadata = metadata
        self._connection: Connection | None = None

        # Lazily-initialised service wrappers
        self._system: SystemService | None = None
        self._project: ProjectService | None = None
        self._parameter: ParameterService | None = None
        self._logging: LoggingService | None = None
        self._virtual: VirtualService | None = None

        # Auto-connect on creation
        self._connect()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        """Open the gRPC connection and initialise all service wrappers."""
        self._connection = Connection(self._config)
        channel = self._connection.channel
        kw = {"timeout": self._timeout, "metadata": self._metadata}

        self._system = SystemService(channel, **kw)
        self._project = ProjectService(channel, **kw)
        self._parameter = ParameterService(channel, **kw)
        self._logging = LoggingService(channel, **kw)
        self._virtual = VirtualService(channel, **kw)

        logger.info("SystemMonitorClient connected to %s", self._config.target)

    def close(self) -> None:
        """Close the underlying gRPC channel and release resources."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("SystemMonitorClient closed")

    @property
    def is_connected(self) -> bool:
        """``True`` if the connection is open."""
        return self._connection is not None

    def reconnect(self) -> None:
        """Close the current connection (if any) and open a fresh one."""
        self.close()
        self._connect()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> SystemMonitorClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        self.close()

    # ------------------------------------------------------------------
    # Service accessors
    # ------------------------------------------------------------------

    @property
    def connection(self) -> Connection:
        """The underlying :class:`Connection` object."""
        if self._connection is None:
            raise RuntimeError("Client is closed — call reconnect() or create a new client")
        return self._connection

    @property
    def system(self) -> SystemService:
        """System Monitor system-level operations (19 RPCs).

        Status, online/offline, unit management, licence, device info,
        logging control, ECU messaging.
        """
        if self._system is None:
            raise RuntimeError("Client is closed")
        return self._system

    @property
    def project(self) -> ProjectService:
        """Project management operations (85 RPCs).

        Open/close/save projects, DTV management, application management,
        CAN configuration, MATLAB import/export, events, errors.
        """
        if self._project is None:
            raise RuntimeError("Client is closed")
        return self._project

    @property
    def parameter(self) -> ParameterService:
        """Parameter operations (60 RPCs).

        Read/write parameter values, conversions, properties, maps,
        warning limits, DTV values.
        """
        if self._parameter is None:
            raise RuntimeError("Client is closed")
        return self._parameter

    @property
    def logging(self) -> LoggingService:
        """Logging configuration operations (22 RPCs).

        Channel properties, triggers, download/upload configs,
        session details, parameter management.
        """
        if self._logging is None:
            raise RuntimeError("Client is closed")
        return self._logging

    @property
    def virtual(self) -> VirtualService:
        """Virtual parameter operations (15 RPCs).

        Create/remove virtual parameters, groups, conversions,
        import/export, data type management.
        """
        if self._virtual is None:
            raise RuntimeError("Client is closed")
        return self._virtual

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def config(self) -> ConnectionConfig:
        """The connection configuration used by this client."""
        return self._config

    def __repr__(self) -> str:
        state = "connected" if self.is_connected else "closed"
        return f"<SystemMonitorClient target={self._config.target!r} {state}>"

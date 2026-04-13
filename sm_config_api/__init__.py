"""System Monitor Configuration API — Python Client.

Quick start::

    from sm_config_api import SystemMonitorClient, ConnectionConfig

    config = ConnectionConfig(address="localhost:7000", insecure=True)
    with SystemMonitorClient(config) as client:
        status = client.system.get_status()
        apps = client.project.get_app_details()
"""

__version__ = "0.1.0"

from sm_config_api.client import SystemMonitorClient
from sm_config_api.connection import Connection, ConnectionConfig, TokenManager, create_channel
from sm_config_api.enums import (
    BufferType,
    ByteOrder,
    ConversionType,
    DataType,
    ErrorCode,
    ErrorStatus,
    EventPriority,
    FileType,
    LinkStatus,
    LoggingType,
    ParameterType,
    Reason,
    TriggerOperator,
    TriggerType,
)
from sm_config_api.errors import SystemMonitorError, raise_for_error_code
from sm_config_api.services.base import (
    AuthenticationError,
    BaseService,
    ConnectionFailedError,
    GrpcError,
    TimeoutError,
)
from sm_config_api.services.logging_svc import LoggingService
from sm_config_api.services.parameter import ParameterService
from sm_config_api.services.project import ProjectService
from sm_config_api.services.system import SystemService
from sm_config_api.services.virtual import VirtualService

__all__ = [
    # Client facade
    "SystemMonitorClient",
    # Connection
    "Connection",
    "ConnectionConfig",
    "TokenManager",
    "create_channel",
    # Services
    "SystemService",
    "ProjectService",
    "ParameterService",
    "LoggingService",
    "VirtualService",
    # Base service
    "BaseService",
    # Enums
    "BufferType",
    "ByteOrder",
    "ConversionType",
    "DataType",
    "ErrorCode",
    "ErrorStatus",
    "EventPriority",
    "FileType",
    "LinkStatus",
    "LoggingType",
    "ParameterType",
    "Reason",
    "TriggerOperator",
    "TriggerType",
    # Errors — API level
    "SystemMonitorError",
    "raise_for_error_code",
    # Errors — transport level
    "AuthenticationError",
    "ConnectionFailedError",
    "GrpcError",
    "TimeoutError",
]

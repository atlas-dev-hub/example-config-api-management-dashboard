"""LoggingService — wrapper for the SystemMonitorLogging gRPC service.

Provides Pythonic access to the 22 Logging-level RPCs covering:

- **Channel properties**: get/set logging channel configuration
- **Triggers**: get/set logging trigger conditions
- **Wrap & offset**: circular-buffer wrap mode and offset
- **Session details**: session metadata (name/value pairs)
- **Duration & parameters**: estimated logging duration and parameter details
- **Download/upload**: logging config transfer to/from ECU
- **Parameter management**: add, remove, clear logging parameters and slot info
- **ECU config**: current ECU logging configuration name

.. note::
   This module is named ``logging_svc.py`` (not ``logging.py``) to avoid
   shadowing Python's built-in :mod:`logging` module.
"""

from __future__ import annotations

from typing import Sequence

from google.protobuf.empty_pb2 import Empty

from sm_config_api.generated import system_monitor_common_pb2 as common_pb2
from sm_config_api.generated import system_monitor_logging_pb2 as pb2
from sm_config_api.generated.system_monitor_logging_pb2_grpc import SystemMonitorLoggingStub
from sm_config_api.services.base import BaseService


class LoggingService(BaseService):
    """Wrapper for the ``SystemMonitorLogging`` gRPC service (22 RPCs)."""

    _stub_class = SystemMonitorLoggingStub

    # ==================================================================
    # Channel properties
    # ==================================================================

    def get_logging_channel_properties(self) -> list[pb2.ChannelProperties]:
        """Get properties for all logging channels.

        Returns:
            List of ``ChannelProperties``, each with ``index``, ``name``,
            ``log_logging``, ``log_telemetry``, ``logging_rate``,
            ``telemetry_rate``, ``trigger_rearm``, ``slot``.
        """
        reply = self._call(self._stub.GetLoggingChannelProperties)
        return list(reply.channels)

    def set_logging_channel_properties(
        self,
        index: int,
        name: str,
        *,
        log_to_unit: bool = False,
        log_telemetry: bool = False,
        trigger_rearm: bool = False,
    ) -> None:
        """Set properties for a logging channel.

        Args:
            index: Channel index.
            name: Channel name.
            log_to_unit: Whether to log to the unit.
            log_telemetry: Whether to log telemetry.
            trigger_rearm: Whether trigger re-arm is enabled.
        """
        request = pb2.ChannelRequest(
            index=index,
            name=name,
            log_to_unit=log_to_unit,
            log_telemetry=log_telemetry,
            trigger_rearm=trigger_rearm,
        )
        self._call(self._stub.SetLoggingChannelProperties, request)

    # ==================================================================
    # Triggers
    # ==================================================================

    def get_logging_triggers(self) -> list[pb2.Trigger]:
        """Get all logging trigger definitions.

        Returns:
            List of ``Trigger``, each with ``index``, ``start_conditions``,
            ``stop_conditions``, ``start_post_trigger``,
            ``stop_post_trigger``, ``slot``.
        """
        reply = self._call(self._stub.GetLoggingTriggers)
        return list(reply.triggers)

    def set_logging_trigger(
        self,
        index: int,
        start_conditions: Sequence[pb2.TriggerCondition],
        stop_conditions: Sequence[pb2.TriggerCondition],
        start_post_trigger: int = 0,
        stop_post_trigger: int = 0,
    ) -> None:
        """Set a logging trigger definition.

        Args:
            index: Trigger index.
            start_conditions: Sequence of ``TriggerCondition`` for start.
            stop_conditions: Sequence of ``TriggerCondition`` for stop.
            start_post_trigger: Post-trigger sample count for start.
            stop_post_trigger: Post-trigger sample count for stop.
        """
        request = pb2.TriggerRequest(
            index=index,
            start_conditions=start_conditions,
            stop_conditions=stop_conditions,
            start_post_trigger=start_post_trigger,
            stop_post_trigger=stop_post_trigger,
        )
        self._call(self._stub.SetLoggingTrigger, request)

    # ==================================================================
    # Wrap & offset
    # ==================================================================

    def get_logging_wrap(self) -> bool:
        """Get the logging wrap (circular buffer) setting.

        Returns:
            ``True`` if wrap mode is enabled, ``False`` otherwise.
        """
        reply = self._call(self._stub.GetLoggingWrap)
        return reply.wrap

    def set_logging_wrap(self, wrap: bool) -> None:
        """Set the logging wrap (circular buffer) setting.

        Args:
            wrap: ``True`` to enable wrap mode, ``False`` to disable.
        """
        request = pb2.WrapRequest(wrap=wrap)
        self._call(self._stub.SetLoggingWrap, request)

    def get_logging_offset(self) -> int:
        """Get the logging offset.

        Returns:
            The current logging offset value.
        """
        reply = self._call(self._stub.GetLoggingOffset)
        return reply.offset

    def set_logging_offset(self, offset: int) -> None:
        """Set the logging offset.

        Args:
            offset: The logging offset value to set.
        """
        request = pb2.LoggingOffsetRequest(offset=offset)
        self._call(self._stub.SetLoggingOffset, request)

    # ==================================================================
    # Session details
    # ==================================================================

    def get_logging_session_details(self, name: str) -> str:
        """Get a logging session detail value by name.

        Args:
            name: The session detail key name.

        Returns:
            The session detail value string.
        """
        request = pb2.GetSessionDetailRequest(name=name)
        reply = self._call(self._stub.GetLoggingSessionDetails, request)
        return reply.value

    def set_logging_session_details(self, name: str, value: str) -> None:
        """Set a logging session detail.

        Args:
            name: The session detail key name.
            value: The session detail value.
        """
        request = pb2.SetSessionDetailRequest(name=name, value=value)
        self._call(self._stub.SetLoggingSessionDetails, request)

    # ==================================================================
    # Duration & parameters
    # ==================================================================

    def get_logging_duration(self) -> pb2.LoggingDurationReply:
        """Get the estimated logging duration and lap count.

        Returns:
            ``LoggingDurationReply`` with ``estimated_time``
            (``google.protobuf.Duration``) and ``estimated_laps``.
        """
        return self._call(self._stub.GetLoggingDuration)

    def get_logging_parameter_details(self) -> pb2.LoggingParametersReply:
        """Get details for all configured logging parameters.

        Returns:
            ``LoggingParametersReply`` with ``parameters`` (list of
            ``LoggingParameter``), ``channel_names``, and ``return_code``.
        """
        return self._call(self._stub.GetLoggingParameterDetails)

    # ==================================================================
    # Download / upload
    # ==================================================================

    def logging_config_download_in_progress(self) -> bool:
        """Check whether a logging config download is currently in progress.

        Returns:
            ``True`` if a download is in progress, ``False`` otherwise.
        """
        reply = self._call(self._stub.LoggingConfigDownloadInProgress)
        return reply.in_progress

    def logging_config_download(
        self,
        app_id: int = 0,
        parameter_id: str = "",
        delay_ms: int = 0,
    ) -> str:
        """Download (read) the logging configuration from the ECU.

        Args:
            app_id: Optional application ID filter.
            parameter_id: Optional parameter ID filter.
            delay_ms: Optional delay in milliseconds.

        Returns:
            The optional value string from the download reply.
        """
        request = pb2.DownloadRequest(
            optional_app_id=app_id,
            optional_parameter_id=parameter_id,
            optional_delay_ms=delay_ms,
        )
        reply = self._call(self._stub.LoggingConfigDownload, request)
        return reply.optional_value

    def logging_config_upload(self) -> None:
        """Upload (write) the logging configuration to the ECU."""
        self._call(self._stub.LoggingConfigUpload)

    # ==================================================================
    # Parameter management
    # ==================================================================

    def remove_logging_parameter(self, app_id: int, parameter_id: str) -> None:
        """Remove a parameter from the logging configuration.

        Args:
            app_id: Application ID that owns the parameter.
            parameter_id: Parameter identifier to remove.
        """
        request = common_pb2.ParameterRequest(
            app_id=app_id,
            parameter_id=parameter_id,
        )
        self._call(self._stub.RemoveLoggingParameter, request)

    def clear_all_logging_parameters(self, remove_triggers: bool = False) -> None:
        """Remove all parameters from the logging configuration.

        Args:
            remove_triggers: If ``True``, also remove all trigger definitions.
        """
        request = pb2.ClearRequest(remove_triggers=remove_triggers)
        self._call(self._stub.ClearAllLoggingParameters, request)

    def get_logging_slots_used(self) -> int:
        """Get the number of logging slots currently in use.

        Returns:
            The slot count.
        """
        reply = self._call(self._stub.GetLoggingSlotsUsed)
        return reply.slot_count

    def get_logging_slot_percentage(self, app_id: int, parameter_id: str) -> float:
        """Get the slot usage percentage for a specific parameter.

        Args:
            app_id: Application ID that owns the parameter.
            parameter_id: Parameter identifier.

        Returns:
            Slot usage as a percentage (0.0–100.0).
        """
        request = common_pb2.ParameterRequest(
            app_id=app_id,
            parameter_id=parameter_id,
        )
        reply = self._call(self._stub.GetLoggingSlotPercentage, request)
        return reply.slot_percentage

    def get_ecu_logging_config(self) -> str:
        """Get the name of the current ECU logging configuration.

        Returns:
            The configuration name string.
        """
        reply = self._call(self._stub.GetECULoggingConfig)
        return reply.config_name

    # ==================================================================
    # Add parameters
    # ==================================================================

    def add_logging_parameter(
        self,
        app_id: int,
        parameter_id: str,
        logging_rate: Sequence[pb2.LoggingChannelValue],
    ) -> None:
        """Add a parameter to the logging configuration.

        Args:
            app_id: Application ID that owns the parameter.
            parameter_id: Parameter identifier to add.
            logging_rate: Sequence of ``LoggingChannelValue`` specifying the
                rate for each channel (``channel_id``, ``type``, ``value``).
        """
        request = pb2.AddParameterRequest(
            app_id=app_id,
            parameter_id=parameter_id,
            logging_rate=logging_rate,
        )
        self._call(self._stub.AddLoggingParameter, request)

    def add_virtual_logging_parameter(
        self,
        parameter_id: str,
        logging_rate: Sequence[pb2.LoggingChannelValue],
    ) -> None:
        """Add a virtual parameter to the logging configuration.

        Args:
            parameter_id: Virtual parameter identifier to add.
            logging_rate: Sequence of ``LoggingChannelValue`` specifying the
                rate for each channel (``channel_id``, ``type``, ``value``).
        """
        request = pb2.AddVirtualParameterRequest(
            parameter_id=parameter_id,
            logging_rate=logging_rate,
        )
        self._call(self._stub.AddVirtualLoggingParameter, request)

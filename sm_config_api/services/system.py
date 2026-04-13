"""SystemService — wrapper for the SystemMonitorSystem gRPC service.

Provides Pythonic access to the 19 System-level RPCs covering:
- Status & connectivity (GetStatus, SetOnline, SetLiveUpdate)
- Unit/car management (GetUnitList, GetUnitName, GetUnitByIndex, SetUnitByIndex)
- Multi-application bases (Get/Set)
- Licence & device info
- Live logging & batch mode
- ECU messaging
- Log folder & PPO file paths
- PGV creation
"""

from __future__ import annotations

from google.protobuf.empty_pb2 import Empty

from sm_config_api.generated import system_monitor_system_pb2 as pb2
from sm_config_api.generated.system_monitor_system_pb2_grpc import SystemMonitorSystemStub
from sm_config_api.services.base import BaseService


class SystemService(BaseService):
    """Wrapper for the ``SystemMonitorSystem`` gRPC service (19 RPCs)."""

    _stub_class = SystemMonitorSystemStub

    # ------------------------------------------------------------------
    # Status & connectivity
    # ------------------------------------------------------------------

    def get_status(self) -> pb2.StatusReply:
        """Get the current System Monitor status.

        Returns:
            ``StatusReply`` with ``link_status``, ``online``, ``live_update``,
            ``return_code``.
        """
        return self._call(self._stub.GetStatus)

    def set_online(self, state: bool) -> None:
        """Set the online state of System Monitor.

        Args:
            state: ``True`` to go online, ``False`` to go offline.
        """
        request = pb2.OnlineRequest(state=state)
        self._call(self._stub.SetOnline, request)

    def set_live_update(self, state: bool, action: int = 0) -> None:
        """Enable or disable live-update mode.

        Args:
            state: ``True`` to enable, ``False`` to disable.
            action: Update action type (default ``0``).
        """
        request = pb2.LiveUpdateRequest(state=state, action=action)
        self._call(self._stub.SetLiveUpdate, request)

    # ------------------------------------------------------------------
    # Units (cars)
    # ------------------------------------------------------------------

    def get_unit_list(self) -> list[pb2.UnitInfo]:
        """Get the list of available units (cars).

        Returns:
            List of ``UnitInfo`` objects, each with ``name``, ``type``,
            ``ip_address``, ``return_code``.
        """
        reply = self._call(self._stub.GetUnitList)
        return list(reply.info)

    def get_unit_name(self) -> str:
        """Get the currently selected unit (car) name.

        Returns:
            The unit name string.
        """
        reply = self._call(self._stub.GetUnitName)
        return reply.name

    def get_unit_by_index(self, index: int) -> pb2.UnitInfo:
        """Get unit details by list index.

        Args:
            index: Zero-based index from :meth:`get_unit_list`.

        Returns:
            ``UnitInfo`` with ``name``, ``type``, ``ip_address``.
        """
        request = pb2.UnitByIndexRequest(index=index)
        return self._call(self._stub.GetUnitByIndex, request)

    def set_unit_by_index(self, index: int, primary: bool = True) -> None:
        """Select a unit by its list index.

        Args:
            index: Zero-based index from :meth:`get_unit_list`.
            primary: Whether this is the primary unit selection.
        """
        request = pb2.UnitByIndexTypeRequest(index=index, primary=primary)
        self._call(self._stub.SetUnitByIndex, request)

    # ------------------------------------------------------------------
    # Multi-application bases
    # ------------------------------------------------------------------

    def get_multi_application_bases(self) -> list[pb2.MultiApplicationBaseInfo]:
        """Get all available multi-application bases.

        Returns:
            List of ``MultiApplicationBaseInfo``, each with ``name``, ``path``.

        Note:
            Returns empty list if a project is already open.
        """
        reply = self._call(self._stub.GetMultiApplicationBases)
        return list(reply.info)

    def get_multi_application_base(self) -> pb2.MultiApplicationBaseInfo:
        """Get the currently active multi-application base.

        Returns:
            ``MultiApplicationBaseInfo`` with ``name`` and ``path``.
        """
        return self._call(self._stub.GetMultiApplicationBase)

    def set_multi_application_base(self, base_name: str) -> None:
        """Set the active multi-application base.

        Args:
            base_name: Name of the base to activate (from
                :meth:`get_multi_application_bases`).
        """
        request = pb2.MultiApplicationBasesRequest(base_name=base_name)
        self._call(self._stub.SetMultiApplicationBase, request)

    # ------------------------------------------------------------------
    # Licence & device info
    # ------------------------------------------------------------------

    def get_licence_details(self) -> pb2.LicenceDetailsReply:
        """Get licence information.

        Returns:
            ``LicenceDetailsReply`` with ``consortium`` and ``owner``.
        """
        return self._call(self._stub.GetLicenceDetails)

    def get_device_properties(self) -> list[pb2.DeviceProperties]:
        """Get properties for all connected devices (ECUs).

        Returns:
            List of ``DeviceProperties``, each with ``device_name``,
            ``comms_path``, ``ip_address``, ``serial_number``.
        """
        reply = self._call(self._stub.GetDeviceProperties)
        return list(reply.devices)

    # ------------------------------------------------------------------
    # Live logging & batch mode
    # ------------------------------------------------------------------

    def get_live_logging(self) -> bool:
        """Get the current live-logging state.

        Returns:
            ``True`` if live logging is active, ``False`` otherwise.
        """
        reply = self._call(self._stub.GetLiveLogging)
        return reply.live_logging_state

    def set_live_logging(self, state: bool) -> None:
        """Enable or disable live logging.

        Args:
            state: ``True`` to enable, ``False`` to disable.
        """
        request = pb2.LiveLoggingRequest(state=state)
        self._call(self._stub.SetLiveLogging, request)

    def set_batch_mode(self, mode: bool) -> None:
        """Enter or exit batch mode.

        When batch mode is active, data-version changes are deferred until
        batch mode is exited, improving performance for bulk operations.

        Args:
            mode: ``True`` to enter batch mode, ``False`` to exit.
        """
        request = pb2.BatchModeRequest(mode=mode)
        self._call(self._stub.SetBatchMode, request)

    # ------------------------------------------------------------------
    # ECU messaging
    # ------------------------------------------------------------------

    def send_message(
        self,
        app_id: int,
        messages: list[int],
        *,
        timeout: int = 500,
        retries: int = 3,
    ) -> list[int]:
        """Send a raw message to an ECU and receive the response.

        Args:
            app_id: Target application ID (e.g. ``0x3200``).
            messages: List of integer message words to send.
            timeout: Response timeout in milliseconds.
            retries: Number of retry attempts.

        Returns:
            List of integer response words from the ECU.
        """
        request = pb2.SendMessageRequest(
            app_id=app_id,
            timeout=timeout,
            retries=retries,
            messages=messages,
        )
        reply = self._call(self._stub.SendMessage, request)
        return list(reply.messages)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def get_log_folder(self) -> str:
        """Get the current log output folder path.

        Returns:
            Absolute folder path string.
        """
        reply = self._call(self._stub.GetLogFolder)
        return reply.file_path

    def get_ppo_file_name(self) -> str:
        """Get the PPO (Parameter Preset Override) file name.

        Returns:
            File path string.
        """
        reply = self._call(self._stub.GetPPOFileName)
        return reply.file_path

    # ------------------------------------------------------------------
    # PGV creation
    # ------------------------------------------------------------------

    def create_pgv(
        self,
        location: str,
        *,
        asap2_file_path: str = "",
        hex_file_path: str = "",
        controllers_file_path: str = "",
        errors_file_path: str = "",
        events_file_path: str = "",
        adjustment_file_path: str = "",
        sensors_file_path: str = "",
        injector_file_path: str = "",
        sensor_enable_file_path: str = "",
        live_auto_tune_file_path: str = "",
        comments: str = "",
        notes: str = "",
    ) -> pb2.CreatePGVReply:
        """Create PGV and DTV files from ASAP2/HEX data.

        Args:
            location: Output directory for generated files.
            asap2_file_path: Path to the ASAP2 (.a2l) file.
            hex_file_path: Path to the HEX (.hex) file.
            controllers_file_path: Path to the controllers definition file.
            errors_file_path: Path to the errors definition file.
            events_file_path: Path to the events definition file.
            adjustment_file_path: Path to the adjustment file.
            sensors_file_path: Path to the sensors file.
            injector_file_path: Path to the injector file.
            sensor_enable_file_path: Path to the sensor-enable file.
            live_auto_tune_file_path: Path to the live auto-tune file.
            comments: Comments to embed in the PGV.
            notes: Notes to embed in the PGV.

        Returns:
            ``CreatePGVReply`` with ``pgv_file_path`` and ``dtv_file_path``.
        """
        request = pb2.CreatePGVRequest(
            location=location,
            asap2_file_path=asap2_file_path,
            hex_file_path=hex_file_path,
            controllers_file_path=controllers_file_path,
            errors_file_path=errors_file_path,
            events_file_path=events_file_path,
            adjustment_file_path=adjustment_file_path,
            sensors_file_path=sensors_file_path,
            injector_file_path=injector_file_path,
            sensor_enable_file_path=sensor_enable_file_path,
            live_auto_tune_file_path=live_auto_tune_file_path,
            comments=comments,
            notes=notes,
        )
        return self._call(self._stub.CreatePGV, request)

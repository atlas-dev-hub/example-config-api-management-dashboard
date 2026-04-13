"""ProjectService — wrapper for the SystemMonitorProject gRPC service.

Provides Pythonic access to the 85 Project-level RPCs, grouped as:

- **Project lifecycle**: open, close, create, save, import, export
- **Data version (DTV)**: version info, comments, notes, save, backup
- **Application management**: list apps, add/remove, active app, PGV/DTV info
- **File operations**: generic file open/save/new, file details
- **CAN configuration**: slot management, buffer/message import/export
- **Logging configuration**: slot management
- **Matlab**: import/export in various modes
- **PUL & Parameter sets**: generate PUL files, parameter unlock lists
- **Enhanced row**: register/clear/activate enhanced-row parameters
- **Events & errors**: list, details, dump, clear, delete
- **Reprogram & data transfer**: reprogram ECU, download/upload data
- **Misc**: compare apps, hex export, sensor serial, parameter existence
"""

from __future__ import annotations

from google.protobuf.empty_pb2 import Empty

from sm_config_api.generated import system_monitor_common_pb2 as common_pb2
from sm_config_api.generated import system_monitor_project_pb2 as pb2
from sm_config_api.generated.system_monitor_project_pb2_grpc import SystemMonitorProjectStub
from sm_config_api.services.base import BaseService


class ProjectService(BaseService):
    """Wrapper for the ``SystemMonitorProject`` gRPC service (85 RPCs)."""

    _stub_class = SystemMonitorProjectStub

    # ==================================================================
    # Project lifecycle
    # ==================================================================

    def project_open(self, file_path: str) -> None:
        """Open a project file (.prj).

        Args:
            file_path: Absolute path to the project file.
        """
        self._call(self._stub.ProjectOpen, common_pb2.FileRequest(file_path=file_path))

    def project_close(self, action: int = 0) -> None:
        """Close the current project.

        Args:
            action: Close action (0 = default).
        """
        self._call(self._stub.ProjectClose, pb2.ProjectCloseRequest(action=action))

    def project_create(
        self,
        project_path: str,
        *,
        app_paths: list[str] | None = None,
        desktop_path: str = "",
        virtuals_path: str = "",
        can_path: str = "",
        logging_config_path: str = "",
    ) -> None:
        """Create a new project.

        Args:
            project_path: Folder path for the new project.
            app_paths: List of application DTV file paths to include.
            desktop_path: Desktop file path.
            virtuals_path: Virtuals file path.
            can_path: CAN configuration file path.
            logging_config_path: Logging configuration file path.
        """
        request = pb2.ProjectCreateRequest(
            project_path=project_path,
            app_paths=app_paths or [],
            desktop_path=desktop_path,
            virtuals_path=virtuals_path,
            can_path=can_path,
            logging_config_path=logging_config_path,
        )
        self._call(self._stub.ProjectCreate, request)

    def project_save(self, save_all: bool = False) -> None:
        """Save the current project.

        Args:
            save_all: If ``True``, save all applications.
        """
        self._call(self._stub.ProjectSave, pb2.ProjectSaveRequest(save_all=save_all))

    def project_save_as(
        self,
        project_name: str,
        *,
        save_all: bool = True,
        comments: str = "",
        notes: str = "",
    ) -> None:
        """Save the project under a new name.

        Args:
            project_name: New project name.
            save_all: Save all applications.
            comments: Comments to embed.
            notes: Notes to embed.
        """
        request = pb2.ProjectSaveAsRequest(
            project_name=project_name,
            save_all=save_all,
            comments=comments,
            notes=notes,
        )
        self._call(self._stub.ProjectSaveAs, request)

    def project_import(self, project_path: str, base: str = "") -> None:
        """Import a project.

        Args:
            project_path: Path to the project to import.
            base: Base path for resolution.
        """
        request = pb2.ProjectImportRequest(project_path=project_path, base=base)
        self._call(self._stub.ProjectImport, request)

    def project_export(self, save_modified: bool = True) -> None:
        """Export the current project.

        Args:
            save_modified: Save modified data before exporting.
        """
        self._call(self._stub.ProjectExport, pb2.ProjectExportRequest(save_modified=save_modified))

    # ==================================================================
    # Version info
    # ==================================================================

    def get_version_number(self) -> pb2.GetVersionNumberReply:
        """Get the System Monitor version number.

        Returns:
            ``GetVersionNumberReply`` with ``major_version``, ``minor_version``,
            ``build_version``.
        """
        return self._call(self._stub.GetVersionNumber)

    def get_build_number(self) -> int:
        """Get the build number.

        Returns:
            The build number integer.
        """
        reply = self._call(self._stub.GetBuildNumber)
        return reply.build_number

    # ==================================================================
    # Data version (DTV)
    # ==================================================================

    def get_pgv_version(self, app_id: int) -> str:
        """Get the PGV version string for an application."""
        reply = self._call(self._stub.GetPGVVersion, common_pb2.AppRequest(app_id=app_id))
        return reply.text

    def get_pgv_id(self, app_id: int) -> int:
        """Get the PGV ID for an application."""
        reply = self._call(self._stub.GetPGVID, common_pb2.AppRequest(app_id=app_id))
        return reply.pgv_id

    def get_dtv_version(self, app_id: int) -> str:
        """Get the DTV version string for an application."""
        reply = self._call(self._stub.GetDTVVersion, common_pb2.AppRequest(app_id=app_id))
        return reply.text

    def get_ecu_dtv_version(self, app_id: int) -> str:
        """Get the ECU's DTV version for an application."""
        reply = self._call(self._stub.GetEcuDTVVersion, common_pb2.AppRequest(app_id=app_id))
        return reply.text

    def get_next_dtv_version(self, app_id: int) -> str:
        """Get the next available DTV version for an application."""
        reply = self._call(self._stub.GetNextDTVVersion, common_pb2.AppRequest(app_id=app_id))
        return reply.text

    def get_dtv_modified(self, app_id: int) -> bool:
        """Check if the DTV has been modified.

        Returns:
            ``True`` if the data version has unsaved changes.
        """
        reply = self._call(self._stub.GetDTVModified, common_pb2.AppRequest(app_id=app_id))
        return reply.modified

    def get_dtv_saved_on(self, app_id: int) -> str:
        """Get the date/time when the DTV was last saved.

        Returns:
            Date string.
        """
        reply = self._call(self._stub.GetDTVSavedOn, common_pb2.AppRequest(app_id=app_id))
        return reply.saved_on

    def get_dtv_notes(self, app_id: int) -> str:
        """Get the DTV notes."""
        reply = self._call(self._stub.GetDTVNotes, common_pb2.AppRequest(app_id=app_id))
        return reply.text

    def set_dtv_notes(self, app_id: int, text: str) -> None:
        """Set the DTV notes."""
        self._call(self._stub.SetDTVNotes, pb2.DetailsRequest(app_id=app_id, text=text))

    def clear_dtv_notes(self, app_id: int) -> None:
        """Clear the DTV notes."""
        self._call(self._stub.ClearDTVNotes, common_pb2.AppRequest(app_id=app_id))

    def get_dtv_comment(self, app_id: int) -> str:
        """Get the DTV comment."""
        reply = self._call(self._stub.GetDTVComment, common_pb2.AppRequest(app_id=app_id))
        return reply.text

    def set_dtv_comment(self, app_id: int, text: str) -> None:
        """Set the DTV comment."""
        self._call(self._stub.SetDTVComment, pb2.DetailsRequest(app_id=app_id, text=text))

    def enable_dtv_backup(self, enable: bool) -> None:
        """Enable or disable DTV backup."""
        self._call(self._stub.EnableDTVBackup, pb2.EnableRequest(enable=enable))

    def dtv_open(self, file_path: str) -> None:
        """Open a DTV file."""
        self._call(self._stub.DTVOpen, common_pb2.FileRequest(file_path=file_path))

    def dtv_save(
        self, app_id: int, save_path: str, *, comment: str = "", notes: str = "",
    ) -> None:
        """Save the DTV to a specific path."""
        request = pb2.DTVSaveRequest(
            app_id=app_id, save_path=save_path, comment=comment, notes=notes,
        )
        self._call(self._stub.DTVSave, request)

    def dtv_save_copy(
        self,
        app_id: int,
        save_path: str,
        *,
        comment: str = "",
        notes: str = "",
        consortium: str = "",
    ) -> None:
        """Save a copy of the DTV."""
        request = pb2.DTVSaveCopyRequest(
            app_id=app_id, save_path=save_path,
            comment=comment, notes=notes, consortium=consortium,
        )
        self._call(self._stub.DTVSaveCopy, request)

    def dtv_save_increment(
        self, app_id: int, *, comment: str = "", notes: str = "",
    ) -> None:
        """Save and auto-increment the DTV version."""
        request = pb2.DTVSaveIncrementRequest(
            app_id=app_id, comment=comment, notes=notes,
        )
        self._call(self._stub.DTVSaveIncrement, request)

    # ==================================================================
    # Application management
    # ==================================================================

    def get_app_details(self) -> list[pb2.Application]:
        """Get details for all loaded applications.

        Returns:
            List of ``Application`` objects with ``app_id`` and ``app_name``.
        """
        reply = self._call(self._stub.GetAppDetails)
        return list(reply.apps)

    def get_active_apps(self) -> list[int]:
        """Get the list of active application IDs.

        Returns:
            List of app_id integers.
        """
        reply = self._call(self._stub.GetActiveApps)
        return list(reply.app_ids)

    def set_active_apps(self, app_ids: list[int]) -> None:
        """Set the active applications.

        Args:
            app_ids: List of application IDs to activate.
        """
        self._call(self._stub.SetActiveApps, pb2.MultiAppRequest(app_ids=app_ids))

    def add_app(self, file_path: str) -> None:
        """Add an application from a DTV file.

        Args:
            file_path: Path to the DTV file.
        """
        self._call(self._stub.AddApp, common_pb2.FileRequest(file_path=file_path))

    def remove_app(self, app_id: int) -> None:
        """Remove an application.

        Args:
            app_id: Application ID to remove.
        """
        self._call(self._stub.RemoveApp, common_pb2.AppRequest(app_id=app_id))

    def compare_app(
        self, app_id: int, dtv1_path: str, dtv2_path: str,
    ) -> pb2.CompareAppReply:
        """Compare two DTV files for an application.

        Args:
            app_id: Application ID.
            dtv1_path: Path to the first DTV file.
            dtv2_path: Path to the second DTV file.

        Returns:
            ``CompareAppReply`` with a list of differing ``parameters``.
        """
        request = pb2.CompareAppRequest(
            app_id=app_id, dtv1_path=dtv1_path, dtv2_path=dtv2_path,
        )
        return self._call(self._stub.CompareApp, request)

    # ==================================================================
    # Reprogram & data transfer
    # ==================================================================

    def reprogram(self, app_ids: list[int], *, force: bool = False) -> None:
        """Reprogram ECU(s) with the current data.

        Args:
            app_ids: List of application IDs to reprogram.
            force: Force reprogram even if data appears up-to-date.
        """
        request = pb2.ReprogramRequest(app_ids=app_ids, force=force)
        self._call(self._stub.Reprogram, request)

    def download_data_changes(self, app_id: int) -> None:
        """Download data changes to the ECU."""
        self._call(self._stub.DownloadDataChanges, common_pb2.AppRequest(app_id=app_id))

    def edit_buffer_synced(self, app_id: int) -> bool:
        """Check if the edit buffer is synchronised with the ECU.

        Returns:
            ``True`` if synced.
        """
        reply = self._call(self._stub.EditBufferSynced, common_pb2.AppRequest(app_id=app_id))
        return reply.synced

    def upload_data_version(self, app_id: int) -> None:
        """Upload the data version from the ECU."""
        self._call(self._stub.UploadDataVersion, common_pb2.AppRequest(app_id=app_id))

    # ==================================================================
    # PUL & parameter sets
    # ==================================================================

    def get_app_pul_file(self, app_id: int) -> str:
        """Get the PUL file path for an application.

        Returns:
            File path string.
        """
        reply = self._call(self._stub.GetAppPULFile, common_pb2.AppRequest(app_id=app_id))
        return reply.file_path

    def set_app_pul_file(self, app_id: int, file_path: str) -> None:
        """Set the PUL file for an application."""
        request = pb2.AppFileRequest(app_id=app_id, file_path=file_path)
        self._call(self._stub.SetAppPULFile, request)

    def generate_param_set(self, parameter_ids: list[str], file_path: str) -> None:
        """Generate a parameter set file.

        Args:
            parameter_ids: List of parameter identifier strings.
            file_path: Output file path.
        """
        request = common_pb2.ParametersFileRequest(
            parameter_ids=parameter_ids, file_path=file_path,
        )
        self._call(self._stub.GenerateParamSet, request)

    def generate_pul_file(
        self, app_id: int, parameter_ids: list[str], file_path: str,
    ) -> None:
        """Generate a PUL file from a list of parameters.

        Args:
            app_id: Application ID.
            parameter_ids: Parameter identifiers to include.
            file_path: Output file path.
        """
        request = common_pb2.AppParametersFileRequest(
            app_id=app_id, parameter_ids=parameter_ids, file_path=file_path,
        )
        self._call(self._stub.GeneratePULFile, request)

    def generate_pul_file_from_param_set(self, app_id: int, file_path: str) -> str:
        """Generate a PUL file from an existing parameter set file.

        Returns:
            The generated PUL file path.
        """
        request = pb2.AppFileRequest(app_id=app_id, file_path=file_path)
        reply = self._call(self._stub.GeneratePULFileFromParamSet, request)
        return reply.file_path

    def add_parameters_to_unlock_list(
        self, app_id: int, parameter_ids: list[str], file_path: str,
    ) -> str:
        """Add parameters to the unlock list.

        Returns:
            The updated unlock list file path.
        """
        request = common_pb2.AppParametersFileRequest(
            app_id=app_id, parameter_ids=parameter_ids, file_path=file_path,
        )
        reply = self._call(self._stub.AddParametersToUnlockList, request)
        return reply.file_path

    def remove_parameters_from_unlock_list(
        self, app_id: int, parameter_ids: list[str], file_path: str,
    ) -> str:
        """Remove parameters from the unlock list.

        Returns:
            The updated unlock list file path.
        """
        request = common_pb2.AppParametersFileRequest(
            app_id=app_id, parameter_ids=parameter_ids, file_path=file_path,
        )
        reply = self._call(self._stub.RemoveParametersFromUnlockList, request)
        return reply.file_path

    # ==================================================================
    # Parameter lookup across apps
    # ==================================================================

    def get_apps_holding_param(self, parameter_id: str) -> list[int]:
        """Get app IDs that contain a given parameter.

        Returns:
            List of application IDs.
        """
        request = pb2.ParameterIdRequest(parameter_id=parameter_id)
        reply = self._call(self._stub.GetAppsHoldingParam, request)
        return list(reply.app_ids)

    def get_apps_holding_measurement_param(self, parameter_id: str) -> list[int]:
        """Get app IDs that hold a measurement parameter.

        Returns:
            List of application IDs.
        """
        request = pb2.ParameterIdRequest(parameter_id=parameter_id)
        reply = self._call(self._stub.GetAppsHoldingMeasurementParam, request)
        return list(reply.app_ids)

    def get_apps_holding_control_param(self, parameter_id: str) -> list[int]:
        """Get app IDs that hold a control parameter.

        Returns:
            List of application IDs.
        """
        request = pb2.ParameterIdRequest(parameter_id=parameter_id)
        reply = self._call(self._stub.GetAppsHoldingControlParam, request)
        return list(reply.app_ids)

    def parameter_exists(self, app_id: int, parameter_id: str, data_type: int = 0) -> bool:
        """Check whether a parameter exists in an application.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier string.
            data_type: Parameter type filter (0 = any).

        Returns:
            ``True`` if the parameter exists.
        """
        request = pb2.ExistsRequest(
            app_id=app_id, parameter_id=parameter_id, data_type=data_type,
        )
        reply = self._call(self._stub.ParameterExists, request)
        return reply.exists

    # ==================================================================
    # Sensor
    # ==================================================================

    def change_sensor_serial_number(
        self, app_id: int, sensor: str, serial_number: int,
    ) -> None:
        """Change the serial number of a sensor.

        Args:
            app_id: Application ID.
            sensor: Sensor identifier string.
            serial_number: New serial number.
        """
        request = pb2.SensorRequest(
            app_id=app_id, sensor=sensor, serial_number=serial_number,
        )
        self._call(self._stub.ChangeSensorSerialNumber, request)

    # ==================================================================
    # Generic file operations
    # ==================================================================

    def file_open(
        self, file_type: int, file_path: str, *, slot: int = 0, activate: bool = True,
    ) -> None:
        """Open a file by type.

        Args:
            file_type: :class:`~sm_config_api.enums.FileType` value.
            file_path: Path to the file.
            slot: Slot number (for multi-slot file types).
            activate: Whether to activate the file after opening.
        """
        request = pb2.FileOpenRequest(
            file_type=file_type, file_path=file_path, slot=slot, activate=activate,
        )
        self._call(self._stub.FileOpen, request)

    def file_save(
        self,
        file_type: int,
        file_path: str,
        *,
        comment: str = "",
        notes: str = "",
        consortium: str = "",
        save_copy_as: bool = False,
    ) -> None:
        """Save a file by type.

        Args:
            file_type: :class:`~sm_config_api.enums.FileType` value.
            file_path: Output path.
            comment: Embedded comment.
            notes: Embedded notes.
            consortium: Consortium string.
            save_copy_as: Save as a copy.
        """
        request = pb2.FileSaveRequest(
            file_type=file_type, file_path=file_path,
            comment=comment, notes=notes,
            consortium=consortium, save_copy_as=save_copy_as,
        )
        self._call(self._stub.FileSave, request)

    def file_new(
        self,
        file_type: int,
        file_path: str,
        *,
        save_existing: bool = True,
        overwrite: bool = False,
    ) -> None:
        """Create a new file by type.

        Args:
            file_type: :class:`~sm_config_api.enums.FileType` value.
            file_path: Path for the new file.
            save_existing: Save the existing file before creating.
            overwrite: Overwrite if file already exists.
        """
        request = pb2.FileNewRequest(
            file_type=file_type, file_path=file_path,
            save_existing=save_existing, overwrite=overwrite,
        )
        self._call(self._stub.FileNew, request)

    def get_file_name(self, file_type: int, slot: int = 0) -> str:
        """Get the current file name for a given type and slot.

        Returns:
            File path string.
        """
        request = pb2.FileNameRequest(file_type=file_type, slot=slot)
        reply = self._call(self._stub.GetFileName, request)
        return reply.file_path

    def get_file_details(self, file_path: str) -> pb2.FileDetailsReply:
        """Get metadata for a file.

        Returns:
            ``FileDetailsReply`` with ``saved_by``, ``saved_on``, ``comment``,
            ``notes``, ``build``, ``consortium``, ``owner``, ``rda``.
        """
        return self._call(
            self._stub.GetFileDetails, common_pb2.FileRequest(file_path=file_path),
        )

    def create_ffc_from_pgv(self, file_path: str) -> None:
        """Create an FFC file from a PGV file."""
        self._call(self._stub.CreateFFCFromPGV, common_pb2.FileRequest(file_path=file_path))

    def export_to_hex_file(self, app_id: int) -> None:
        """Export application data to a HEX file."""
        self._call(self._stub.ExportToHexFile, common_pb2.AppRequest(app_id=app_id))

    # ==================================================================
    # CAN configuration
    # ==================================================================

    def get_active_can_config(self, slot: int) -> bool:
        """Check if a CAN configuration slot is active.

        Returns:
            ``True`` if the slot is active.
        """
        reply = self._call(self._stub.GetActiveCANConfig, pb2.SlotRequest(slot=slot))
        return reply.active

    def set_active_can_config(self, slot: int, active: bool) -> None:
        """Activate or deactivate a CAN configuration slot."""
        request = pb2.SlotActiveRequest(slot=slot, active=active)
        self._call(self._stub.SetActiveCANConfig, request)

    def get_fia_can_config(self, slot: int) -> bool:
        """Check if a FIA CAN configuration slot is active.

        Returns:
            ``True`` if the slot is active.
        """
        reply = self._call(self._stub.GetFIACANConfig, pb2.SlotRequest(slot=slot))
        return reply.active

    def set_fia_can_config(self, slot: int, active: bool) -> None:
        """Activate or deactivate a FIA CAN configuration slot."""
        request = pb2.SlotActiveRequest(slot=slot, active=active)
        self._call(self._stub.SetFIACANConfig, request)

    def can_buffers_export(self, index: int, file_path: str) -> None:
        """Export CAN buffers to a file.

        Args:
            index: CAN bus index (typically 1-based).
            file_path: Output file path.
        """
        request = pb2.CANRequest(index=index, file_path=file_path)
        self._call(self._stub.CANBuffersExport, request)

    def can_buffers_import(self, index: int, file_path: str) -> None:
        """Import CAN buffers from a file."""
        request = pb2.CANRequest(index=index, file_path=file_path)
        self._call(self._stub.CANBuffersImport, request)

    def can_messages_export(self, index: int, file_path: str) -> None:
        """Export CAN messages to a file."""
        request = pb2.CANRequest(index=index, file_path=file_path)
        self._call(self._stub.CANMessagesExport, request)

    def can_messages_import(
        self, index: int, file_path: str, *, merge: bool = False,
    ) -> None:
        """Import CAN messages from a file.

        Args:
            index: CAN bus index.
            file_path: Input file path.
            merge: Merge with existing messages instead of replacing.
        """
        request = pb2.CANMergeRequest(index=index, file_path=file_path, merge=merge)
        self._call(self._stub.CANMessagesImport, request)

    def can_config_unload(self, slot: int) -> None:
        """Unload a CAN configuration slot."""
        self._call(self._stub.CANConfigUnload, pb2.SlotRequest(slot=slot))

    # ==================================================================
    # Logging configuration
    # ==================================================================

    def get_active_logging_config(self, slot: int) -> bool:
        """Check if a logging configuration slot is active.

        Returns:
            ``True`` if the slot is active.
        """
        reply = self._call(
            self._stub.GetActiveLoggingConfig, pb2.SlotRequest(slot=slot),
        )
        return reply.active

    def set_active_logging_config(self, slot: int, active: bool) -> None:
        """Activate or deactivate a logging configuration slot."""
        request = pb2.SlotActiveRequest(slot=slot, active=active)
        self._call(self._stub.SetActiveLoggingConfig, request)

    def logging_config_unload(self, slot: int) -> None:
        """Unload a logging configuration slot."""
        self._call(self._stub.LoggingConfigUnload, pb2.SlotRequest(slot=slot))

    # ==================================================================
    # Matlab
    # ==================================================================

    def matlab_import(self, file_path: str) -> None:
        """Import parameters from a Matlab .m file."""
        self._call(self._stub.MatlabImport, common_pb2.FileRequest(file_path=file_path))

    def matlab_export(
        self,
        app_id: int,
        export_path: str,
        *,
        data_only: bool = True,
        data_types: list[int] | None = None,
    ) -> None:
        """Export parameters to a Matlab .m file.

        Args:
            app_id: Application ID.
            export_path: Output .m file path.
            data_only: Export data values only (no metadata).
            data_types: List of :class:`~sm_config_api.enums.ParameterType`
                values to include. Empty list exports all types.
        """
        request = pb2.MatlabRequest(
            app_id=app_id, export_path=export_path,
            data_only=data_only, data_types=data_types or [],
        )
        self._call(self._stub.MatlabExport, request)

    def matlab_export_dtv(
        self,
        dtv_path: str,
        export_path: str,
        *,
        data_only: bool = True,
        data_types: list[int] | None = None,
    ) -> None:
        """Export parameters from a DTV file to Matlab .m format.

        Args:
            dtv_path: Path to the DTV file.
            export_path: Output .m file path.
            data_only: Export data values only.
            data_types: Parameter types to include.
        """
        request = pb2.MatlabDTVRequest(
            dtv_path=dtv_path, export_path=export_path,
            data_only=data_only, data_types=data_types or [],
        )
        self._call(self._stub.MatlabExportDTV, request)

    def matlab_export_selected(
        self,
        app_id: int,
        export_path: str,
        parameter_ids: list[str],
        *,
        data_only: bool = True,
    ) -> None:
        """Export selected parameters to Matlab .m format.

        Args:
            app_id: Application ID.
            export_path: Output .m file path.
            parameter_ids: List of parameter identifiers to export.
            data_only: Export data values only.
        """
        request = pb2.MatlabSelectedRequest(
            app_id=app_id, export_path=export_path,
            data_only=data_only, parameter_ids=parameter_ids,
        )
        self._call(self._stub.MatlabExportSelected, request)

    # ==================================================================
    # Enhanced row parameters
    # ==================================================================

    def register_enhanced_row_parameters(
        self, app_id: int, parameter_ids: list[str],
    ) -> None:
        """Register parameters for enhanced-row data capture.

        Args:
            app_id: Application ID.
            parameter_ids: Parameter identifiers to register.
        """
        request = common_pb2.AppParametersRequest(
            app_id=app_id, parameter_ids=parameter_ids,
        )
        self._call(self._stub.RegisterEnhancedRowParameters, request)

    def clear_enhanced_row_parameters(self, app_id: int) -> None:
        """Clear all registered enhanced-row parameters for an application."""
        self._call(
            self._stub.ClearEnhancedRowParameters, common_pb2.AppRequest(app_id=app_id),
        )

    def register_can_enhanced_row_parameters(self, parameter_ids: list[str]) -> None:
        """Register CAN parameters for enhanced-row capture."""
        request = common_pb2.ParametersRequest(parameter_ids=parameter_ids)
        self._call(self._stub.RegisterCANEnhancedRowParameters, request)

    def register_virtual_enhanced_row_parameters(self, parameter_ids: list[str]) -> None:
        """Register virtual parameters for enhanced-row capture."""
        request = common_pb2.ParametersRequest(parameter_ids=parameter_ids)
        self._call(self._stub.RegisterVirtualEnhancedRowParameters, request)

    def activate_enhanced_row_parameters(self) -> None:
        """Activate all registered enhanced-row parameters."""
        self._call(self._stub.ActivateEnhancedRowParameters)

    # ==================================================================
    # Events & errors
    # ==================================================================

    def get_events(self, app_id: int) -> list[pb2.Event]:
        """Get the list of events for an application.

        Returns:
            List of ``Event`` objects with ``id``, ``name``, ``priority``.
        """
        reply = self._call(self._stub.GetEvents, common_pb2.AppRequest(app_id=app_id))
        return list(reply.events)

    def get_event_details(self, app_id: int, event_id: int) -> pb2.EventReply:
        """Get detailed information about a specific event.

        Returns:
            ``EventReply`` with ``event_id``, ``description``,
            ``conversion_id1/2/3``, ``priority``.
        """
        request = pb2.EventRequest(app_id=app_id, event_id=event_id)
        return self._call(self._stub.GetEventDetails, request)

    def get_error_definitions(self, app_id: int) -> list[pb2.ErrorDefinition]:
        """Get error definitions for an application.

        Returns:
            List of ``ErrorDefinition`` objects with ``id``, ``name``,
            ``description``, ``group``, ``bit_number``, ``current``, ``logged``.
        """
        reply = self._call(
            self._stub.GetErrorDefinitions, common_pb2.AppRequest(app_id=app_id),
        )
        return list(reply.error_definitions)

    def get_errors(self) -> list[pb2.ErrorInstance]:
        """Get all current error instances.

        Returns:
            List of ``ErrorInstance`` objects with ``name``, ``description``,
            ``status``.
        """
        reply = self._call(self._stub.GetErrors)
        return list(reply.error_instances)

    def delete_errors(self) -> None:
        """Delete all error records.

        .. warning:: This permanently removes all error data.
        """
        self._call(self._stub.DeleteErrors)

    def clear_events(self) -> None:
        """Clear all events.

        .. warning:: This removes all event records.
        """
        self._call(self._stub.ClearEvents)

    def dump_events(self, file_path: str) -> None:
        """Dump events to a file.

        Args:
            file_path: Output file path.
        """
        self._call(self._stub.DumpEvents, common_pb2.FileRequest(file_path=file_path))

    def dump_errors(self, file_path: str) -> None:
        """Dump errors to a file.

        Args:
            file_path: Output file path.
        """
        self._call(self._stub.DumpErrors, common_pb2.FileRequest(file_path=file_path))

    def dump_row_data(self, file_path: str) -> None:
        """Dump row data to a file.

        Args:
            file_path: Output file path.
        """
        self._call(self._stub.DumpRowData, common_pb2.FileRequest(file_path=file_path))

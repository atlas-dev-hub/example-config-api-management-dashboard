"""VirtualService — wrapper for the SystemMonitorVirtual gRPC service.

Provides Pythonic access to the 15 Virtual-level RPCs, grouped as:

- **Parameter CRUD**: set, get properties, remove, remove all
- **Conversion management**: remove conversions, remove all conversions
- **Group management**: list groups, get group, get parameters in group,
  add/remove group, remove all parameters from group
- **Import/Export**: export and import virtual parameters
- **Data type**: set parameter data type
"""

from __future__ import annotations

from typing import Sequence

from google.protobuf.empty_pb2 import Empty

from sm_config_api.generated import system_monitor_common_pb2 as common_pb2
from sm_config_api.generated import system_monitor_virtual_pb2 as pb2
from sm_config_api.generated.system_monitor_virtual_pb2_grpc import SystemMonitorVirtualStub
from sm_config_api.services.base import BaseService


class VirtualService(BaseService):
    """Wrapper for the ``SystemMonitorVirtual`` gRPC service (15 RPCs)."""

    _stub_class = SystemMonitorVirtualStub

    # ==================================================================
    # Parameter CRUD
    # ==================================================================

    def set_virtual_parameter(
        self,
        id: str,
        name: str,
        *,
        description: str = "",
        min_display: float = 0.0,
        max_display: float = 0.0,
        min_logging_rate: int = 0,
        scaling_factor: int = 0,
        is_min_not_def: bool = False,
        expression: str = "",
        conversion_id: str = "",
        overwrite: bool = False,
        units: str = "",
        format_override: str = "",
        group: str = "",
        data_type: int = 0,
        lower_warning: float = 0.0,
        upper_warning: float = 0.0,
    ) -> None:
        """Create or update a virtual parameter.

        Args:
            id: Unique parameter identifier.
            name: Display name.
            description: Optional description text.
            min_display: Minimum display value.
            max_display: Maximum display value.
            min_logging_rate: Minimum logging rate.
            scaling_factor: Scaling factor.
            is_min_not_def: Whether the minimum is user-defined.
            expression: Virtual parameter expression.
            conversion_id: Associated conversion identifier.
            overwrite: If ``True``, overwrite an existing parameter.
            units: Engineering units string.
            format_override: Display format override.
            group: Group path to assign the parameter to.
            data_type: Parameter data type enum value.
            lower_warning: Lower warning threshold.
            upper_warning: Upper warning threshold.
        """
        request = pb2.VirtualParameterRequest(
            id=id,
            name=name,
            description=description,
            min_display=min_display,
            max_display=max_display,
            Min_logging_rate=min_logging_rate,
            scaling_factor=scaling_factor,
            is_min_not_def=is_min_not_def,
            expression=expression,
            conversion_id=conversion_id,
            overwrite=overwrite,
            units=units,
            format_override=format_override,
            group=group,
            data_type=data_type,
            lower_warning=lower_warning,
            upper_warning=upper_warning,
        )
        self._call(self._stub.SetVirtualParameter, request)

    def get_virtual_parameter_properties(
        self,
        parameter_ids: Sequence[str],
    ) -> list[pb2.VirtualParameterProperties]:
        """Get properties for one or more virtual parameters.

        Args:
            parameter_ids: Sequence of parameter identifiers to query.

        Returns:
            List of ``VirtualParameterProperties`` objects.
        """
        request = common_pb2.ParametersRequest(parameter_ids=parameter_ids)
        reply = self._call(self._stub.GetVirtualParameterProperties, request)
        return list(reply.parameters)

    def remove_virtual_parameters(
        self,
        ids: Sequence[str],
    ) -> list[pb2.VirtualParameter]:
        """Remove one or more virtual parameters by ID.

        Args:
            ids: Sequence of parameter identifiers to remove.

        Returns:
            List of ``VirtualParameter`` results with per-ID return codes.
        """
        request = pb2.VirtualsRequest(ids=ids)
        reply = self._call(self._stub.RemoveVirtualParameters, request)
        return list(reply.ids)

    def remove_all_virtual_parameters(self) -> None:
        """Remove all virtual parameters."""
        self._call(self._stub.RemoveAllVirtualParameters, Empty())

    # ==================================================================
    # Conversion management
    # ==================================================================

    def remove_virtual_conversions(
        self,
        ids: Sequence[str],
    ) -> list[pb2.VirtualParameter]:
        """Remove one or more virtual conversions by ID.

        Args:
            ids: Sequence of conversion identifiers to remove.

        Returns:
            List of ``VirtualParameter`` results with per-ID return codes.
        """
        request = pb2.VirtualsRequest(ids=ids)
        reply = self._call(self._stub.RemoveVirtualConversions, request)
        return list(reply.ids)

    def remove_all_virtual_conversions(self) -> None:
        """Remove all virtual conversions."""
        self._call(self._stub.RemoveAllVirtualConversions, Empty())

    # ==================================================================
    # Groups
    # ==================================================================

    def get_virtual_parameter_groups(self) -> list[str]:
        """Get the list of all virtual parameter group names.

        Returns:
            List of group name strings.
        """
        reply = self._call(self._stub.GetVirtualParameterGroups, Empty())
        return list(reply.ids)

    def get_virtual_parameter_group(
        self,
        group: str,
    ) -> pb2.VirtualGroupReply:
        """Get details of a virtual parameter group.

        Args:
            group: Group name to query.

        Returns:
            ``VirtualGroupReply`` with ``name``, ``description``,
            ``read_only``, and ``return_code``.
        """
        request = pb2.VirtualGroupRequest(group=group)
        return self._call(self._stub.GetVirtualParameterGroup, request)

    def get_virtual_parameters_in_group(
        self,
        group: str,
    ) -> list[str]:
        """Get all virtual parameter IDs belonging to a group.

        Args:
            group: Group name to query.

        Returns:
            List of parameter identifier strings.
        """
        request = pb2.VirtualGroupRequest(group=group)
        reply = self._call(self._stub.GetVirtualParametersInGroup, request)
        return list(reply.ids)

    def add_virtual_parameter_group(
        self,
        group_path: str,
        name: str,
        *,
        description: str = "",
        read_only: bool = False,
    ) -> None:
        """Add a new virtual parameter group.

        Args:
            group_path: Path for the new group.
            name: Display name of the group.
            description: Optional group description.
            read_only: Whether the group should be read-only.
        """
        request = pb2.AddGroupRequest(
            group_path=group_path,
            name=name,
            description=description,
            read_only=read_only,
        )
        self._call(self._stub.AddVirtualParameterGroup, request)

    def remove_virtual_parameter_group(self, group: str) -> None:
        """Remove a virtual parameter group.

        Args:
            group: Group name to remove.
        """
        request = pb2.VirtualGroupRequest(group=group)
        self._call(self._stub.RemoveVirtualParameterGroup, request)

    def remove_all_virtual_parameters_from_group(self, group: str) -> None:
        """Remove all virtual parameters from a group without deleting the group.

        Args:
            group: Group name to clear.
        """
        request = pb2.VirtualGroupRequest(group=group)
        self._call(self._stub.RemoveAllVirtualParametersFromGroup, request)

    # ==================================================================
    # Import / Export
    # ==================================================================

    def virtual_parameters_export(
        self,
        file_path: str,
        *,
        group: str = "",
    ) -> None:
        """Export virtual parameters to a file.

        Args:
            file_path: Destination file path.
            group: Optional group to limit the export to.
        """
        request = pb2.VirtualExportRequest(file_path=file_path, group=group)
        self._call(self._stub.VirtualParametersExport, request)

    def virtual_parameters_import(self, file_path: str) -> None:
        """Import virtual parameters from a file.

        Args:
            file_path: Path to the file to import.
        """
        request = common_pb2.FileRequest(file_path=file_path)
        self._call(self._stub.VirtualParametersImport, request)

    # ==================================================================
    # Data type
    # ==================================================================

    def set_virtual_parameter_data_type(
        self,
        id: str,
        data_type: int,
    ) -> None:
        """Set the data type of a virtual parameter.

        Args:
            id: Parameter identifier.
            data_type: Data type enum value.
        """
        request = pb2.VirtualParameterDataTypeRequest(Id=id, data_type=data_type)
        self._call(self._stub.SetVirtualParameterDataType, request)

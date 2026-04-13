"""ParameterService — wrapper for the SystemMonitorParameter gRPC service.

Provides Pythonic access to the 60 Parameter-level RPCs, grouped as:

- **Parameter listing & properties**: list parameters, conversions, groups, properties
- **External input**: gain/offset for external input parameters
- **Modified parameters**: list modified parameters
- **Warning limits**: get/set parameter warning limits
- **Utility**: delete min/max, import/export input signals, undo, restore
- **Map/conversion relationships**: axis parameters, conversion use
- **Conversion getters**: rational, table, text, formula conversions
- **Conversion setters**: create/update conversions
- **Value offset**: get/set/zero value offsets
- **Get values**: measurement, scalar, map, axis, array, string, CAN, virtual
- **Get DTV values**: scalar, map, axis, array, string from DTV files
- **Set values**: scalar, map, axis, array, string
"""

from __future__ import annotations

from typing import Sequence

from google.protobuf.empty_pb2 import Empty

from sm_config_api.generated import system_monitor_common_pb2 as common_pb2
from sm_config_api.generated import system_monitor_parameter_pb2 as pb2
from sm_config_api.generated.system_monitor_parameter_pb2_grpc import SystemMonitorParameterStub
from sm_config_api.services.base import BaseService


class ParameterService(BaseService):
    """Wrapper for the ``SystemMonitorParameter`` gRPC service (60 RPCs)."""

    _stub_class = SystemMonitorParameterStub

    # ==================================================================
    # Parameter listing & properties
    # ==================================================================

    def get_parameters(self, app_id: int, data_type: int) -> list[pb2.Parameter]:
        """Get the list of parameters for an application filtered by data type.

        Args:
            app_id: Application ID.
            data_type: Parameter type enum value (e.g. ``ParameterType.scalar``).

        Returns:
            List of ``Parameter`` objects, each with ``id`` and ``name``.
        """
        request = pb2.AppTypeRequest(app_id=app_id, data_type=data_type)
        reply = self._call(self._stub.GetParameters, request)
        return list(reply.parameters)

    def get_conversions(self, app_id: int) -> list[pb2.Conversion]:
        """Get all conversions for an application.

        Args:
            app_id: Application ID.

        Returns:
            List of ``Conversion`` objects, each with ``id`` and ``type``.
        """
        request = common_pb2.AppRequest(app_id=app_id)
        reply = self._call(self._stub.GetConversions, request)
        return list(reply.conversions)

    def get_parameter_and_groups(self, app_id: int) -> list[pb2.ParameterGroup]:
        """Get parameters with their group assignments.

        Args:
            app_id: Application ID.

        Returns:
            List of ``ParameterGroup`` objects, each with ``id`` and ``group``.
        """
        request = common_pb2.AppRequest(app_id=app_id)
        reply = self._call(self._stub.GetParameterAndGroups, request)
        return list(reply.parameters)

    def get_parameter_properties(
        self, app_id: int, data_type: int,
    ) -> list[pb2.ParameterProperties]:
        """Get detailed properties for all parameters of a given type.

        Args:
            app_id: Application ID.
            data_type: Parameter type enum value.

        Returns:
            List of ``ParameterProperties`` with full metadata (name,
            description, type, units, format, conversion, limits, etc.).
        """
        request = pb2.AppTypeRequest(app_id=app_id, data_type=data_type)
        reply = self._call(self._stub.GetParameterProperties, request)
        return list(reply.parameters)

    def get_can_parameter_properties(
        self, parameter_ids: Sequence[str],
    ) -> list[pb2.CANParameterProperties]:
        """Get detailed properties for CAN parameters.

        Args:
            parameter_ids: CAN parameter identifiers.

        Returns:
            List of ``CANParameterProperties`` with CAN-specific metadata
            (bus, message, start bit, gain, offset, etc.).
        """
        request = common_pb2.ParametersRequest(parameter_ids=parameter_ids)
        reply = self._call(self._stub.GetCANParameterProperties, request)
        return list(reply.parameters)

    def get_map_properties(
        self, app_id: int, parameter_id: str,
    ) -> pb2.MapPropertiesReply:
        """Get map properties (axis IDs and point counts) for a map parameter.

        Args:
            app_id: Application ID.
            parameter_id: Map parameter identifier.

        Returns:
            ``MapPropertiesReply`` with ``x_axis_id``, ``y_axis_id``,
            ``x_points``, ``y_points``.
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        return self._call(self._stub.GetMapProperties, request)

    def get_row_details(
        self, app_id: int, parameter_id: str,
    ) -> pb2.RowDetailsReply:
        """Get row details for a parameter.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.

        Returns:
            ``RowDetailsReply`` with ``row_id`` and ``ident_offset``.
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        return self._call(self._stub.GetRowDetails, request)

    def get_parameter_bit_mask(
        self, app_id: int, parameter_id: str,
    ) -> int:
        """Get the bit mask for a parameter.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.

        Returns:
            The bit mask value.
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        reply = self._call(self._stub.GetParameterBitMask, request)
        return reply.mask

    def get_parameter_bit_shift(
        self, app_id: int, parameter_id: str,
    ) -> int:
        """Get the bit shift for a parameter.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.

        Returns:
            The bit shift value.
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        reply = self._call(self._stub.GetParameterBitShift, request)
        return reply.shift

    def get_parameter_address(
        self, app_id: int, parameter_id: str, data_type: int,
    ) -> pb2.AddressReply:
        """Get the memory address and ident for a parameter.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.
            data_type: Parameter type enum value.

        Returns:
            ``AddressReply`` with ``address`` and ``ident``.
        """
        request = pb2.ParameterTypeRequest(
            app_id=app_id, parameter_id=parameter_id, data_type=data_type,
        )
        return self._call(self._stub.GetParameterAddress, request)

    def get_parameter_byte_order(
        self, app_id: int, parameter_id: str,
    ) -> int:
        """Get the byte order for a parameter.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.

        Returns:
            Byte order enum value (``ByteOrder.msb_first`` or ``msb_last``).
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        reply = self._call(self._stub.GetParameterByteOrder, request)
        return reply.byte_order

    def parameter_loggable(
        self, app_id: int, parameter_id: str,
    ) -> bool:
        """Check whether a parameter is loggable.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.

        Returns:
            ``True`` if the parameter is loggable.
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        reply = self._call(self._stub.ParameterLoggable, request)
        return reply.loggable

    # ==================================================================
    # External input
    # ==================================================================

    def get_external_input_gain_offset(
        self, parameter_id: str,
    ) -> pb2.ExternalReply:
        """Get the gain and offset for an external input parameter.

        Args:
            parameter_id: External parameter identifier.

        Returns:
            ``ExternalReply`` with ``parameter_id``, ``gain``, ``offset``.
        """
        request = pb2.ExternalParameterRequest(parameter_id=parameter_id)
        return self._call(self._stub.GetExternalInputGainOffset, request)

    def set_external_input_gain_offset(
        self, parameter_id: str, gain: float, offset: float,
    ) -> None:
        """Set the gain and offset for an external input parameter.

        Args:
            parameter_id: External parameter identifier.
            gain: Gain value.
            offset: Offset value.
        """
        request = pb2.ExternalRequest(
            parameter_id=parameter_id, gain=gain, offset=offset,
        )
        self._call(self._stub.SetExternalInputGainOffset, request)

    # ==================================================================
    # Modified parameters
    # ==================================================================

    def get_modified_parameters(self, app_id: int) -> list[pb2.Parameter]:
        """Get the list of parameters that have been modified.

        Args:
            app_id: Application ID.

        Returns:
            List of ``Parameter`` objects with ``id`` and ``name``.
        """
        request = common_pb2.AppRequest(app_id=app_id)
        reply = self._call(self._stub.GetModifiedParameters, request)
        return list(reply.parameters)

    # ==================================================================
    # Warning limits
    # ==================================================================

    def get_parameter_warning_limits(
        self, app_id: int, parameter_id: str,
    ) -> pb2.WarningLimitsReply:
        """Get warning limits for a parameter.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.

        Returns:
            ``WarningLimitsReply`` with ``low`` and ``high`` limits.
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        return self._call(self._stub.GetParameterWarningLimits, request)

    def set_parameter_warning_limits(
        self, app_id: int, parameter_id: str, low: float, high: float,
    ) -> None:
        """Set warning limits for a parameter.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.
            low: Lower warning limit.
            high: Upper warning limit.
        """
        request = pb2.WarningLimitsRequest(
            app_id=app_id, parameter_id=parameter_id, low=low, high=high,
        )
        self._call(self._stub.SetParameterWarningLimits, request)

    # ==================================================================
    # Utility
    # ==================================================================

    def delete_min_max(self) -> None:
        """Delete all min/max stored values."""
        self._call(self._stub.DeleteMinMax)

    def export_input_signals(self, file_path: str) -> None:
        """Export input signal definitions to a file.

        Args:
            file_path: Destination file path.
        """
        self._call(
            self._stub.ExportInputSignals,
            common_pb2.FileRequest(file_path=file_path),
        )

    def import_input_signals(self, file_path: str) -> None:
        """Import input signal definitions from a file.

        Args:
            file_path: Source file path.
        """
        self._call(
            self._stub.ImportInputSignals,
            common_pb2.FileRequest(file_path=file_path),
        )

    def regenerate_input_signal_parameters(self) -> None:
        """Regenerate input signal parameters from current configuration."""
        self._call(self._stub.RegenerateInputSignalParameters)

    def undo_data_changes(self, buffer_type: int) -> None:
        """Undo data changes in the specified buffer.

        Args:
            buffer_type: Buffer type enum value (e.g.
                ``BufferType.unit_buffer``, ``edit_buffer``,
                ``unit_and_edit_buffer``).
        """
        request = pb2.UndoRequest(buffer_type=buffer_type)
        self._call(self._stub.UndoDataChanges, request)

    def restore_value(self, app_id: int, parameter_id: str) -> None:
        """Restore a parameter to its original value.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        self._call(self._stub.RestoreValue, request)

    # ==================================================================
    # Map / conversion relationships
    # ==================================================================

    def get_axis_parameter_from_map(
        self, app_id: int, parameter_id: str,
    ) -> list[str]:
        """Get the axis parameter IDs for a map parameter.

        Args:
            app_id: Application ID.
            parameter_id: Map parameter identifier.

        Returns:
            List of axis parameter ID strings.
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        reply = self._call(self._stub.GetAxisParameterFromMap, request)
        return list(reply.parameter_ids)

    def get_conversion_use(
        self, app_id: int, conversion_id: str,
    ) -> list[str]:
        """Get the parameter IDs that use a given conversion.

        Args:
            app_id: Application ID.
            conversion_id: Conversion identifier.

        Returns:
            List of parameter ID strings that reference this conversion.
        """
        request = common_pb2.ConversionRequest(app_id=app_id, conversion_id=conversion_id)
        reply = self._call(self._stub.GetConversionUse, request)
        return list(reply.parameter_ids)

    # ==================================================================
    # Conversion getters
    # ==================================================================

    def get_conversion_type(self, conversion_id: str) -> pb2.ConversionTypeReply:
        """Get the type of a conversion.

        Args:
            conversion_id: Conversion identifier.

        Returns:
            ``ConversionTypeReply`` with ``conversion_id`` and ``type``.
        """
        request = pb2.ConversionNoAppRequest(conversion_id=conversion_id)
        return self._call(self._stub.GetConversionType, request)

    def get_rational_conversion(
        self, conversion_id: str,
    ) -> pb2.RationalConversionReply:
        """Get a rational conversion definition.

        Args:
            conversion_id: Conversion identifier.

        Returns:
            ``RationalConversionReply`` with six coefficients, comment,
            format, units, and default.
        """
        request = pb2.ConversionNoAppRequest(conversion_id=conversion_id)
        return self._call(self._stub.GetRationalConversion, request)

    def get_table_conversion(
        self, conversion_id: str,
    ) -> pb2.TableConversionReply:
        """Get a table conversion definition.

        Args:
            conversion_id: Conversion identifier.

        Returns:
            ``TableConversionReply`` with comment, format, units, default,
            interpolate flag, and table values.
        """
        request = pb2.ConversionNoAppRequest(conversion_id=conversion_id)
        return self._call(self._stub.GetTableConversion, request)

    def get_text_conversion(
        self, conversion_id: str,
    ) -> pb2.TextConversionReply:
        """Get a text conversion definition.

        Args:
            conversion_id: Conversion identifier.

        Returns:
            ``TextConversionReply`` with format, units, default, and
            text mapping values.
        """
        request = pb2.ConversionNoAppRequest(conversion_id=conversion_id)
        return self._call(self._stub.GetTextConversion, request)

    def get_formula_conversion(
        self, conversion_id: str,
    ) -> pb2.FormulaConversionReply:
        """Get a formula conversion definition.

        Args:
            conversion_id: Conversion identifier.

        Returns:
            ``FormulaConversionReply`` with comment, format, units,
            formula, and inverse formula.
        """
        request = pb2.ConversionNoAppRequest(conversion_id=conversion_id)
        return self._call(self._stub.GetFormulaConversion, request)

    def get_app_rational_conversion(
        self, app_id: int, conversion_id: str,
    ) -> pb2.RationalConversionReply:
        """Get a rational conversion as applied within an application.

        Args:
            app_id: Application ID.
            conversion_id: Conversion identifier.

        Returns:
            ``RationalConversionReply`` with six coefficients, comment,
            format, units, and default.
        """
        request = common_pb2.ConversionRequest(app_id=app_id, conversion_id=conversion_id)
        return self._call(self._stub.GetAppRationalConversion, request)

    def get_app_table_conversion(
        self, app_id: int, conversion_id: str,
    ) -> pb2.TableConversionReply:
        """Get a table conversion as applied within an application.

        Args:
            app_id: Application ID.
            conversion_id: Conversion identifier.

        Returns:
            ``TableConversionReply`` with comment, format, units, default,
            interpolate flag, and table values.
        """
        request = common_pb2.ConversionRequest(app_id=app_id, conversion_id=conversion_id)
        return self._call(self._stub.GetAppTableConversion, request)

    # ==================================================================
    # Conversion setters
    # ==================================================================

    def set_rational_conversion(
        self,
        conversion_id: str,
        *,
        coefficient1: float = 0.0,
        coefficient2: float = 0.0,
        coefficient3: float = 0.0,
        coefficient4: float = 0.0,
        coefficient5: float = 0.0,
        coefficient6: float = 0.0,
        comment: str = "",
        format: str = "",
        units: str = "",
        default: str = "",
        overwrite: bool = False,
    ) -> None:
        """Create or update a rational conversion.

        Args:
            conversion_id: Conversion identifier.
            coefficient1: First coefficient.
            coefficient2: Second coefficient.
            coefficient3: Third coefficient.
            coefficient4: Fourth coefficient.
            coefficient5: Fifth coefficient.
            coefficient6: Sixth coefficient.
            comment: Conversion comment.
            format: Display format string.
            units: Engineering units.
            default: Default display value.
            overwrite: If ``True``, overwrite an existing conversion.
        """
        request = pb2.RationalConversionRequest(
            conversion_id=conversion_id,
            coefficient1=coefficient1,
            coefficient2=coefficient2,
            coefficient3=coefficient3,
            coefficient4=coefficient4,
            coefficient5=coefficient5,
            coefficient6=coefficient6,
            comment=comment,
            format=format,
            units=units,
            default=default,
            overwrite=overwrite,
        )
        self._call(self._stub.SetRationalConversion, request)

    def set_table_conversion(
        self,
        conversion_id: str,
        *,
        comment: str = "",
        format: str = "",
        units: str = "",
        default: str = "",
        interpolate: bool = False,
        values: Sequence[pb2.TableConversion] | None = None,
        overwrite: bool = False,
    ) -> None:
        """Create or update a table conversion.

        Args:
            conversion_id: Conversion identifier.
            comment: Conversion comment.
            format: Display format string.
            units: Engineering units.
            default: Default display value.
            interpolate: Whether to interpolate between table entries.
            values: List of ``pb2.TableConversion(raw=..., mapped=...)``
                entries.
            overwrite: If ``True``, overwrite an existing conversion.
        """
        request = pb2.TableConversionRequest(
            conversion_id=conversion_id,
            comment=comment,
            format=format,
            units=units,
            default=default,
            interpolate=interpolate,
            values=values or [],
            overwrite=overwrite,
        )
        self._call(self._stub.SetTableConversion, request)

    def set_text_conversion(
        self,
        conversion_id: str,
        *,
        format: str = "",
        units: str = "",
        default: str = "",
        values: Sequence[pb2.TextConversion] | None = None,
        overwrite: bool = False,
    ) -> None:
        """Create or update a text conversion.

        Args:
            conversion_id: Conversion identifier.
            format: Display format string.
            units: Engineering units.
            default: Default display value.
            values: List of ``pb2.TextConversion(raw=..., mapped=...)``
                entries.
            overwrite: If ``True``, overwrite an existing conversion.
        """
        request = pb2.TextConversionRequest(
            conversion_id=conversion_id,
            format=format,
            units=units,
            default=default,
            values=values or [],
            overwrite=overwrite,
        )
        self._call(self._stub.SetTextConversion, request)

    def set_formula_conversion(
        self,
        conversion_id: str,
        *,
        comment: str = "",
        format: str = "",
        units: str = "",
        formula: str = "",
        inverse: str = "",
        overwrite: bool = False,
    ) -> None:
        """Create or update a formula conversion.

        Args:
            conversion_id: Conversion identifier.
            comment: Conversion comment.
            format: Display format string.
            units: Engineering units.
            formula: Forward conversion formula string.
            inverse: Inverse conversion formula string.
            overwrite: If ``True``, overwrite an existing conversion.
        """
        request = pb2.FormulaConversionRequest(
            conversion_id=conversion_id,
            comment=comment,
            format=format,
            units=units,
            formula=formula,
            inverse=inverse,
            overwrite=overwrite,
        )
        self._call(self._stub.SetFormulaConversion, request)

    # ==================================================================
    # Value offset
    # ==================================================================

    def get_value_offset(self, app_id: int, parameter_id: str) -> float:
        """Get the value offset for a parameter.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.

        Returns:
            The offset value.
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        reply = self._call(self._stub.GetValueOffset, request)
        return reply.offset

    def set_value_offset(
        self, app_id: int, parameter_id: str, offset: float,
    ) -> None:
        """Set the value offset for a parameter.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.
            offset: Offset value to apply.
        """
        request = pb2.OffsetRequest(
            app_id=app_id, parameter_id=parameter_id, offset=offset,
        )
        self._call(self._stub.SetValueOffset, request)

    def zero_live_value(self, app_id: int, parameter_id: str) -> None:
        """Zero the live value of a parameter by adjusting its offset.

        Args:
            app_id: Application ID.
            parameter_id: Parameter identifier.
        """
        request = common_pb2.ParameterRequest(app_id=app_id, parameter_id=parameter_id)
        self._call(self._stub.ZeroLiveValue, request)

    # ==================================================================
    # Get values
    # ==================================================================

    def get_value_measurement(
        self, app_id: int, parameter_ids: Sequence[str],
    ) -> list[pb2.ParameterValue]:
        """Get measurement values for parameters.

        Args:
            app_id: Application ID.
            parameter_ids: Parameter identifiers to read.

        Returns:
            List of ``ParameterValue`` with ``parameter_id``, ``value``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.AppParametersRequest(
            app_id=app_id, parameter_ids=parameter_ids,
        )
        reply = self._call(self._stub.GetValueMeasurement, request)
        return list(reply.values)

    def get_value_scalar(
        self, app_id: int, parameter_ids: Sequence[str],
    ) -> list[pb2.ParameterValue]:
        """Get scalar values for parameters.

        Args:
            app_id: Application ID.
            parameter_ids: Parameter identifiers to read.

        Returns:
            List of ``ParameterValue`` with ``parameter_id``, ``value``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.AppParametersRequest(
            app_id=app_id, parameter_ids=parameter_ids,
        )
        reply = self._call(self._stub.GetValueScalar, request)
        return list(reply.values)

    def get_value_1_axis_map(
        self, app_id: int, parameter_ids: Sequence[str],
    ) -> list[pb2.Array1dValues]:
        """Get 1-axis map values for parameters.

        Args:
            app_id: Application ID.
            parameter_ids: Parameter identifiers to read.

        Returns:
            List of ``Array1dValues`` with ``parameter_id``, ``values``
            (list of floats), and per-parameter ``return_code``.
        """
        request = common_pb2.AppParametersRequest(
            app_id=app_id, parameter_ids=parameter_ids,
        )
        reply = self._call(self._stub.GetValue1AxisMap, request)
        return list(reply.values)

    def get_value_2_axis_map(
        self, app_id: int, parameter_ids: Sequence[str],
    ) -> list[pb2.Array2dValues]:
        """Get 2-axis map values for parameters.

        Args:
            app_id: Application ID.
            parameter_ids: Parameter identifiers to read.

        Returns:
            List of ``Array2dValues`` with ``parameter_id``, ``rows``
            (each containing a list of floats), and per-parameter
            ``return_code``.
        """
        request = common_pb2.AppParametersRequest(
            app_id=app_id, parameter_ids=parameter_ids,
        )
        reply = self._call(self._stub.GetValue2AxisMap, request)
        return list(reply.values)

    def get_value_axis(
        self, app_id: int, parameter_ids: Sequence[str],
    ) -> list[pb2.Array1dValues]:
        """Get axis values for parameters.

        Args:
            app_id: Application ID.
            parameter_ids: Parameter identifiers to read.

        Returns:
            List of ``Array1dValues`` with ``parameter_id``, ``values``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.AppParametersRequest(
            app_id=app_id, parameter_ids=parameter_ids,
        )
        reply = self._call(self._stub.GetValueAxis, request)
        return list(reply.values)

    def get_value_array(
        self, app_id: int, parameter_ids: Sequence[str],
    ) -> list[pb2.Array1dValues]:
        """Get array values for parameters.

        Args:
            app_id: Application ID.
            parameter_ids: Parameter identifiers to read.

        Returns:
            List of ``Array1dValues`` with ``parameter_id``, ``values``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.AppParametersRequest(
            app_id=app_id, parameter_ids=parameter_ids,
        )
        reply = self._call(self._stub.GetValueArray, request)
        return list(reply.values)

    def get_value_string(
        self, app_id: int, parameter_ids: Sequence[str],
    ) -> list[pb2.StringParameterValue]:
        """Get string values for parameters.

        Args:
            app_id: Application ID.
            parameter_ids: Parameter identifiers to read.

        Returns:
            List of ``StringParameterValue`` with ``parameter_id``,
            ``value`` (string), and per-parameter ``return_code``.
        """
        request = common_pb2.AppParametersRequest(
            app_id=app_id, parameter_ids=parameter_ids,
        )
        reply = self._call(self._stub.GetValueString, request)
        return list(reply.values)

    def get_value_can(
        self, parameter_ids: Sequence[str],
    ) -> list[pb2.ParameterValue]:
        """Get CAN parameter values.

        Args:
            parameter_ids: CAN parameter identifiers.

        Returns:
            List of ``ParameterValue`` with ``parameter_id``, ``value``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.ParametersRequest(parameter_ids=parameter_ids)
        reply = self._call(self._stub.GetValueCAN, request)
        return list(reply.values)

    def get_value_virtual(
        self, parameter_ids: Sequence[str],
    ) -> list[pb2.ParameterValue]:
        """Get virtual parameter values.

        Args:
            parameter_ids: Virtual parameter identifiers.

        Returns:
            List of ``ParameterValue`` with ``parameter_id``, ``value``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.ParametersRequest(parameter_ids=parameter_ids)
        reply = self._call(self._stub.GetValueVirtual, request)
        return list(reply.values)

    # ==================================================================
    # Get DTV values
    # ==================================================================

    def get_dtv_value_scalar(
        self, parameter_ids: Sequence[str], file_path: str,
    ) -> list[pb2.ParameterValue]:
        """Get scalar values from a DTV file.

        Args:
            parameter_ids: Parameter identifiers to read.
            file_path: Path to the DTV file.

        Returns:
            List of ``ParameterValue`` with ``parameter_id``, ``value``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.ParametersFileRequest(
            parameter_ids=parameter_ids, file_path=file_path,
        )
        reply = self._call(self._stub.GetDTVValueScalar, request)
        return list(reply.values)

    def get_dtv_value_1_axis_map(
        self, parameter_ids: Sequence[str], file_path: str,
    ) -> list[pb2.Array1dValues]:
        """Get 1-axis map values from a DTV file.

        Args:
            parameter_ids: Parameter identifiers to read.
            file_path: Path to the DTV file.

        Returns:
            List of ``Array1dValues`` with ``parameter_id``, ``values``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.ParametersFileRequest(
            parameter_ids=parameter_ids, file_path=file_path,
        )
        reply = self._call(self._stub.GetDTVValue1AxisMap, request)
        return list(reply.values)

    def get_dtv_value_2_axis_map(
        self, parameter_ids: Sequence[str], file_path: str,
    ) -> list[pb2.Array2dValues]:
        """Get 2-axis map values from a DTV file.

        Args:
            parameter_ids: Parameter identifiers to read.
            file_path: Path to the DTV file.

        Returns:
            List of ``Array2dValues`` with ``parameter_id``, ``rows``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.ParametersFileRequest(
            parameter_ids=parameter_ids, file_path=file_path,
        )
        reply = self._call(self._stub.GetDTVValue2AxisMap, request)
        return list(reply.values)

    def get_dtv_value_axis(
        self, parameter_ids: Sequence[str], file_path: str,
    ) -> list[pb2.Array1dValues]:
        """Get axis values from a DTV file.

        Args:
            parameter_ids: Parameter identifiers to read.
            file_path: Path to the DTV file.

        Returns:
            List of ``Array1dValues`` with ``parameter_id``, ``values``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.ParametersFileRequest(
            parameter_ids=parameter_ids, file_path=file_path,
        )
        reply = self._call(self._stub.GetDTVValueAxis, request)
        return list(reply.values)

    def get_dtv_value_array(
        self, parameter_ids: Sequence[str], file_path: str,
    ) -> list[pb2.Array1dValues]:
        """Get array values from a DTV file.

        Args:
            parameter_ids: Parameter identifiers to read.
            file_path: Path to the DTV file.

        Returns:
            List of ``Array1dValues`` with ``parameter_id``, ``values``,
            and per-parameter ``return_code``.
        """
        request = common_pb2.ParametersFileRequest(
            parameter_ids=parameter_ids, file_path=file_path,
        )
        reply = self._call(self._stub.GetDTVValueArray, request)
        return list(reply.values)

    def get_dtv_value_string(
        self, parameter_ids: Sequence[str], file_path: str,
    ) -> list[pb2.StringParameterValue]:
        """Get string values from a DTV file.

        Args:
            parameter_ids: Parameter identifiers to read.
            file_path: Path to the DTV file.

        Returns:
            List of ``StringParameterValue`` with ``parameter_id``,
            ``value``, and per-parameter ``return_code``.
        """
        request = common_pb2.ParametersFileRequest(
            parameter_ids=parameter_ids, file_path=file_path,
        )
        reply = self._call(self._stub.GetDTVValueString, request)
        return list(reply.values)

    # ==================================================================
    # Set values
    # ==================================================================

    def set_value_scalar(
        self, app_id: int, values: dict[str, float],
    ) -> list[pb2.ParameterValue]:
        """Set scalar parameter values.

        Args:
            app_id: Application ID.
            values: Mapping of ``parameter_id`` → ``value``.

        Returns:
            List of ``ParameterValue`` with per-parameter return codes.
        """
        params = [
            pb2.ParameterSetValue(parameter_id=pid, value=val)
            for pid, val in values.items()
        ]
        request = pb2.AppParameterValuesRequest(app_id=app_id, parameters=params)
        reply = self._call(self._stub.SetValueScalar, request)
        return list(reply.parameters)

    def set_value_1_axis_map(
        self, app_id: int, values: dict[str, Sequence[float]],
    ) -> list[pb2.Array1dParameterValue]:
        """Set 1-axis map parameter values.

        Args:
            app_id: Application ID.
            values: Mapping of ``parameter_id`` → list of float values.

        Returns:
            List of ``Array1dParameterValue`` with per-parameter return codes.
        """
        params = [
            pb2.Array1dParameterSetValue(parameter_id=pid, values=vals)
            for pid, vals in values.items()
        ]
        request = pb2.AppArray1dParameterValuesRequest(app_id=app_id, parameters=params)
        reply = self._call(self._stub.SetValue1AxisMap, request)
        return list(reply.parameters)

    def set_value_2_axis_map(
        self, app_id: int, values: dict[str, Sequence[Sequence[float]]],
    ) -> list[pb2.Array2dParameterValue]:
        """Set 2-axis map parameter values.

        Args:
            app_id: Application ID.
            values: Mapping of ``parameter_id`` → list of rows, where each
                row is a list of float values.

        Returns:
            List of ``Array2dParameterValue`` with per-parameter return codes.
        """
        params = [
            pb2.Array2dParameterSetValue(
                parameter_id=pid,
                rows=[pb2.RowValues(values=row) for row in rows],
            )
            for pid, rows in values.items()
        ]
        request = pb2.AppArray2dParameterValuesRequest(app_id=app_id, parameters=params)
        reply = self._call(self._stub.SetValue2AxisMap, request)
        return list(reply.parameters)

    def set_value_axis(
        self, app_id: int, values: dict[str, Sequence[float]],
    ) -> list[pb2.Array1dParameterValue]:
        """Set axis parameter values.

        Args:
            app_id: Application ID.
            values: Mapping of ``parameter_id`` → list of float values.

        Returns:
            List of ``Array1dParameterValue`` with per-parameter return codes.
        """
        params = [
            pb2.Array1dParameterSetValue(parameter_id=pid, values=vals)
            for pid, vals in values.items()
        ]
        request = pb2.AppArray1dParameterValuesRequest(app_id=app_id, parameters=params)
        reply = self._call(self._stub.SetValueAxis, request)
        return list(reply.parameters)

    def set_value_array(
        self, app_id: int, values: dict[str, Sequence[float]],
    ) -> list[pb2.Array1dParameterValue]:
        """Set array parameter values.

        Args:
            app_id: Application ID.
            values: Mapping of ``parameter_id`` → list of float values.

        Returns:
            List of ``Array1dParameterValue`` with per-parameter return codes.
        """
        params = [
            pb2.Array1dParameterSetValue(parameter_id=pid, values=vals)
            for pid, vals in values.items()
        ]
        request = pb2.AppArray1dParameterValuesRequest(app_id=app_id, parameters=params)
        reply = self._call(self._stub.SetValueArray, request)
        return list(reply.parameters)

    def set_value_string(
        self, app_id: int, values: dict[str, str],
    ) -> list[pb2.StringParameterValue]:
        """Set string parameter values.

        Args:
            app_id: Application ID.
            values: Mapping of ``parameter_id`` → string value.

        Returns:
            List of ``StringParameterValue`` with per-parameter return codes.
        """
        params = [
            pb2.StringParameterSetValue(parameter_id=pid, value=val)
            for pid, val in values.items()
        ]
        request = pb2.AppStringParameterValuesRequest(app_id=app_id, parameters=params)
        reply = self._call(self._stub.SetValueString, request)
        return list(reply.parameters)

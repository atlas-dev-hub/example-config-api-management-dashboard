"""Unit tests for enums and error mapping — no live server required."""

import pytest

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
from sm_config_api.errors import (
    InvalidFileError,
    NoEcuError,
    NoLicenceError,
    NoProjectError,
    ParameterNotFoundError,
    SystemMonitorError,
    raise_for_error_code,
)


class TestErrorCode:
    """Test the ErrorCode IntEnum."""

    def test_no_error_is_zero(self):
        assert ErrorCode.NO_ERROR == 0

    def test_negative_codes(self):
        assert ErrorCode.NO_PROJECT < 0
        assert ErrorCode.NO_LICENCE < 0
        assert ErrorCode.NO_ECU < 0

    def test_known_codes_exist(self):
        # Spot-check a handful
        assert ErrorCode.INVALID_FILE == -8
        assert ErrorCode.PARAMETER_NOT_FOUND == -100
        assert ErrorCode.NO_PROJECT == -1

    def test_conversion_from_int(self):
        assert ErrorCode(-8) == ErrorCode.INVALID_FILE


class TestRaiseForErrorCode:
    """Test the raise_for_error_code helper."""

    def test_no_error_does_not_raise(self):
        # Should not raise for code 0
        raise_for_error_code(0)

    def test_no_project_raises(self):
        with pytest.raises(NoProjectError):
            raise_for_error_code(-1)

    def test_no_licence_raises(self):
        with pytest.raises(NoLicenceError):
            raise_for_error_code(-2)

    def test_no_ecu_raises(self):
        with pytest.raises(NoEcuError):
            raise_for_error_code(-7)

    def test_invalid_file_raises(self):
        with pytest.raises(InvalidFileError):
            raise_for_error_code(-8)

    def test_parameter_not_found_raises(self):
        with pytest.raises(ParameterNotFoundError):
            raise_for_error_code(-100)

    def test_unknown_code_raises_base(self):
        with pytest.raises(SystemMonitorError) as exc_info:
            raise_for_error_code(-9999)
        assert exc_info.value.code == -9999

    def test_error_has_code_attribute(self):
        with pytest.raises(SystemMonitorError) as exc_info:
            raise_for_error_code(-1)
        assert exc_info.value.code == -1


class TestEnums:
    """Spot-check that all enums are importable and have expected members."""

    def test_link_status(self):
        assert LinkStatus.LINK_OK == 0
        assert LinkStatus.LINK_NOK == 1

    def test_buffer_type_values(self):
        assert BufferType.UNIT_BUFFER == 0
        assert BufferType.EDIT_BUFFER == 1

    def test_conversion_type(self):
        assert ConversionType.RATIONAL == 0
        assert ConversionType.TABLE == 1
        assert ConversionType.TEXT == 2

    def test_file_type(self):
        assert hasattr(FileType, "DTV")

    def test_parameter_type_bitmask(self):
        # ParameterType values are bitmasks
        assert ParameterType.SCALAR != 0

    def test_trigger_type(self):
        assert hasattr(TriggerType, "ON_DATA")
        assert TriggerType.NO_CONDITION == 4

    def test_trigger_operator(self):
        assert hasattr(TriggerOperator, "GREATER_THAN")

    def test_all_enums_are_int(self):
        """All our enums should be IntEnum (subclass of int)."""
        for enum_cls in [
            BufferType, ByteOrder, ConversionType, DataType,
            ErrorCode, ErrorStatus, EventPriority, FileType,
            LinkStatus, LoggingType, ParameterType, Reason,
            TriggerOperator, TriggerType,
        ]:
            for member in enum_cls:
                assert isinstance(member.value, int), f"{enum_cls.__name__}.{member.name}"

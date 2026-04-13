"""Python-friendly enum wrappers for System Monitor Configuration API.

These mirror the proto enums but provide proper Python IntEnum semantics
with docstrings, so IDE autocompletion and type-checking work naturally.

Usage:
    from sm_config_api.enums import ParameterType, ErrorCode

    if param_type == ParameterType.SCALAR:
        ...
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """System Monitor error codes returned by all API calls."""

    NO_ERROR = 0
    NO_PROJECT = -1
    NO_LICENCE = -2
    NON_SPECIFIC = -3
    DATA_VERSION_MISMATCH = -4
    NO_DATA_VERSION = -5
    NO_PROGRAM_VERSION = -6
    NO_ECU = -7
    INVALID_FILE = -8
    NO_APPLICATION = -9
    APPLICATION_INACTIVE = -10
    LIVE_UPDATES_ON = -11
    TAGTRONIC_ONLY = -12
    SM_BUSY = -13
    MESSAGE_ARGUMENT_MISMATCH = -20
    MESSAGE_DIMENSION_MISMATCH = -21
    MESSAGE_LOWER_BOUND_NON_ZERO = -22
    BOUNDS_ERROR = -23
    MESSAGE_ARGUMENT_ERROR = -24
    MESSAGE_ARGUMENT_INVALID = -25
    FDL_NOT_PARSED = -26
    CONVERSION_INVALID = -27
    PARAMETER_INVALID = -28
    PARAMETER_OVERRIDE_NOT_ALLOWED = -29
    BAD_STATE = -30
    INVALID_COMMAND = -31
    NO_DATA_PRESENT = -32
    BAD_MEMORY_ALLOCATION = -33
    PARTIALLY_COMPLETE = -34
    DOCUMENT_FULL = -35
    PARAMETER_IDENTIFIER_ALREADY_EXISTS = -36
    PARAMETER_READ_ONLY = -37
    PARAMETER_NON_LIVE_TUNEABLE = -38
    GROUP_NOT_FOUND = -39
    FILE_REQUIRES_SAVING = -40
    FREQUENCY_OVERRIDDEN = -41
    NO_CUSTOMER_BASE = -42
    PARAMETER_NOT_FOUND = -100
    ERROR_READ_ONLY = -101
    ERROR_LIMITS = -102
    ERROR_MONOTONY = -103
    ERROR_AXIS_PT = -104
    ERROR_ADDRESS = -105
    ERROR_NON_NUM = -106
    ERROR_SIZE = -107
    ERROR_LIVE_TUNE = -108
    ERROR_INTP = -109
    ERROR_ACTIVELAYER = -110
    ERROR_TOLERANCE = -111
    ERROR_AXIS_CHANGE = -112
    ERROR_NO_LIVE_TUNE = -113
    ERROR_VALIDATION = -114
    ERROR_LIVE_TUNE_DATA_INVALID = -115
    ERROR_SERIAL_NOT_FOUND = -116
    ERROR_UNKNOWN = -117
    ERROR_CANCEL = -118
    ERROR_LOCKED_PARAM = -119
    ERROR_VALUE_NOT_MATCHING_ENTRY = -120
    DETAIL_UNKNOWN = -200
    DUMP_ROW_DATA_FAILED = -201
    LIVE_UPDATE_FAILED = -300
    ONLINE_FAILED = -301
    DOWNLOAD_DATA_FAILED = -302
    SYSTEM_NOT_RUNNING = -303
    PARAMETER_LOCKED = -304
    COMMS_BASE = -1000


class LinkStatus(IntEnum):
    """ECU link status."""

    LINK_OK = 0
    LINK_NOK = 1
    CONTROLLER_BUSY = 2
    IN_BOOT = 3
    ZONE_1 = 4
    ZONE_2 = 5
    ZONE_3 = 6
    BAD_RESPONSE = 7
    INVALID_DEVICE = 8
    UNKNOWN = 0xFFFF


class FileType(IntEnum):
    """System Monitor file types."""

    PROJECT = 0
    PGV = 1
    DTV = 2
    DESKTOP = 3
    LOGGING_CONFIG = 4
    VIRTUALS = 5
    CAN = 6
    LIVE_LOGGING = 7
    POT_BOARD = 8


class ParameterType(IntEnum):
    """System Monitor parameter types (bitmask values)."""

    UNDEFINED = 0
    SCALAR = 0x00000001
    AXIS_1 = 0x00000002
    AXIS_2 = 0x00000004
    ARRAY = 0x00000010
    STRING = 0x00000020
    ECU = 0x00000080
    CAN = 0x00000100
    TSB = 0x00000200
    VIRTUAL = 0x00000400
    AXIS = 0x00030000
    INPUT = 0x10000000
    MEASUREMENT = 0x10000780


class ConversionType(IntEnum):
    """Parameter conversion rule types."""

    RATIONAL = 0
    TABLE = 1
    TEXT = 2
    FORMULA = 3


class DataType(IntEnum):
    """ECU parameter data types."""

    UBYTE = 0
    BYTE = 1
    UWORD = 2
    WORD = 3
    ULONG = 4
    LONG = 5
    FLOAT = 6
    UNKNOWN = 7
    QWORD = 8
    SQWORD = 9
    DOUBLE = 10


class ByteOrder(IntEnum):
    """Parameter byte ordering."""

    MSB_FIRST = 0
    MSB_LAST = 1


class BufferType(IntEnum):
    """Data buffer types for undo operations."""

    UNIT_BUFFER = 0
    EDIT_BUFFER = 1
    UNIT_AND_EDIT_BUFFER = 2


class Reason(IntEnum):
    """Parameter comparison reason codes (bitmask values)."""

    NONE = 0x00000000
    ABSENT = 0x00000001
    DIFFERENT = 0x00000002
    EQUAL = 0x00000004
    DIFFERENT_VALUE = 0x00000008
    DIFFERENT_SIZE = 0x00000010
    DIFFERENT_CONV = 0x00000020
    DIFFERENT_UNITS = 0x00000040
    DIFFERENT_TYPE = 0x00000080
    DIFFERENT_COMMENT = 0x00000100
    DIFFERENT_DEF_VALUE = 0x00000200
    ABSENT_MASTER = 0x00000400
    LOCKED = 0x10000000


class EventPriority(IntEnum):
    """Event priority levels."""

    HIGH = 0
    MEDIUM = 1
    LOW = 2
    DEBUG = 3


class ErrorStatus(IntEnum):
    """Active error status levels."""

    UNKNOWN = 0
    CURRENT = 1
    LOGGED = 2


class TriggerType(IntEnum):
    """Logging trigger condition types."""

    ON_DATA = 0
    DRIVER_PUSH = 1
    IGNITION_ON = 2
    LAP_TRIGGER = 3
    NO_CONDITION = 4
    EXTERNAL_TRIGGER = 5


class TriggerOperator(IntEnum):
    """Logging trigger comparison operators."""

    EQUALS = 0
    LESS_THAN = 1
    GREATER_THAN = 2
    NOT_EQUAL_TO = 3
    GREATER_THAN_OR_EQUAL = 4
    LESS_THAN_OR_EQUAL = 5


class LoggingType(IntEnum):
    """Logging channel rate types."""

    FREQUENCY = 0
    CYLINDER = 1
    CYCLE = 2
    UNKNOWN = 3
    EDGE = 4

"""Exception hierarchy for System Monitor Configuration API.

Maps gRPC ErrorCode values to typed Python exceptions so callers can
catch specific failure modes:

    from sm_config_api.errors import ParameterNotFoundError, NoProjectError

    try:
        client.parameter.get_value_scalar(app_id, [param_id])
    except ParameterNotFoundError:
        print("Parameter does not exist")
    except NoProjectError:
        print("No project loaded")
    except SystemMonitorError as e:
        print(f"API error {e.code}: {e}")
"""

from __future__ import annotations

from sm_config_api.enums import ErrorCode


class SystemMonitorError(Exception):
    """Base exception for all System Monitor API errors.

    Attributes:
        code: The ErrorCode value from the API response.
        message: Human-readable description of the error.
    """

    def __init__(self, code: ErrorCode | int, message: str | None = None):
        if isinstance(code, ErrorCode):
            self.code = code
        else:
            try:
                self.code = ErrorCode(code)
            except ValueError:
                self.code = code  # type: ignore[assignment]
        self.message = message or (self.code.name if isinstance(self.code, ErrorCode) else str(code))
        code_val = self.code.value if isinstance(self.code, ErrorCode) else self.code
        super().__init__(f"[{code_val}] {self.message}")


# --- Project & State errors ---


class NoProjectError(SystemMonitorError):
    """No project is loaded in System Monitor."""


class NoLicenceError(SystemMonitorError):
    """No licence for the requested function."""


class NonSpecificError(SystemMonitorError):
    """Non-specific error occurred."""


class DataVersionMismatchError(SystemMonitorError):
    """Data version mismatch between edit buffer and ECU."""


class NoDataVersionError(SystemMonitorError):
    """No data version is loaded."""


class NoProgramVersionError(SystemMonitorError):
    """No program version is loaded."""


class NoEcuError(SystemMonitorError):
    """No ECU is connected."""


class InvalidFileError(SystemMonitorError):
    """Invalid file specified."""


class NoApplicationError(SystemMonitorError):
    """The open project does not cover the specified application."""


class ApplicationInactiveError(SystemMonitorError):
    """Application must be active to support this operation."""


class LiveUpdatesOnError(SystemMonitorError):
    """Operation not allowed while live updates are on."""


class TagtronicOnlyError(SystemMonitorError):
    """This command is only valid for TAGtronic systems."""


class SmBusyError(SystemMonitorError):
    """System Monitor cannot accept API calls at the moment."""


# --- Message errors ---


class MessageError(SystemMonitorError):
    """Base for SendMessage-related errors."""


class MessageArgumentMismatchError(MessageError):
    """Type mismatch in SendMessage argument."""


class MessageDimensionMismatchError(MessageError):
    """Array dimension mismatch in SendMessage argument."""


# --- Virtual / Conversion errors ---


class FdlNotParsedError(SystemMonitorError):
    """Virtual parameter contains invalid FDL expression."""


class ConversionInvalidError(SystemMonitorError):
    """Conversion for parameter does not exist or is invalid."""


class ParameterInvalidError(SystemMonitorError):
    """Parameter name does not exist or is invalid."""


class ParameterOverrideNotAllowedError(SystemMonitorError):
    """Parameter exists and overwrite is not allowed."""


# --- State & command errors ---


class BadStateError(SystemMonitorError):
    """Request cannot be actioned due to incorrect SM state."""


class InvalidCommandError(SystemMonitorError):
    """Command passed to SM is not valid."""


class NoDataPresentError(SystemMonitorError):
    """Missing document or similar."""


class BadMemoryAllocationError(SystemMonitorError):
    """Memory allocation failed."""


class PartiallyCompleteError(SystemMonitorError):
    """Operation only partially completed."""


class DocumentFullError(SystemMonitorError):
    """The current document (config) is full."""


class ParameterIdentifierExistsError(SystemMonitorError):
    """Parameter identifier already exists in another application."""


class ParameterReadOnlyError(SystemMonitorError):
    """Parameter is read-only — write access denied."""


class ParameterNonLiveTuneableError(SystemMonitorError):
    """Parameter is non-live tuneable — write access denied."""


class GroupNotFoundError(SystemMonitorError):
    """Requested group is not found."""


class FileRequiresSavingError(SystemMonitorError):
    """Previous virtual parameters file has been modified and not saved."""


class NoCustomerBaseError(SystemMonitorError):
    """No customer base found for the project being opened."""


# --- Parameter value errors (−100 range) ---


class ParameterNotFoundError(SystemMonitorError):
    """Specified parameter does not exist in current program version."""


class ParameterValueReadOnlyError(SystemMonitorError):
    """Tried to set a read-only parameter value."""


class ParameterLimitsError(SystemMonitorError):
    """Tried to set a parameter outside its limits."""


class AxisMonotonyError(SystemMonitorError):
    """Axis monotony restrictions not adhered to."""


class InvalidAxisPointError(SystemMonitorError):
    """Tried to get/set parameter at invalid breakpoint."""


class InvalidAddressError(SystemMonitorError):
    """Parameter had invalid address."""


class NonNumericError(SystemMonitorError):
    """String containing non-numeric characters supplied to set function."""


class SizeError(SystemMonitorError):
    """Exceeded specified size of array or string parameter."""


class LiveTuneError(SystemMonitorError):
    """Live tune enabled, failed to update value in ECU."""


class InterpolationError(SystemMonitorError):
    """Tried to get interpolated value but no input quantity or axis points."""


class NoActivelayerError(SystemMonitorError):
    """No active live auto tune layer (group)."""


class ToleranceError(SystemMonitorError):
    """Operating point is outside breakpoint tolerances."""


class AxisChangeError(SystemMonitorError):
    """Number of axis breakpoints has changed between program versions."""


class NotLiveTuneableWarning(SystemMonitorError):
    """Parameter is not modifiable in live tune area (warning)."""


class ValidationError(SystemMonitorError):
    """The attempt to validate the value in the unit failed."""


class LiveTuneDataInvalidError(SystemMonitorError):
    """The live tune data is invalid."""


class SerialNotFoundError(SystemMonitorError):
    """Serial number not found for sensor channel."""


class UnknownError(SystemMonitorError):
    """An unknown error occurred."""


class CancelError(SystemMonitorError):
    """Attempt to set value cancelled."""


class LockedParamError(SystemMonitorError):
    """Access denied — parameter locked by RDA."""


class ValueNotMatchingEntryError(SystemMonitorError):
    """Value set does not match value in the unit."""


# --- Session & operational errors ---


class DetailUnknownError(SystemMonitorError):
    """Session detail does not exist."""


class DumpRowDataFailedError(SystemMonitorError):
    """Failed to dump row data."""


class LiveUpdateFailedError(SystemMonitorError):
    """Failed to enter live tune."""


class OnlineFailedError(SystemMonitorError):
    """Failed to go online."""


class DownloadDataFailedError(SystemMonitorError):
    """Failed to download data."""


class SystemNotRunningError(SystemMonitorError):
    """System Monitor is only running in OLE mode."""


class ParameterLockedError(SystemMonitorError):
    """Attempt to access a locked parameter."""


class CommsBaseError(SystemMonitorError):
    """Communications base error."""


# --- Mapping: ErrorCode → Exception class ---

_ERROR_CODE_MAP: dict[ErrorCode, type[SystemMonitorError]] = {
    ErrorCode.NO_PROJECT: NoProjectError,
    ErrorCode.NO_LICENCE: NoLicenceError,
    ErrorCode.NON_SPECIFIC: NonSpecificError,
    ErrorCode.DATA_VERSION_MISMATCH: DataVersionMismatchError,
    ErrorCode.NO_DATA_VERSION: NoDataVersionError,
    ErrorCode.NO_PROGRAM_VERSION: NoProgramVersionError,
    ErrorCode.NO_ECU: NoEcuError,
    ErrorCode.INVALID_FILE: InvalidFileError,
    ErrorCode.NO_APPLICATION: NoApplicationError,
    ErrorCode.APPLICATION_INACTIVE: ApplicationInactiveError,
    ErrorCode.LIVE_UPDATES_ON: LiveUpdatesOnError,
    ErrorCode.TAGTRONIC_ONLY: TagtronicOnlyError,
    ErrorCode.SM_BUSY: SmBusyError,
    ErrorCode.MESSAGE_ARGUMENT_MISMATCH: MessageArgumentMismatchError,
    ErrorCode.MESSAGE_DIMENSION_MISMATCH: MessageDimensionMismatchError,
    ErrorCode.MESSAGE_LOWER_BOUND_NON_ZERO: MessageError,
    ErrorCode.BOUNDS_ERROR: MessageError,
    ErrorCode.MESSAGE_ARGUMENT_ERROR: MessageError,
    ErrorCode.MESSAGE_ARGUMENT_INVALID: MessageError,
    ErrorCode.FDL_NOT_PARSED: FdlNotParsedError,
    ErrorCode.CONVERSION_INVALID: ConversionInvalidError,
    ErrorCode.PARAMETER_INVALID: ParameterInvalidError,
    ErrorCode.PARAMETER_OVERRIDE_NOT_ALLOWED: ParameterOverrideNotAllowedError,
    ErrorCode.BAD_STATE: BadStateError,
    ErrorCode.INVALID_COMMAND: InvalidCommandError,
    ErrorCode.NO_DATA_PRESENT: NoDataPresentError,
    ErrorCode.BAD_MEMORY_ALLOCATION: BadMemoryAllocationError,
    ErrorCode.PARTIALLY_COMPLETE: PartiallyCompleteError,
    ErrorCode.DOCUMENT_FULL: DocumentFullError,
    ErrorCode.PARAMETER_IDENTIFIER_ALREADY_EXISTS: ParameterIdentifierExistsError,
    ErrorCode.PARAMETER_READ_ONLY: ParameterReadOnlyError,
    ErrorCode.PARAMETER_NON_LIVE_TUNEABLE: ParameterNonLiveTuneableError,
    ErrorCode.GROUP_NOT_FOUND: GroupNotFoundError,
    ErrorCode.FILE_REQUIRES_SAVING: FileRequiresSavingError,
    ErrorCode.FREQUENCY_OVERRIDDEN: SystemMonitorError,
    ErrorCode.NO_CUSTOMER_BASE: NoCustomerBaseError,
    ErrorCode.PARAMETER_NOT_FOUND: ParameterNotFoundError,
    ErrorCode.ERROR_READ_ONLY: ParameterValueReadOnlyError,
    ErrorCode.ERROR_LIMITS: ParameterLimitsError,
    ErrorCode.ERROR_MONOTONY: AxisMonotonyError,
    ErrorCode.ERROR_AXIS_PT: InvalidAxisPointError,
    ErrorCode.ERROR_ADDRESS: InvalidAddressError,
    ErrorCode.ERROR_NON_NUM: NonNumericError,
    ErrorCode.ERROR_SIZE: SizeError,
    ErrorCode.ERROR_LIVE_TUNE: LiveTuneError,
    ErrorCode.ERROR_INTP: InterpolationError,
    ErrorCode.ERROR_ACTIVELAYER: NoActivelayerError,
    ErrorCode.ERROR_TOLERANCE: ToleranceError,
    ErrorCode.ERROR_AXIS_CHANGE: AxisChangeError,
    ErrorCode.ERROR_NO_LIVE_TUNE: NotLiveTuneableWarning,
    ErrorCode.ERROR_VALIDATION: ValidationError,
    ErrorCode.ERROR_LIVE_TUNE_DATA_INVALID: LiveTuneDataInvalidError,
    ErrorCode.ERROR_SERIAL_NOT_FOUND: SerialNotFoundError,
    ErrorCode.ERROR_UNKNOWN: UnknownError,
    ErrorCode.ERROR_CANCEL: CancelError,
    ErrorCode.ERROR_LOCKED_PARAM: LockedParamError,
    ErrorCode.ERROR_VALUE_NOT_MATCHING_ENTRY: ValueNotMatchingEntryError,
    ErrorCode.DETAIL_UNKNOWN: DetailUnknownError,
    ErrorCode.DUMP_ROW_DATA_FAILED: DumpRowDataFailedError,
    ErrorCode.LIVE_UPDATE_FAILED: LiveUpdateFailedError,
    ErrorCode.ONLINE_FAILED: OnlineFailedError,
    ErrorCode.DOWNLOAD_DATA_FAILED: DownloadDataFailedError,
    ErrorCode.SYSTEM_NOT_RUNNING: SystemNotRunningError,
    ErrorCode.PARAMETER_LOCKED: ParameterLockedError,
    ErrorCode.COMMS_BASE: CommsBaseError,
}


def raise_for_error_code(code: int, message: str | None = None) -> None:
    """Raise the appropriate exception if code indicates an error.

    Does nothing when code == 0 (NO_ERROR). Otherwise maps the error code
    to a specific exception subclass and raises it.

    Args:
        code: The return_code value from a gRPC response.
        message: Optional override for the error message.

    Raises:
        SystemMonitorError: (or a subclass) when code != 0.
    """
    if code == 0:
        return

    try:
        error_code = ErrorCode(code)
    except ValueError:
        raise SystemMonitorError(code, message or f"Unknown error code: {code}")

    exc_class = _ERROR_CODE_MAP.get(error_code, SystemMonitorError)
    raise exc_class(error_code, message)

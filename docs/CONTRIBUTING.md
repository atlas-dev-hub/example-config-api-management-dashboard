# Contributing to System Monitor Configuration API

This guide covers every step needed to contribute new functionality, from the
lowest-level gRPC wrapper method through to the PySide6 GUI action button.


## Architecture overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        gui/main.py                               │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│   │  System  │  │ Project  │  │Parameter │  │ Logging Virtual │  │
│   │   tab    │  │   tab    │  │   tab    │  │   tab    tab    │  │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └──┬────────┬────┘  │
│        │              │              │           │        │      │
│   Action buttons ──► _call(service, method, *args)              │
│        │                        │                                │
│   QThread workers ◄── run_in_thread(callable)                   │
│        │                        │                                │
├────────┼────────────────────────┼────────────────────────────────┤
│        │         sm_config_api  │                                │
│   ┌────┴────────────────────────┴──────────────────────────┐    │
│   │              SystemMonitorClient (facade)               │    │
│   │  .system  │  .project  │  .parameter  │  .logging  │   │    │
│   └────┬──────┴─────┬──────┴──────┬───────┴─────┬──────┘   │    │
│        │            │             │             │           │    │
│   ┌────┴────┐  ┌────┴────┐  ┌────┴────┐  ┌────┴────┐      │    │
│   │ System  │  │Project  │  │Paramet. │  │Logging  │  …   │    │
│   │Service  │  │Service  │  │Service  │  │Service  │      │    │
│   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘      │    │
│        │            │             │             │           │    │
│   All inherit BaseService._call() ──► return_code check     │    │
│                    │                ──► typed exceptions    │    │
│              grpc.Channel                                  │    │
│                    │                                        │    │
├────────────────────┼────────────────────────────────────────┤    │
│              System Monitor  (gRPC server, port 7000)       │    │
└────────────────────┴────────────────────────────────────────┘    │
```

Every RPC call follows the same path:
1. **Proto definition** → compile to Python stubs
2. **Service wrapper** → expose as a Pythonic method with `_call()`
3. **Client facade** → aggregates all 5 services into `SystemMonitorClient`
4. **GUI action** → button triggers the call via `run_in_thread()`


## Development setup

```bash
# Clone and enter the project
git clone <repository-url>
cd SystemMonitor_Configuration_API

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate     # Windows
source .venv/bin/activate  # Linux / macOS

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Generate gRPC stubs from proto files
python scripts/generate_protos.py

# Run the GUI
python run_gui.py

# Run tests
pytest tests/ -v
```


## Project structure

```
SystemMonitor_Configuration_API/
├── protos/                              Proto definitions (6 files)
│   ├── system_monitor_common.proto          Shared enums and messages
│   ├── system_monitor_system.proto          SystemService definitions
│   ├── system_monitor_project.proto         ProjectService definitions
│   ├── system_monitor_parameter.proto       ParameterService definitions
│   ├── system_monitor_logging.proto         LoggingService definitions
│   └── system_monitor_virtual.proto         VirtualService definitions
│
├── sm_config_api/                       Python library package
│   ├── __init__.py                          Public API exports
│   ├── client.py                            SystemMonitorClient facade
│   ├── connection.py                        Connection config and channel
│   ├── enums.py                             14 IntEnum classes
│   ├── errors.py                            40+ exception types + mapping
│   ├── generated/                           Auto-generated gRPC stubs (gitignored)
│   └── services/
│       ├── __init__.py
│       ├── base.py                          BaseService with _call() wrapper
│       ├── system.py                        SystemService (19 RPCs)
│       ├── project.py                       ProjectService (85 RPCs)
│       ├── parameter.py                     ParameterService (60 RPCs)
│       ├── logging_svc.py                   LoggingService (22 RPCs)
│       └── virtual.py                       VirtualService (15 RPCs)
│
├── gui/                                 PySide6 desktop application
│   ├── __init__.py
│   ├── main.py                              Main window, tabs, actions, live watch
│   ├── topology.py                          Custom-painted topology diagram
│   ├── connection_manager.py                Multi-connection store + SMConnection
│   └── workers.py                           QThread workers + CallbackBridge
│
├── scripts/
│   ├── generate_protos.py                   Proto → Python stub compiler
│   └── smoke_test.py                        Quick connectivity test
│
├── tests/                               Test suite (52 tests)
├── docs/                                Documentation
│   ├── CONFIGURATION_API_GUIDE.md
│   ├── gRPC_Technical_Overview.md
│   └── plan.md
├── run_gui.py                           GUI launcher
├── pyproject.toml                       Package metadata and dependencies
├── CONTRIBUTING.md                      This file
└── README.md
```


## How the pieces connect

### 1. Proto → generated stubs

The six `.proto` files in `protos/` define every RPC method, request message,
and response message. Compiling them produces Python modules in
`sm_config_api/generated/`:

```bash
python scripts/generate_protos.py
```

This generates `*_pb2.py` (message classes) and `*_pb2_grpc.py` (stub classes).
**Never edit generated files manually** — they are rebuilt from the protos.

### 2. Generated stub → service wrapper

Each generated stub method is a low-level call. The service wrapper in
`sm_config_api/services/` wraps it with:

- Snake_case method names (PEP 8 style)
- Automatic request message construction
- `return_code` checking → typed exception raising
- Per-call timeout and metadata support

All service classes inherit from `BaseService` (`services/base.py`).

### 3. Service wrapper → client facade

`SystemMonitorClient` (`client.py`) composes all five services and exposes them
as properties: `.system`, `.project`, `.parameter`, `.logging`, `.virtual`.

### 4. Client facade → GUI action

The GUI (`gui/main.py`) calls service methods through the client via a
background `QThread` worker. The `_call()` method on `MainWindow` handles:

- Looking up the selected connection
- Formatting the call name and arguments in the output log
- Running the actual gRPC call in a worker thread
- Displaying the result (success + timing or error message)


## Walkthrough: Adding a new service method

Suppose the System Monitor API adds a new RPC `ResetStatistics` to the
`SystemMonitorSystem` service. Here are the exact steps:

### Step 1 — Add the RPC to the proto file (if not already there)

```protobuf
// protos/system_monitor_system.proto
service SystemMonitorSystem {
    // ... existing RPCs ...

    rpc ResetStatistics (google.protobuf.Empty) returns (ResetStatisticsReply);
}

message ResetStatisticsReply {
    system_monitor_common.ErrorCode return_code = 1;
}
```

### Step 2 — Regenerate stubs

```bash
python scripts/generate_protos.py
```

### Step 3 — Add the Python method to the service wrapper

In `sm_config_api/services/system.py`:

```python
# Locate the existing class and add a new method:

def reset_statistics(self) -> None:
    """Reset all internal statistics counters."""
    self._call(self._stub.ResetStatistics)
```

Key points:
- Method name is `snake_case` (PEP 8)
- Use `self._stub.<RpcName>` to reference the generated stub method
- Pass request arguments as positional args (they map to the proto request fields)
- If the RPC takes no arguments, omit the request — `_call()` defaults to `Empty()`
- If the RPC returns data, annotate the return type (see existing methods for the pattern)
- The `_call()` wrapper automatically checks `return_code` and raises typed exceptions

### Step 4 — Expose through the client facade (if adding a new service property)

If you added a method to an **existing** service, no change is needed in
`client.py` — it's already accessible via `client.system.reset_statistics()`.

If you added a **new service**, add a property to `SystemMonitorClient`:

```python
# sm_config_api/client.py
from sm_config_api.services.my_new_service import MyNewService

class SystemMonitorClient:
    def __init__(self, ...):
        # ... existing init ...
        self._my_new: MyNewService | None = None

    @property
    def my_new(self) -> MyNewService:
        if self._my_new is None:
            raise RuntimeError("Client is closed")
        return self._my_new

    def _connect(self):
        # ... existing ...
        self._my_new = MyNewService(channel, **kw)
```

And register the import in `sm_config_api/__init__.py`.

### Step 5 — Add the UI action button to the GUI

In `gui/main.py`, locate the relevant tab builder (e.g., `_build_tab_system`).

**Simple button with no arguments:**

```python
# Inside _build_tab_system():
g = self._group(layout, "Statistics")
self._action_btn(g, "Reset Statistics", self._call, "system", "reset_statistics")
```

`_action_btn` creates an orange button that:
1. Calls `self._call("system", "reset_statistics")` on click
2. Runs the gRPC call in a background thread (never blocks UI)
3. Logs the call, result, and timing

**Button with an App ID combo box:**

```python
self._action_btn_with_app_combo(
    g, "Get App Errors",
    self._call_hex_arg, "project", "get_errors",
)
```

**Button with an App ID combo + text input:**

```python
self._action_btn_with_app_combo_and_input(
    g, "Get Value Scalar",
    "Param IDs (comma-sep):", "vCar",
    self._call_value_read, "parameter", "get_value_scalar",
)
```

**Custom button with multiple inputs:**

```python
self._action_btn_with_two_inputs(
    g, "Set Value",
    "Param ID:", "vCar",
    "Value:", "0.0",
    self._call_custom, "parameter", "set_value_scalar",
)
```

### Available GUI helpers

| Helper | Signature | Use case |
|--------|-----------|----------|
| `_action_btn(layout, label, callback, *args)` | No extra inputs | Simple calls like `get_status()` |
| `_action_btn_with_input(layout, label, input_label, default, callback, *args)` | One text input | Methods with one string/numeric arg |
| `_action_btn_with_two_inputs(layout, label, lbl1, def1, lbl2, def2, callback, *args)` | Two text inputs | Methods with two string/numeric args |
| `_action_btn_with_app_combo(layout, label, callback, *args)` | App ID combo box | Methods needing `app_id` |
| `_action_btn_with_app_combo_and_input(layout, label, lbl2, def2, callback, *args)` | App ID combo + text input | Methods needing `app_id` + extra args |

All callbacks follow the pattern:
```python
def _call(self, service_name: str, method_name: str, *args):
    # Looks up client → finds service → finds method → runs in QThread
```

### Custom callback patterns

If your method needs special argument handling, follow the existing patterns:

```python
# Pattern for hex/decimal app_id parsing
def _call_hex_arg(self, widget, service_name, method_name, *extra_args):
    val = self._parse_app_id(widget)   # handles combo or text input
    if val is None:
        return
    self._call(service_name, method_name, val, *extra_args)

# Pattern for value reads with param ID list
def _call_value_read(self, combo, edit, service_name, method_name):
    app_id = self._parse_app_id(combo)
    if app_id is None:
        return
    param_ids = [p.strip() for p in edit.text().split(",") if p.strip()]
    if not param_ids:
        self._log_error("No parameter IDs specified")
        return
    self._call(service_name, method_name, app_id, param_ids)
```


## Walkthrough: Adding a new error code

If the proto introduces a new `ErrorCode` value, update three files:

### 1. `sm_config_api/enums.py`

```python
class ErrorCode(IntEnum):
    # ... existing entries ...
    NEW_ERROR_CODE = -42   # match exact value from the proto
```

### 2. `sm_config_api/errors.py`

Add an exception class:
```python
class NewSpecificError(SystemMonitorError):
    """Description of what this error means."""
```

Register it in `_ERROR_CODE_MAP`:
```python
_ERROR_CODE_MAP: dict[ErrorCode, type[SystemMonitorError]] = {
    # ... existing entries ...
    ErrorCode.NEW_ERROR_CODE: NewSpecificError,
}
```

### 3. No GUI changes needed

The existing `BaseService._call()` → `raise_for_error_code()` chain
automatically picks up the new mapping.


## Walkthrough: Adding a completely new tab

To add a new service tab (e.g., "Alarms"):

### 1. Create the builder method in `gui/main.py`

```python
def _build_tab_alarms(self):
    tab = QWidget()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(tab)
    layout = QVBoxLayout(tab)

    g = self._group(layout, "Alarm Management")
    self._action_btn(g, "Get Active Alarms", self._call, "alarm", "get_active_alarms")
    self._action_btn(g, "Clear Alarms", self._call, "alarm", "clear_alarms")

    layout.addStretch()
    self._tabs.addTab(scroll, "🚨 Alarms")
```

### 2. Register the tab in `_build_ui()`

```python
def _build_ui(self):
    # ... existing setup ...
    self._build_tab_system()
    self._build_tab_project()
    self._build_tab_parameters()
    self._build_tab_logging()
    self._build_tab_virtual()
    self._build_tab_alarms()     # <-- add here
    # ...
```


## Code conventions

| Convention | Example |
|------------|---------|
| Method names | `snake_case` matching proto RPC names: `get_status`, `set_online` |
| Service files | `logging_svc.py` avoids shadowing stdlib `logging` module |
| Docstrings | Google-style with `Args:` and `Returns:` sections |
| Type hints | All public methods are fully typed |
| Return types | Return proto objects directly (no premature abstraction) |
| Thread safety | All gRPC calls go through `run_in_thread()` in the GUI |
| Signal connections | Use `Qt.QueuedConnection` for cross-thread signals |
| Error handling | Never catch exceptions silently — log or propagate |
| Imports | `from __future__ import annotations` at the top of all modules |
| Line length | 100 characters (configured in `pyproject.toml`) |


## The `_call()` wrapper — what it does automatically

Every service method goes through `BaseService._call()`, which handles:

1. **Default request**: If you pass no request, it creates `Empty()` for you
2. **Timeout**: Applies the service default or a per-call override
3. **Metadata**: Merges service-level and per-call metadata tuples
4. **Execution**: Calls the gRPC stub method with proper timeout + metadata
5. **gRPC error translation**: `UNAVAILABLE` → `ConnectionFailedError`, etc.
6. **Return code checking**: If the response has a `return_code` field ≠ 0, raises the mapped exception
7. **Logging**: Logs the RPC name and timing at DEBUG level

This means your service methods only need to:
```python
def my_method(self, arg1: int, arg2: str) -> SomeReply:
    request = MyRequest(arg1=arg1, arg2=arg2)
    return self._call(self._stub.MyMethod, request)
```

Everything else — error handling, timeout, logging — is automatic.


## Testing

```bash
# Unit tests (no System Monitor required)
pytest tests/ -v

# Live integration tests (requires running System Monitor on localhost:7000)
SM_LIVE_TEST=1 pytest tests/test_live_integration.py -v

# Quick connectivity check
python scripts/smoke_test.py
python scripts/smoke_test.py --address 10.0.0.1:7000
```

When adding a new service method, add a corresponding test in `tests/`.
Follow the existing patterns in `test_connection.py` and `test_live_integration.py`.


## Pull request checklist

- [ ] Proto definitions are up to date
- [ ] `python scripts/generate_protos.py` has been run
- [ ] New method follows `snake_case` naming
- [ ] Method has a Google-style docstring with `Args:` and `Returns:`
- [ ] Return type is annotated
- [ ] If a new error code was added, `enums.py` and `errors.py` are both updated
- [ ] GUI action button is added in the correct tab
- [ ] GUI action uses `run_in_thread()` and never blocks the UI thread
- [ ] Tested against a live System Monitor instance (or unit test with mock stubs)
- [ ] `pytest tests/ -v` passes

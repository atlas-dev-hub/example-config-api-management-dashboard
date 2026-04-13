# System Monitor Configuration API — Python Client

## Goal

Replicate the C# gRPC test client as a **Pythonic wrapper library** (`sm_config_api`) for the
System Monitor Configuration API. The wrapper must be clean, typed, well-documented and support
**multiple simultaneous connections**. A basic CLI/UI frontend will follow in a later phase.

---

## Source Reference

- **C# client**: `C:\Users\CarlesAbellaBelincho\source\repos\System.Monitor.Configuration.API.Client.Sample\ConfigurationAPIClient`
- **Proto files** (6): `...\Protos\system_monitor_*.proto`
- **gRPC services** (5): `SystemMonitorSystem`, `SystemMonitorProject`, `SystemMonitorParameter`, `SystemMonitorLogging`, `SystemMonitorVirtual`
- **Total RPCs**: ~201

---

## Target Directory Layout

```
SystemMonitor_Configuration_API/
├── pyproject.toml                    # Project metadata + dependencies
├── README.md
├── protos/                           # Copied proto source files
│   ├── system_monitor_common.proto
│   ├── system_monitor_system.proto
│   ├── system_monitor_project.proto
│   ├── system_monitor_parameter.proto
│   ├── system_monitor_logging.proto
│   └── system_monitor_virtual.proto
├── scripts/
│   └── generate_protos.py            # Proto → Python stub generator
├── sm_config_api/
│   ├── __init__.py                   # Package init, version, top-level imports
│   ├── generated/                    # Auto-generated gRPC stubs (gitignored)
│   │   └── __init__.py
│   ├── connection.py                 # ConnectionConfig, channel factory, mTLS + OAuth2
│   ├── client.py                     # SystemMonitorClient facade (composes all services)
│   ├── errors.py                     # Exception hierarchy mapped from ErrorCode enum
│   ├── enums.py                      # Python-friendly enum wrappers (ParameterType, etc.)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseService: common call pattern, error handling
│   │   ├── system.py                 # SystemService  (19 RPCs)
│   │   ├── project.py                # ProjectService (85 RPCs)
│   │   ├── parameter.py              # ParameterService (60 RPCs)
│   │   ├── logging_svc.py            # LoggingService (22 RPCs) — avoid shadowing `logging`
│   │   └── virtual.py                # VirtualService (15 RPCs)
│   └── models/                       # Optional dataclass response models (Phase 2)
│       └── __init__.py
└── tests/
    ├── __init__.py
    ├── conftest.py                   # Shared fixtures
    └── test_connection.py            # Connection & basic smoke tests
```

---

## Implementation Steps

### Step 1 — Project Scaffolding & Proto Compilation

- Create `pyproject.toml` with dependencies: `grpcio`, `grpcio-tools`, `protobuf`, `cryptography`
- Copy the 6 `.proto` files into `protos/`
- Adjust proto import paths for Python (`Protos/` → `protos/`)
- Write `scripts/generate_protos.py` to compile protos → `sm_config_api/generated/`
- Run the generator, verify stubs are created
- Create `sm_config_api/__init__.py` and `sm_config_api/generated/__init__.py`

### Step 2 — Enums & Error Handling

- `sm_config_api/enums.py`: Python `IntEnum` wrappers for all 13 proto enums
  (`ErrorCode`, `FileType`, `ParameterType`, `ConversionType`, `DataType`,
  `ByteOrder`, `BufferType`, `Reason`, `EventPriority`, `ErrorStatus`,
  `TriggerType`, `TriggerOperator`, `LoggingType`, `LinkStatus`)
- `sm_config_api/errors.py`: Exception hierarchy
  - `SystemMonitorError` (base, carries `ErrorCode`)
  - Subclasses: `NoProjectError`, `NoLicenceError`, `NoEcuError`,
    `InvalidFileError`, `ParameterNotFoundError`, `ParameterReadOnlyError`, etc.
  - `raise_for_error_code(code)` helper — auto-maps code → exception

### Step 3 — Connection Management

- `sm_config_api/connection.py`:
  - `ConnectionConfig` dataclass: address, certificate path, key path,
    optional OAuth2 fields (token_uri, client_id, client_secret, audience)
  - `create_channel(config) → grpc.Channel` — builds mTLS channel
  - `TokenManager` class — acquires/caches/refreshes OAuth2 bearer tokens
  - `AuthMetadataPlugin` — injects bearer token into gRPC metadata
  - Support for both secure (TLS) and insecure channels

### Step 4 — Base Service Pattern

- `sm_config_api/services/base.py`:
  - `BaseService.__init__(channel, metadata)` — stores channel + auth metadata
  - `_call(stub_method, request, **kwargs)` — wraps gRPC call with:
    - metadata injection
    - `grpc.RpcError` → `SystemMonitorError` translation
    - optional error-code checking on response's `return_code`
    - timing/logging support
  - All service classes inherit from `BaseService`

### Step 5 — SystemService (19 RPCs)

- `sm_config_api/services/system.py`
- Methods: `get_status()`, `set_online(state)`, `set_live_update(state, action)`,
  `get_unit_list()`, `get_unit_name()`, `get_unit_by_index(index)`,
  `set_unit_by_index(index, primary)`, `get_multi_application_bases()`,
  `get_multi_application_base()`, `set_multi_application_base(name)`,
  `get_licence_details()`, `get_device_properties()`, `get_live_logging()`,
  `set_live_logging(state)`, `set_batch_mode(mode)`, `send_message(app_id, messages, ...)`,
  `get_log_folder()`, `get_ppo_file_name()`, `create_pgv(...)`
- Pythonic return types (named tuples or dataclasses)

### Step 6 — ProjectService (85 RPCs)

- `sm_config_api/services/project.py`
- All project management, DTV, CAN config, MATLAB, PUL, events, errors RPCs
- Group logically: project lifecycle, DTV ops, app management, CAN config,
  MATLAB, file ops, slot management, events/errors, enhanced row

### Step 7 — ParameterService (60 RPCs)

- `sm_config_api/services/parameter.py`
- Parameter metadata, conversions, values (get/set for all types),
  DTV value access, warning limits, input signals

### Step 8 — LoggingService (22 RPCs)

- `sm_config_api/services/logging_svc.py`
- Channel properties, triggers, wrap/offset, session details,
  config download/upload, parameter management, slots

### Step 9 — VirtualService (15 RPCs)

- `sm_config_api/services/virtual.py`
- Virtual parameter CRUD, groups, import/export, data type changes

### Step 10 — Client Facade

- `sm_config_api/client.py`:
  - `SystemMonitorClient(config: ConnectionConfig)`
  - Properties: `.system`, `.project`, `.parameter`, `.logging`, `.virtual`
  - Context manager (`__enter__` / `__exit__`) for channel lifecycle
  - `close()` method

### Step 11 — Tests & Validation

- Unit tests with `grpcio-testing` or mock stubs
- Integration smoke test against a live server (guarded by env var)
- Test connection config, error mapping, enum coverage

### Step 12 — PySide6 GUI Frontend

- `gui/` package at project root
- **Multi-connection manager** (left sidebar):
  - Add/remove SM connections (address, name, TLS settings)
  - Auto-probe TLS certificates (reuse `fetch_server_cert` pattern)
  - Status indicators per connection: green/red boxes for Link, Online, Live Update
  - Real-time polling via `QTimer` (every 2s) on background `QThread`
  - Select a connection to view its details panel
- **Main area** (right side, tabbed — inspired by tkinter reference `gui.py`):
  - 🔌 System — status, online/live control, units, licence, device properties
  - 📁 Project — open/close/save, DTV, app management, import/export
  - 📱 Applications — list, add/remove, details, program version
  - 📊 Parameters — list, properties, get/set values, warnings, conversions
  - 📅 Data Version — read/write DTV info, comment, notes, save increment
  - 📝 Logging — config, triggers, enable/disable
  - 🔧 Virtual — virtual parameter CRUD, groups, import/export
- **Output log** (bottom panel):
  - Dark-themed scrollable log with colour-coded entries (call, success, error)
  - Timestamp, method name, duration, result preview
- **Architecture**:
  - `QThread` workers for gRPC calls — never block the UI thread
  - Signal/slot pattern: worker emits result → UI updates
  - Each connection holds its own `Connection` + all 5 service wrappers
  - Connection persistence via JSON settings file
- **Reference**: `C:\Users\CarlesAbellaBelincho\PycharmProjects\SMpyToolboxApplied\gui.py`
  (tkinter ActiveX wrapper — same tab structure, action-card pattern with Run buttons)

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sync vs Async | Sync first, async later | Matches C# reference; simpler to start |
| Response types | Return proto objects initially | Avoid premature abstraction; add models in Phase 2 |
| Error handling | Exception hierarchy + `raise_for_error_code` | Pythonic; callers can catch specific errors |
| Auth | mTLS + optional OAuth2 bearer | Matches C# client exactly |
| Naming | `snake_case` methods matching proto RPC names | PEP 8 + intuitive mapping |
| File: `logging_svc.py` | Avoids `logging.py` | Prevents shadowing stdlib `logging` module |

---

## Dependencies

```
grpcio >= 1.62
grpcio-tools >= 1.62
protobuf >= 5.26
cryptography >= 42.0
requests >= 2.31       # For OAuth2 token acquisition (replaces RestSharp)
pytest >= 8.0          # Dev dependency
```

---

## Phase 2 (Future — after wrapper is solid)

- Pydantic/dataclass response models with type-safe access
- Async gRPC support (`grpc.aio`)
- Connection pooling and health checks

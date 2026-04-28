# System Monitor Configuration API -- Technical Guide

Version: 1.0
Applies to: System Monitor v8.85 and later


## 1. Overview

The System Monitor Configuration API is a remote procedure call (RPC) interface
that enables external applications to interact with Motion Applied System
Monitor instances over a network. It replaces the legacy ActiveX/COM automation
interface with a modern, language-neutral, transport-efficient protocol based on
gRPC and Protocol Buffers.

The API provides full programmatic access to System Monitor functionality
including connection management, application enumeration, parameter reading and
writing, data logging configuration, and virtual parameter management.

Key characteristics:

- Transport protocol: gRPC over HTTP/2
- Serialisation format: Protocol Buffers (protobuf) version 3
- Authentication: mutual TLS (mTLS), with optional OAuth2 bearer tokens
- Default port: 7000 (configurable in System Monitor settings)
- Supported languages: any language with gRPC support (C#, Python, C++, Java, Go, etc.)


## 2. Architecture

### 2.1 Communication Model

The Configuration API follows a client-server architecture. System Monitor acts
as the gRPC server, exposing services on a configured TCP port. Client
applications connect to this endpoint using generated stub code derived from the
proto service definitions.

```
+------------------+          gRPC / HTTP/2          +-------------------+
|                  |  <---------------------------->  |                   |
|  Client          |       TLS-encrypted channel      |  System Monitor   |
|  Application     |                                  |  (gRPC Server)    |
|                  |  Request (protobuf) ---------->  |                   |
|                  |  <---------- Response (protobuf) |  Port 7000        |
+------------------+                                  +-------------------+
                                                             |
                                                      +------+------+
                                                      |  TAG Device |
                                                      |  (ECU/Unit) |
                                                      +-------------+
```

All communication is synchronous request-response (unary RPCs), with the
exception of certain streaming endpoints for bulk data retrieval. The gRPC
channel multiplexes multiple concurrent RPC calls over a single TCP connection.

### 2.2 Service Decomposition

The API is organised into five logical services, each defined in its own proto
file with a shared common definitions file:

| Proto File                       | Service Name                  | Purpose                                |
|----------------------------------|-------------------------------|----------------------------------------|
| system_monitor_common.proto      | (none -- shared types)        | Common message types and enumerations  |
| system_monitor_system.proto      | SystemMonitorSystem           | Connection lifecycle and status        |
| system_monitor_project.proto     | SystemMonitorProject          | Project and application management     |
| system_monitor_parameter.proto   | SystemMonitorParameter        | Parameter access and calibration       |
| system_monitor_logging.proto     | SystemMonitorLogging          | Data logging configuration             |
| system_monitor_virtual.proto     | SystemMonitorVirtual          | Virtual parameter definitions          |

### 2.3 Shared Message Types

The `system_monitor_common.proto` file defines message types and enumerations
used across multiple services:

**Request messages:**
- `AppRequest` -- identifies an application by numeric ID
- `FileRequest` -- identifies a file by application ID and file path
- `ParametersRequest` -- requests parameters for an application and type filter
- `AppParametersRequest` -- requests specific parameters by ID within an application
- `ParameterRequest` -- requests a single parameter by application and parameter ID
- `ConversionRequest` -- requests conversion data for an application

**Response types:**
- `Return` -- standard return envelope containing an error code

**Enumerations:**
- `ErrorCode` -- numeric error codes (0 = success, negative values = errors)
- `LinkStatus` -- LINK_OK (0), LINK_NOK (1)
- `ErrorStatus` -- error severity levels
- `EventPriority` -- event priority classification
- `Reason` -- trigger and event reason codes
- Additional enumerations for data types, byte orders, buffer types, etc.


## 3. Service Reference

### 3.1 SystemMonitorSystem (19 RPCs)

Manages the connection lifecycle and provides system-level information.

**Status and Control:**
- `GetStatus` -- returns link status, online state, and live update state
- `SetOnline` / `SetLiveUpdate` -- control the System Monitor operational mode
- `GetLinkStatus` -- returns the current link status to the connected unit

**Unit Information:**
- `GetUnitList` -- enumerates all units visible on the network
- `GetUnitName` -- returns the name of the currently connected unit
- `GetDeviceProperties` -- returns device communication paths, names, and addresses

**System Metadata:**
- `GetLicenceDetails` -- returns consortium and owner from the licence
- `GetLogFolder` -- returns the active log storage directory
- `GetPpoFileName` -- returns the loaded PPO file path

**File Operations:**
- `GetFile` / `SetFile` -- read and write files on the connected unit
- `GetFileList` -- list files available on the unit

### 3.2 SystemMonitorProject (85 RPCs)

The largest service, providing access to project structure, application
management, version control, error and event retrieval, and file operations.

**Application Management:**
- `GetAppDetails` -- returns all applications with their numeric IDs and names
- `GetActiveApps` -- returns IDs of currently active applications
- `GetAppNames` -- returns application names by ID

**Version Information:**
- `GetVersionNumber` -- returns System Monitor major.minor.build version
- `GetBuildNumber` -- returns the build number
- `GetDtvVersion` / `GetDtvComment` / `GetDtvNotes` -- DTV file metadata per application
- `GetPgvVersion` -- PGV file version per application

**Error and Event Management:**
- `GetErrors` / `GetEvents` -- retrieve current errors and events
- `GetErrorDetails` / `GetEventDetails` -- detailed information per item
- `ClearErrors` / `ClearEvents` -- acknowledge and clear

**File Operations:**
- `SetDtvFile` / `SetPgvFile` -- load configuration files
- `GetDtvFileList` / `GetPgvFileList` -- enumerate available files
- Additional RPCs for map files, calibration files, and configuration export/import

### 3.3 SystemMonitorParameter (60 RPCs)

Provides access to parameter metadata, live values, conversions, and calibration
write-back.

**Parameter Enumeration:**
- `GetParameters` -- returns all parameters for an application, filterable by type
- `GetParameterProperties` -- returns full metadata (type, group, units, range)
- `GetParameterAndGroups` -- returns parameters organised by group hierarchy
- `GetModifiedParameters` -- returns parameters with unsaved calibration changes

**Value Reading:**
- `GetValueScalar` -- reads current scalar values for a list of parameter IDs
- `GetValueMeasurement` -- reads measurement values with units and status
- `GetValueString` -- reads string-type parameter values
- `GetValue1d` / `GetValue2d` -- reads one-dimensional and two-dimensional map data
- `GetValueBitField` -- reads bit-field parameter values

**Calibration (Value Writing):**
- `SetValueScalar` / `SetValueString` / `SetValue1d` / `SetValue2d`
- `SetValueBitField` -- write values to the edit buffer or unit buffer
- `SendToUnit` / `GetFromUnit` -- transfer calibration data between buffers
- `DeleteMinMax` -- reset min/max recorded values

**Conversions:**
- `GetConversions` -- returns all conversion definitions for an application
- `GetConversionDetails` -- returns the full conversion specification (rational,
  table, text, or formula)

### 3.4 SystemMonitorLogging (22 RPCs)

Controls the data logging subsystem, including channel configuration and trigger
management.

**Configuration:**
- `GetLoggingConfig` -- returns the current logging configuration
- `SetLoggingConfig` -- applies a new logging configuration
- `GetLoggingChannels` -- enumerates configured logging channels
- `GetLoggingChannelDetails` -- returns parameters, rates, and triggers for a channel

**Trigger Management:**
- `GetLoggingTriggers` -- lists all configured triggers
- `GetLoggingTriggerDetails` -- returns trigger conditions and parameters
- `SetLoggingTrigger` / `DeleteLoggingTrigger` -- create, update, and remove triggers

**Control:**
- `StartLogging` / `StopLogging` -- begin and end a logging session

### 3.5 SystemMonitorVirtual (15 RPCs)

Manages virtual (computed) parameters that exist only within System Monitor and
are derived from physical parameters through mathematical expressions.

- `GetVirtualParameters` -- lists virtual parameters for an application
- `GetVirtualParameterDetails` -- returns the expression, inputs, and data type
- `SetVirtualParameter` / `DeleteVirtualParameter` -- create, update, remove
- `GetVirtualParameterDataTypes` -- available data types for virtual parameters


## 4. Protocol Buffer Definitions

### 4.1 Proto File Structure

All service definitions use Protocol Buffers version 3 syntax. The six proto
files follow a consistent structure:

```protobuf
syntax = "proto3";
package <package_name>;
import "system_monitor_common.proto";

service <ServiceName> {
    rpc MethodName (RequestMessage) returns (ResponseMessage);
    ...
}

message RequestMessage { ... }
message ResponseMessage { ... }
```

### 4.2 Error Handling Convention

Most response messages include a `return_code` field of type
`system_monitor_common.ErrorCode`. The value 0 indicates success; negative
values indicate specific error conditions:

| Code  | Name                    | Description                            |
|-------|-------------------------|----------------------------------------|
| 0     | NO_ERROR                | Operation completed successfully       |
| -1    | COMMS_FAILURE           | Communication with unit failed         |
| -2    | UNIT_NOT_FOUND          | Specified unit does not exist           |
| -3    | FILE_NOT_FOUND          | Specified file does not exist           |
| -4    | INVALID_PARAMETER       | Parameter ID is invalid                |
| -5    | INVALID_VALUE           | Value is out of range or wrong type    |
| -6    | NOT_SUPPORTED           | Operation not supported in this mode   |
| -7    | BUSY                    | System Monitor is busy                 |
| -8    | NOT_CONNECTED           | No unit is connected                   |
| -9    | NO_APPLICATION          | Application ID does not exist          |
| -10   | APPLICATION_INACTIVE    | Application exists but is not active   |
| -100  | PARAMETER_NOT_FOUND     | Parameter not found in application     |

The Python wrapper library automatically checks return codes and raises typed
exceptions from the `sm_config_api.errors` module.

### 4.3 Application Identifiers

Applications are identified by numeric IDs. These are unsigned 32-bit integers
that correspond to the application slot in the TAG unit firmware. Common
examples from a TAG-700 configuration:

| App ID | Hex    | Name         |
|--------|--------|--------------|
| 3840   | 0x0F00 | BIOS         |
| 3841   | 0x0F01 | FIA          |
| 3842   | 0x0F02 | Chassis      |
| 3843   | 0x0F03 | Arbitrator   |
| 3844   | 0x0F04 | Coordinator  |
| 3845   | 0x0F05 | Controller   |
| 3846   | 0x0F06 | Dash         |
| 3847   | 0x0F07 | BrakeControl |

Application IDs are obtained dynamically at runtime using `GetAppDetails` or
`GetActiveApps`. Hard-coding IDs is not recommended as they vary between
configurations.


## 5. Authentication and Transport Security

### 5.1 TLS (Default)

System Monitor serves the Configuration API over TLS by default. The server
generates a self-signed certificate on first run, typically with CN=localhost.

The Python client library handles TLS connections through automatic certificate
probing. When no explicit certificate is provided, the client performs the
following steps at connection time:

1. Opens a raw SSL socket to the server address.
2. Retrieves the server's TLS certificate (DER format).
3. Converts the certificate to PEM format and uses it as the trusted CA root.
4. Extracts the Common Name (CN) from the certificate subject.
5. Sets the gRPC option `ssl_target_name_override` to the extracted CN so that
   hostname verification succeeds regardless of whether the connection address
   is a hostname or IP address.

This process is fully automatic and requires no configuration on the client
side. It works with:

- The default self-signed certificate generated by System Monitor (CN=localhost)
- Custom PFX certificates installed on the System Monitor host
- CA-signed certificates with any CN or Subject Alternative Names

Example: connecting to a remote System Monitor instance at `10.0.0.50:5001`
where the server certificate has CN=localhost:

```python
config = ConnectionConfig(address="10.0.0.50:5001")

with SystemMonitorClient(config) as client:
    status = client.system.get_status()
```

No additional certificate files or configuration are needed. The library probes
the certificate from `10.0.0.50:5001`, extracts CN=localhost, and applies the
hostname override automatically.

### 5.2 Installing a TLS Certificate on System Monitor

System Monitor accepts PFX/PKCS#12 certificate files for its gRPC API endpoint.
To install a custom certificate:

1. Obtain or generate a PFX certificate file (e.g., `localhost.pfx`).
2. Place the PFX file on the System Monitor host machine.
3. Configure System Monitor to use the certificate by specifying the file path
   and password in the System Monitor settings.
4. Restart the System Monitor Configuration API service.

Generating a self-signed PFX certificate (PowerShell, run on the SM host):

```powershell
$cert = New-SelfSignedCertificate `
    -DnsName "localhost" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears(1)

$password = ConvertTo-SecureString -String "YourPassword" -Force -AsPlainText

Export-PfxCertificate `
    -Cert $cert `
    -FilePath "C:\path\to\localhost.pfx" `
    -Password $password
```

After installing the certificate on the server, no changes are required on the
client side. The automatic certificate probing adapts to whatever certificate
the server presents.

### 5.3 Mutual TLS (mTLS)

For authenticated connections, both the client and server present certificates:

```
Client                              Server
  |---- ClientHello + cert -------->|
  |<--- ServerHello + cert ---------|
  |---- Verify server cert          |
  |                    Verify client cert ----|
  |<--- Encrypted channel ----------|
```

Client certificates can be provided as:
- PEM files (separate certificate and key files)
- PFX/PKCS#12 bundles (single file with password, compatible with C# client)

```python
# PFX client certificate
config = ConnectionConfig(
    address="hostname:7000",
    pfx_path="path/to/client.pfx",
    pfx_password="password",
    ca_cert="path/to/ca.pem",
)

# PEM client certificate
config = ConnectionConfig(
    address="hostname:7000",
    client_cert="path/to/client.pem",
    client_key="path/to/client-key.pem",
    ca_cert="path/to/ca.pem",
)
```

### 5.4 OAuth2 Bearer Tokens

For cloud or enterprise deployments, the API supports OAuth2 client_credentials
flow. The client obtains an access token from an identity provider and attaches
it to each gRPC call as a bearer token in the request metadata.

Token refresh is handled automatically by the `TokenManager` class, which
re-authenticates before the current token expires.

```python
config = ConnectionConfig(
    address="hostname:7000",
    ca_cert="path/to/ca.pem",
    use_token=True,
    client_id="my-client-id",
    client_secret="my-client-secret",
    token_uri="https://auth-server/oauth/token",
    audience="system-monitor-api",
)
```


## 6. Python Wrapper Implementation

### 6.1 Code Generation

The Python gRPC stubs are generated from the proto definitions using the
`grpcio-tools` package. The generation script (`scripts/generate_protos.py`)
performs two steps:

1. Invokes `grpc_tools.protoc` to compile all six proto files into Python
   modules (message classes, stub classes, and servicer base classes).

2. Fixes relative imports in the generated code. The protoc compiler generates
   absolute imports (e.g., `import system_monitor_common_pb2`) which do not
   work when the generated files are inside a Python package. The script
   rewrites these to relative imports (e.g., `from . import
   system_monitor_common_pb2`).

The generated files are placed in `sm_config_api/generated/` and should not be
edited manually. They are excluded from version control via `.gitignore`.

To regenerate after proto file changes:

```bash
python scripts/generate_protos.py
```

### 6.2 Service Wrapper Pattern

Each gRPC service is wrapped by a Python class that inherits from `BaseService`.
The wrapper provides:

- Pythonic method names (snake_case instead of PascalCase)
- Automatic request message construction from method arguments
- Return code checking with typed exception raising
- Configurable timeout with per-call override support
- Structured logging of all RPC calls with timing information

Example of the wrapping pattern:

```python
# Generated stub call (low-level):
stub = SystemMonitorSystemStub(channel)
request = google.protobuf.empty_pb2.Empty()
response = stub.GetStatus(request, timeout=5.0)

# Wrapper call (high-level):
client.system.get_status()  # returns the StatusReply protobuf message
```

The `BaseService._call()` method handles the common logic:

1. Constructs the request message if arguments are provided
2. Invokes the stub method with the configured timeout
3. Checks `response.return_code` if the field exists
4. Raises a typed exception from `sm_config_api.errors` if the code is non-zero
5. Returns the response protobuf message

### 6.3 Client Facade

The `SystemMonitorClient` class provides a single entry point that composes all
five services:

```python
from sm_config_api import SystemMonitorClient, ConnectionConfig

config = ConnectionConfig(address="localhost:7000")
client = SystemMonitorClient(config, timeout=5.0)

client.system    # SystemService instance
client.project   # ProjectService instance
client.parameter # ParameterService instance
client.logging   # LoggingService instance
client.virtual   # VirtualService instance

client.close()   # or use as a context manager
```

The client manages the gRPC channel lifecycle. When used as a context manager,
the channel is closed automatically on exit. The client also supports
`reconnect()` to re-establish the channel after a connection loss.

### 6.4 Error Handling

The library defines a two-level error hierarchy:

**Transport-level errors** (gRPC failures):
- `GrpcError` -- base class for all gRPC transport errors
- `ConnectionFailedError` -- server unreachable (gRPC UNAVAILABLE)
- `TimeoutError` -- RPC deadline exceeded (gRPC DEADLINE_EXCEEDED)
- `AuthenticationError` -- credential rejection (gRPC UNAUTHENTICATED)

**Application-level errors** (non-zero return codes):
- `SystemMonitorError` -- base class for all API error codes
- 40+ specific subclasses mapped from `ErrorCode` values
- Examples: `NoApplicationError`, `ParameterNotFoundError`,
  `CommsFailureError`, `FileNotFoundError`

```python
from sm_config_api.errors import NoApplicationError

try:
    version = client.project.get_dtv_version(app_id=99999)
except NoApplicationError:
    print("Application does not exist")
```

### 6.5 Enumeration Types

The library provides 14 Python `IntEnum` classes that mirror the protobuf
enumerations. These allow symbolic comparison and display of status values:

```python
from sm_config_api.enums import LinkStatus, ParameterType

status = client.system.get_status()
if LinkStatus(status.link_status) == LinkStatus.LINK_OK:
    print("Link is established")
```

Key enumerations:
- `LinkStatus` -- LINK_OK (0), LINK_NOK (1)
- `ErrorCode` -- NO_ERROR (0), COMMS_FAILURE (-1), ... PARAMETER_NOT_FOUND (-100)
- `ParameterType` -- SCALAR, MEASUREMENT, STRING, MAP_1D, MAP_2D, BIT_FIELD, etc.
- `ConversionType` -- RATIONAL (0), TABLE (1), TEXT (2), FORMULA (3)
- `BufferType` -- UNIT_BUFFER (0), EDIT_BUFFER (1), UNIT_AND_EDIT_BUFFER (2)


## 7. Setup Walkthrough

This section provides a step-by-step guide to setting up the Python client from
a clean environment.

### Step 1: Obtain the Proto Files

The proto files define the gRPC service contracts. They can be obtained from:

- The C# sample client repository:
  `System.Monitor.Configuration.API.Client.Sample/ConfigurationAPIClient/Protos/`
- The NuGet package `SystemMonitorConfigurationAPI` (requires Motion Applied
  SSO credentials)

Copy all six `.proto` files into the `protos/` directory:

```
protos/
    system_monitor_common.proto
    system_monitor_system.proto
    system_monitor_project.proto
    system_monitor_parameter.proto
    system_monitor_logging.proto
    system_monitor_virtual.proto
```

### Step 2: Fix Proto Import Paths

The proto files from the C# repository use import paths prefixed with `Protos/`:

```protobuf
import "Protos/system_monitor_common.proto";
```

For flat-directory compilation, these must be changed to:

```protobuf
import "system_monitor_common.proto";
```

Apply this change in all five service proto files (the common file has no
imports).

### Step 3: Install Dependencies

```bash
pip install grpcio grpcio-tools protobuf cryptography requests
```

For GUI support, also install:

```bash
pip install PySide6
```

### Step 4: Generate Python Stubs

Run the generation script:

```bash
python scripts/generate_protos.py
```

This produces 18 files in `sm_config_api/generated/`:
- `*_pb2.py` -- message classes
- `*_pb2.pyi` -- type stubs for IDE support
- `*_pb2_grpc.py` -- client stubs and server base classes

The script automatically fixes relative imports so the generated code works as
part of the `sm_config_api` package.

### Step 5: Configure System Monitor

Ensure the Configuration API is enabled in System Monitor:

1. Open System Monitor (version 8.85 or later)
2. Verify the API port in System Monitor settings (default: 7000)
3. Ensure the firewall allows inbound TCP on the configured port
4. For remote connections, ensure the System Monitor host is reachable from the
   client machine

### Step 6: Verify Connectivity

Run the smoke test to verify the connection:

```bash
python scripts/smoke_test.py
```

For a non-default address:

```bash
python scripts/smoke_test.py --address 10.0.0.1:7000
```

Expected output for a successful connection:

```
Probing TLS certificate from localhost:7000...
Got server certificate (CN=localhost)
Creating TLS channel to localhost:7000...
Calling GetStatus...
  online=True, live_update=True, link_status=0
Calling GetUnitList...
  1 unit(s) found
Connection test PASSED
```

### Step 7: Use the Library

At this point the library is ready for use. Refer to the Quick Start section in
the README or the service reference in Section 3 of this document for the
available methods.


## 8. Network and Firewall Considerations

The Configuration API requires a direct TCP connection between the client and
the System Monitor host on the configured port. This section covers common
deployment scenarios and troubleshooting steps.

### 8.1 Local Connections

Connecting to a System Monitor instance on the same machine (localhost:7000)
typically works without any additional configuration. The server binds to all
network interfaces by default.

```python
config = ConnectionConfig(address="localhost:7000")
```

### 8.2 Remote Connections

For remote connections, two conditions must be met:

1. The API port must be open on the System Monitor host firewall.
2. The network path between client and server must permit TCP traffic on that
   port.

To open the port on the System Monitor host (Windows, run as Administrator):

```powershell
New-NetFirewallRule -DisplayName "System Monitor API" `
    -Direction Inbound -Protocol TCP -LocalPort 7000 -Action Allow
```

### 8.3 Corporate Networks and VPNs

Corporate firewalls commonly restrict traffic to a small set of permitted ports.
If the default port (7000) is blocked:

1. Verify basic host reachability:
   ```powershell
   Test-Connection <host>
   ```

2. Test the specific port:
   ```powershell
   $tcp = New-Object System.Net.Sockets.TcpClient
   $tcp.Connect("<host>", 7000)
   $tcp.Close()
   ```

3. If the port is blocked, options include:
   - Request a firewall rule from IT for the required port
   - Change the System Monitor API port to one that is permitted (configure in
     System Monitor settings, then connect using the new port)
   - Run the client application directly on the System Monitor host

To identify which ports are permitted, start a TCP listener on the remote host
and test from the client:

```powershell
# On the remote host -- start a listener on a candidate port
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, 5001)
$listener.Start()
Write-Host "Listening on 5001..."
# Then test from the client machine
# Stop with: $listener.Stop()
```

### 8.4 TLS and Hostname Verification

gRPC enforces TLS hostname verification by default. The hostname in the
connection address must match the Common Name (CN) or a Subject Alternative
Name (SAN) in the server certificate.

When using the automatic certificate probing feature, the library handles this
transparently by extracting the CN from the probed certificate and applying
`grpc.ssl_target_name_override`. This means:

- Connecting to `localhost:7000` with a CN=localhost certificate works.
- Connecting to `10.0.0.50:5001` with a CN=localhost certificate also works.
- Connecting to `my-server.local:7000` with a CN=my-server.local certificate
  works.

No manual hostname override configuration is required when using the library's
default connection flow.

If providing certificates explicitly (without auto-probing), ensure that either:
- The connection address hostname matches the certificate CN/SAN, or
- The `grpc.ssl_target_name_override` option is set manually:

```python
config = ConnectionConfig(
    address="10.0.0.50:7000",
    ca_cert="path/to/server-cert.pem",
    options=[("grpc.ssl_target_name_override", "localhost")],
)
```


## 9. Comparison with the ActiveX/COM Interface

The Configuration API replaces the legacy System Monitor ActiveX/COM automation
interface. Key differences:

| Aspect               | ActiveX/COM                    | Configuration API (gRPC)       |
|----------------------|--------------------------------|--------------------------------|
| Protocol             | COM/DCOM (Windows only)        | gRPC/HTTP/2 (cross-platform)   |
| Language support     | COM-compatible languages       | Any language with gRPC support |
| Network              | DCOM (complex, often blocked)  | Standard TCP port              |
| Authentication       | Windows integrated             | TLS, mTLS, OAuth2              |
| Serialisation        | COM variant types              | Protocol Buffers (compact)     |
| Performance          | Single-threaded apartment      | Multiplexed HTTP/2 streams     |
| Deployment           | Requires COM registration      | No registration required       |
| Multiple connections | One instance per process       | Multiple channels per process  |

The gRPC API provides the same functional coverage as the ActiveX interface
while eliminating the Windows-only dependency and COM configuration complexity.


## 10. Revision History

| Version | Date       | Description                                    |
|---------|------------|------------------------------------------------|
| 1.0     | 2026-04-10 | Initial release -- all five services documented |
| 1.1     | 2026-04-10 | TLS auto-probe CN extraction, PFX setup guide, expanded network troubleshooting |

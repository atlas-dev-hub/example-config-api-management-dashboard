# gRPC — Technical Overview

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT APPLICATION                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │  Python  │  │   Java   │  │    Go    │  │       C# / …      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────────┬──────────┘  │
│       │              │              │                  │            │
│       └──────────────┴──────────────┴──────────────────┘            │
│                          │                                          │
│               Generated Stubs (from .proto)                         │
│                          │                                          │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │      Protobuf Wire      │
              │   (binary serialised)   │
              └────────────┬────────────┘
                           │
              ┌────────────┴────────────┐
              │        HTTP/2           │
              │  ┌───────────────────┐  │
              │  │   Single TCP      │  │
              │  │   Connection      │  │
              │  └───┬───┬───┬───┬───┘  │
              │   R1  R2  R3  R4  …     │  ← multiplexed streams
              │                         │
              │    TLS (encrypted)      │
              └────────────┬────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────────┐
│               Generated Stubs (from .proto)                         │
│                          │                                          │
│       ┌──────────────────┼──────────────────┐                      │
│  ┌────┴─────┐       ┌────┴─────┐       ┌────┴─────┐                │
│  │ Service  │       │ Service  │       │ Service  │  …             │
│  │   A      │       │   B      │       │   C      │                │
│  └──────────┘       └──────────┘       └──────────┘                │
│                        gRPC SERVER                                  │
└─────────────────────────────────────────────────────────────────────┘
```


## What is gRPC

**gRPC** (gRPC Remote Procedure Call) is a modern, high-performance communication
protocol that allows software services to talk to each other. It is mainly used
in distributed systems and microservice architectures, where many services need
fast, reliable, and well-defined communication.

At its core, gRPC lets you call a method on a remote server as if it were a
local function. The transport, serialisation, error handling, and deadlines are
all handled by the framework.


## What is Protobuf (Protocol Buffers)

**Protobuf** is a language-neutral, binary data format used by gRPC to define
APIs and exchange data. Instead of sending text (like JSON), Protobuf sends
compact binary messages, which are:

- **Smaller in size** — typically 3× to 10× smaller than equivalent JSON
- **Faster to serialise and parse** — no text parsing overhead
- **Strongly typed** — strict schemas enforced at compile time

With Protobuf, you define your data structures and service methods in `.proto`
files, and code is automatically generated for many programming languages. This
reduces bugs and keeps client and server perfectly in sync.

### Example `.proto` file

```protobuf
syntax = "proto3";

service Greeter {
    rpc SayHello (HelloRequest) returns (HelloReply);
}

message HelloRequest {
    string name = 1;
}

message HelloReply {
    string message = 1;
}
```


## What is HTTP/2

gRPC runs on top of **HTTP/2**, a modern version of HTTP that improves
performance. HTTP/2 provides:

| Feature              | Benefit                                               |
|----------------------|-------------------------------------------------------|
| **Multiplexing**     | Many requests over a single TCP connection            |
| **Header compression** | Reduces overhead on repeated headers                |
| **Binary framing**   | More efficient to parse than text-based HTTP/1.1     |
| **Server push**      | Server can proactively send resources to client       |
| **Bidirectional streaming** | Both client and server can send streams concurrently |

These features make gRPC much faster and more efficient than traditional REST
APIs over HTTP/1.1.

### Connection comparison

```
REST / HTTP/1.1                     gRPC / HTTP/2
───────────────────────────         ───────────────────────────
Connection 1 ──► GET /users         ┌─ GET /users ──────┐
Connection 2 ──► GET /orders        │  Stream 1          │
Connection 3 ──► GET /products      ├─ GET /orders ──────┤   Single
Connection 4 ──► GET /inventory     │  Stream 2          │   TCP
                                    ├─ GET /products ────┤   Connection
  4 TCP connections,                │  Stream 3          │
  4 TLS handshakes                  └─ GET /inventory ───┘
                                        Stream 4

      ↑ overhead                         ↑ efficient
```


## Why gRPC is powerful

gRPC is powerful because it combines:

- **Speed** — binary data over HTTP/2 with persistent connections
- **Strong contracts** — Protobuf schemas guarantee API compatibility
- **Streaming support** — unary, server-streaming, client-streaming, bidirectional
- **Automatic code generation** — stubs for 10+ languages from a single `.proto`
- **Built-in error handling and deadlines** — no need for custom retry/timeout logic

This makes it ideal for real-time systems, data pipelines, cloud services, and
internal APIs.

### gRPC vs REST at a glance

```
          gRPC                          REST
   ┌──────────────────┐          ┌──────────────────┐
   │ Protobuf (binary) │          │ JSON / XML (text) │
   │ HTTP/2             │          │ HTTP/1.1          │
   │ .proto schema      │          │ OpenAPI / Swagger │
   │ Codegen stubs      │          │ Manual clients    │
   │ Bidirectional      │          │ Request/response  │
   │ streaming built-in │          │ only              │
   └──────────────────┘          └──────────────────┘
```


## Why gRPC is widely used in industry

Companies use gRPC because it **scales well**, **enforces API consistency**, and
**performs extremely well under load**. It is heavily used at **Google** and
widely adopted in cloud-native and high-performance systems.

Common use cases:

- **Microservice communication** (Kubernetes, service meshes)
- **Real-time telemetry and monitoring** (IoT, System Monitor)
- **Mobile-to-backend** (low bandwidth, binary efficient)
- **Streaming data pipelines** (logs, events, metrics)
- **Polyglot environments** (teams using different languages)


## Supported languages

gRPC supports many languages, including:

| Language | Status |
|----------|--------|
| C++ | Official (Google) |
| Java | Official (Google) |
| Python | Official (Google) |
| Go | Official (Google) |
| C# / .NET | Official (Google) |
| JavaScript / TypeScript | Official (Google) |
| Kotlin | Official (Google) |
| Swift | Official (Apple) |
| Ruby | Official (Google) |
| PHP | Official (Google) |
| Dart | Official (Google) |
| Rust | Community (tonic) |

This makes it easy for different teams and services to communicate, even when
written in different languages.

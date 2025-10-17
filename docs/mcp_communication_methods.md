# MCP Communication Methods

This document explains the different ways to communicate with MCP (Model Context Protocol) servers and their trade-offs.

## Overview

MCP servers can be run and accessed in several different ways, each with its own advantages and use cases. Understanding these methods helps you choose the right approach for your specific needs.

## Communication Methods

### 1. HTTP Server (Standalone) - Primary Method

**How it works:**
- MCP server runs as standalone HTTP server on port 8001
- Communication via HTTP REST API
- Agents make HTTP requests to the MCP server
- Real-time logging visible in server console

**Implementation:**
```python
# Agent code
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8001/tools/execute",
        json={
            "tool_name": "telecom.graphql.run",
            "arguments": {"query": query, "variables": variables}
        }
    )
    result = response.json()
```

**Pros:**
- ✅ Real-time logging visible in console
- ✅ Easy to debug and monitor
- ✅ Scalable and production-ready
- ✅ Standard HTTP communication
- ✅ Can be load balanced
- ✅ Works across network boundaries

**Cons:**
- ❌ Requires network setup
- ❌ Slightly more complex than stdio

**Use Case:** Production, development, and debugging

---

### 2. Stdio (Subprocess) - Legacy Support

**How it works:**
- MCP server runs as a subprocess
- Communication via stdin/stdout
- Agent spawns the server process and communicates through pipes

**Implementation:**
```python
# Agent code
process = subprocess.Popen(
    [sys.executable, "mcp_server/server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Send request
process.stdin.write(json.dumps(request) + "\n")
response = process.stdout.readline()
```

**Pros:**
- ✅ Simple to implement
- ✅ No network setup required
- ✅ Process isolation
- ✅ Works on all platforms

**Cons:**
- ❌ Logs not visible in main console
- ❌ Harder to debug
- ❌ Limited scalability
- ❌ No real-time monitoring

**Use Case:** Legacy support and simple applications

---

### 3. Named Pipes/Unix Sockets

**How it works:**
- Communication via named pipes or Unix domain sockets
- More efficient than stdio
- Better for high-throughput applications

**Implementation:**
```python
# Server code
import socket
server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server_socket.bind("/tmp/mcp_server.sock")

# Client code
client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
client_socket.connect("/tmp/mcp_server.sock")
```

**Pros:**
- ✅ More efficient than stdio
- ✅ Better for high-throughput
- ✅ Process isolation
- ✅ Lower latency

**Cons:**
- ❌ Platform-specific (Unix-like systems only)
- ❌ More complex setup
- ❌ File system permissions required

**Use Case:** High-performance applications

---

### 4. WebSocket Connection

**How it works:**
- Real-time bidirectional communication
- Good for interactive applications
- Supports streaming responses

**Implementation:**
```python
# Server code (WebSocket)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        # Process request
        await websocket.send_text(response)

# Client code
async with websockets.connect("ws://localhost:8001/ws") as websocket:
    await websocket.send(json.dumps(request))
    response = await websocket.recv()
```

**Pros:**
- ✅ Real-time communication
- ✅ Bidirectional data flow
- ✅ Good for interactive apps
- ✅ Supports streaming

**Cons:**
- ❌ More complex protocol
- ❌ Connection management overhead
- ❌ Not suitable for simple requests

**Use Case:** Interactive and real-time applications

## Comparison Table

| Method | Complexity | Performance | Debugging | Scalability | Platform |
|--------|------------|-------------|-----------|-------------|----------|
| Stdio | Low | Medium | Hard | Low | All |
| HTTP | Medium | Medium | Easy | High | All |
| Named Pipes | High | High | Medium | Medium | Unix |
| WebSocket | High | Medium | Medium | High | All |

## Implementation Examples

### Starting HTTP MCP Server

```bash
# Start HTTP MCP server
make run-mcp-http-server

# Server will be available at http://localhost:8001
# Logs will be visible in real-time
```

### Using HTTP MCP Client

```bash
# Test HTTP MCP server
python test_mcp_methods.py

# Run HTTP demo
make demo-http
```

### Switching Between Methods

```bash
# Stdio method (current default)
make demo-prod

# HTTP method (with visible logs)
make demo-http
```

## Recommendations

### For Development and Debugging
**Use HTTP MCP Server** because:
- Logs are visible in real-time
- Easy to debug with standard HTTP tools
- Can monitor tool invocations
- Better error visibility

### For Simple Applications
**Use Stdio MCP Server** because:
- Simple implementation
- No network setup required
- Good for basic use cases

### For Production
**Use HTTP MCP Server** because:
- Better scalability
- Multiple clients can connect
- Easier monitoring and logging
- More robust error handling

### For High-Performance Applications
**Use Named Pipes/Unix Sockets** because:
- Lower latency
- Higher throughput
- More efficient communication

## Migration Guide

### From Stdio to HTTP

1. **Start HTTP MCP Server:**
   ```bash
   make run-mcp-http-server
   ```

2. **Update Agent Code:**
   ```python
   # Old stdio approach
   async with TelecomMCPClient(server_script) as client:
       await client.call_graphql(query, variables)
   
   # New HTTP approach
   async with HTTPMCPClient() as client:
       result = await client.run_graphql(query, variables)
   ```

3. **Test the Migration:**
   ```bash
   make demo-http
   ```

## Troubleshooting

### HTTP MCP Server Issues

**Server not starting:**
```bash
# Check if port 8001 is available
lsof -i :8001

# Check server logs
python mcp_server/http_server.py
```

**Connection refused:**
```bash
# Ensure server is running
curl http://localhost:8001/

# Check firewall settings
```

### Stdio MCP Server Issues

**Logs not visible:**
- This is expected behavior
- Use HTTP MCP server for visible logs

**Process hanging:**
```bash
# Kill hanging processes
pkill -f "mcp_server/server.py"
```

## Conclusion

The choice of MCP communication method depends on your specific needs:

- **Development/Debugging**: HTTP Server
- **Simple Applications**: Stdio
- **Production**: HTTP Server
- **High Performance**: Named Pipes/Unix Sockets
- **Real-time**: WebSocket

For most use cases, the HTTP MCP Server provides the best balance of simplicity, debuggability, and functionality.

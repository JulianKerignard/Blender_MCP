"""Blender MCP Addon - TCP server that receives commands from the MCP server."""

bl_info = {
    "name": "Blender MCP",
    "author": "Julian Kerignard",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > MCP",
    "description": "MCP server addon - allows AI assistants to control Blender",
    "category": "Interface",
}

import bpy
import json
import socket
import struct
import threading
import traceback
import io
import sys
from contextlib import redirect_stdout, redirect_stderr


# ---------------------------------------------------------------------------
# TCP Server
# ---------------------------------------------------------------------------

class BlenderMCPServer:
    """TCP server running inside Blender to receive and execute commands."""

    _EXEC_GLOBALS: dict | None = None

    def __init__(self):
        self.server_socket: socket.socket | None = None
        self.client_socket: socket.socket | None = None
        self.running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._pending_commands: list = []

    def start(self, host: str = "127.0.0.1", port: int = 9876):
        """Start the TCP server in a background thread."""
        if self.running:
            return

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1.0)
        self.server_socket.bind((host, port))
        self.server_socket.listen(1)
        self.running = True

        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

        # Register timer to process commands on the main thread
        if not bpy.app.timers.is_registered(self._process_commands):
            bpy.app.timers.register(self._process_commands, first_interval=0.1)

    def stop(self):
        """Stop the TCP server."""
        self.running = False

        if bpy.app.timers.is_registered(self._process_commands):
            bpy.app.timers.unregister(self._process_commands)

        if self.client_socket:
            try:
                self.client_socket.close()
            except OSError:
                pass
            self.client_socket = None

        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

    def _accept_loop(self):
        """Accept connections in background thread."""
        while self.running:
            try:
                client, addr = self.server_socket.accept()
                client.settimeout(None)
                self.client_socket = client
                self._handle_client(client)
            except socket.timeout:
                continue
            except OSError:
                if self.running:
                    continue
                break

    def _handle_client(self, client: socket.socket):
        """Handle a connected client - receive commands."""
        while self.running:
            try:
                # Receive length-prefixed message
                raw_length = self._recv_exact(client, 4)
                if not raw_length:
                    break
                length = struct.unpack(">I", raw_length)[0]
                data = self._recv_exact(client, length)
                if not data:
                    break

                request = json.loads(data.decode("utf-8"))
                command = request.get("command", "")
                params = request.get("params", {})

                # Queue command for main thread execution with per-request result holder
                event = threading.Event()
                result_holder: dict = {}
                with self._lock:
                    self._pending_commands.append((command, params, event, result_holder))

                # Wait for result (processed on main thread via timer)
                event.wait(timeout=60.0)
                result = result_holder.get("result", {"status": "error", "message": "Timeout waiting for execution"})

                # Send response
                response_data = json.dumps(result).encode("utf-8")
                response_length = struct.pack(">I", len(response_data))
                client.sendall(response_length + response_data)

            except (ConnectionError, OSError):
                break
            except Exception as e:
                error_response = json.dumps({
                    "status": "error",
                    "message": str(e)
                }).encode("utf-8")
                try:
                    client.sendall(struct.pack(">I", len(error_response)) + error_response)
                except OSError:
                    break

        try:
            client.close()
        except OSError:
            pass
        self.client_socket = None

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes | None:
        """Receive exactly n bytes."""
        chunks = []
        received = 0
        while received < n:
            try:
                chunk = sock.recv(n - received)
                if not chunk:
                    return None
                chunks.append(chunk)
                received += len(chunk)
            except OSError:
                return None
        return b"".join(chunks)

    def _process_commands(self) -> float | None:
        """Process pending commands on the main thread (called by timer)."""
        if not self.running:
            return None

        with self._lock:
            commands = list(self._pending_commands)
            self._pending_commands.clear()

        if not commands:
            return 0.25  # Idle: check 4 times/second

        for command, params, event, result_holder in commands:
            result = self._execute_command(command, params)
            result_holder["result"] = result
            event.set()

        return 0.05  # Active: stay responsive

    def _execute_command(self, command: str, params: dict) -> dict:
        """Execute a command in Blender's main thread."""
        if command == "execute":
            return self._execute_code(params.get("code", ""))
        elif command == "ping":
            return {"status": "ok", "message": "pong"}
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}

    def _get_exec_globals(self) -> dict:
        """Get pre-populated globals dict for exec(), avoiding repeated imports."""
        if BlenderMCPServer._EXEC_GLOBALS is None:
            import math
            BlenderMCPServer._EXEC_GLOBALS = {
                "__builtins__": __builtins__,
                "bpy": bpy,
                "math": math,
                "json": json,
            }
        return BlenderMCPServer._EXEC_GLOBALS

    def _execute_code(self, code: str) -> dict:
        """Execute Python code in Blender and return the result."""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        local_vars = {}

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, self._get_exec_globals(), local_vars)

            result_data = local_vars.get("result", None)

            response = {"status": "ok"}
            if result_data is not None:
                response["result"] = result_data

            stdout_val = stdout_capture.getvalue()
            if stdout_val:
                response["stdout"] = stdout_val

            stderr_val = stderr_capture.getvalue()
            if stderr_val:
                response["stderr"] = stderr_val

            # Validate the whole response is serializable in one pass
            try:
                json.dumps(response)
            except (TypeError, ValueError):
                if result_data is not None:
                    response["result"] = str(result_data)

            return response

        except Exception as e:
            return {
                "status": "error",
                "message": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
            }


# Global server instance
_server = BlenderMCPServer()


# ---------------------------------------------------------------------------
# Addon Preferences
# ---------------------------------------------------------------------------

class BlenderMCPPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    tcp_port: bpy.props.IntProperty(
        name="TCP Port",
        description="Port for the MCP TCP server",
        default=9876,
        min=1024,
        max=65535,
    )

    sketchfab_api_token: bpy.props.StringProperty(
        name="SketchFab API Token",
        description="API token from sketchfab.com/settings/password",
        default="",
        subtype='PASSWORD',
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "tcp_port")
        layout.prop(self, "sketchfab_api_token")
        layout.label(text="Get your SketchFab token at: sketchfab.com/settings/password")


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class BLENDERMCP_OT_start_server(bpy.types.Operator):
    bl_idname = "blendermcp.start_server"
    bl_label = "Start MCP Server"
    bl_description = "Start the MCP TCP server"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        _server.start(port=prefs.tcp_port)
        self.report({'INFO'}, f"MCP Server started on port {prefs.tcp_port}")
        return {'FINISHED'}


class BLENDERMCP_OT_stop_server(bpy.types.Operator):
    bl_idname = "blendermcp.stop_server"
    bl_label = "Stop MCP Server"
    bl_description = "Stop the MCP TCP server"

    def execute(self, context):
        _server.stop()
        self.report({'INFO'}, "MCP Server stopped")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class BLENDERMCP_PT_main_panel(bpy.types.Panel):
    bl_label = "Blender MCP"
    bl_idname = "BLENDERMCP_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MCP"

    def draw(self, context):
        layout = self.layout

        if _server.running:
            layout.label(text="Status: Running", icon='CHECKMARK')
            row = layout.row()
            row.label(text=f"Port: {_server.server_socket.getsockname()[1]}" if _server.server_socket else "Port: ---")
            connected = _server.client_socket is not None
            row = layout.row()
            row.label(
                text="Client: Connected" if connected else "Client: Waiting...",
                icon='LINKED' if connected else 'UNLINKED',
            )
            layout.operator("blendermcp.stop_server", icon='CANCEL')
        else:
            layout.label(text="Status: Stopped", icon='X')
            layout.operator("blendermcp.start_server", icon='PLAY')

        layout.separator()
        layout.label(text="Configuration:")
        prefs = context.preferences.addons.get(__package__)
        if prefs:
            layout.prop(prefs.preferences, "tcp_port")
            layout.prop(prefs.preferences, "sketchfab_api_token")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    BlenderMCPPreferences,
    BLENDERMCP_OT_start_server,
    BLENDERMCP_OT_stop_server,
    BLENDERMCP_PT_main_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    _server.stop()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

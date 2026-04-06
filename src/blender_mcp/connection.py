"""TCP client for communicating with the Blender addon."""

import json
import socket
import struct
from typing import Any


class BlenderConnection:
    """Manages TCP connection to the Blender MCP addon."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9876):
        self.host = host
        self.port = port
        self._socket: socket.socket | None = None

    def connect(self) -> None:
        """Connect to the Blender addon TCP server."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(30.0)
        self._socket.connect((self.host, self.port))

    def disconnect(self) -> None:
        """Disconnect from Blender."""
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    @property
    def is_connected(self) -> bool:
        return self._socket is not None

    def _send_message(self, data: bytes) -> None:
        """Send a length-prefixed message."""
        length = struct.pack(">I", len(data))
        self._socket.sendall(length + data)

    def _recv_message(self) -> bytes:
        """Receive a length-prefixed message."""
        raw_length = self._recv_exact(4)
        length = struct.unpack(">I", raw_length)[0]
        return self._recv_exact(length)

    def _recv_exact(self, n: int) -> bytes:
        """Receive exactly n bytes."""
        chunks = []
        received = 0
        while received < n:
            chunk = self._socket.recv(n - received)
            if not chunk:
                raise ConnectionError("Connection closed by Blender")
            chunks.append(chunk)
            received += len(chunk)
        return b"".join(chunks)

    def send_command(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a command to Blender and return the response.

        Args:
            command: The command name to execute.
            params: Optional parameters for the command.

        Returns:
            The response dict from Blender.

        Raises:
            ConnectionError: If not connected or connection lost.
            RuntimeError: If Blender returns an error.
        """
        if not self._socket:
            raise ConnectionError("Not connected to Blender. Start the addon first.")

        request = {"command": command}
        if params:
            request["params"] = params

        try:
            self._send_message(json.dumps(request).encode("utf-8"))
            response_data = self._recv_message()
            response = json.loads(response_data.decode("utf-8"))
        except (socket.timeout, ConnectionError, OSError) as e:
            self.disconnect()
            raise ConnectionError(f"Lost connection to Blender: {e}")

        if response.get("status") == "error":
            raise RuntimeError(response.get("message", "Unknown Blender error"))

        return response

    def execute_code(self, code: str) -> dict[str, Any]:
        """Execute arbitrary Python code in Blender.

        This is the fundamental building block - all other tools
        ultimately generate Python code to execute in Blender.
        """
        return self.send_command("execute", {"code": code})

"""MCP server launcher script."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from blender_mcp.server import main
main()

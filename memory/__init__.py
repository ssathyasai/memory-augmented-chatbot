"""Memory management package initialization.

Process Flow:
1. Exports high-level `MemoryManager` orchestration entry point.
"""

from .manager import MemoryManager

__all__ = ["MemoryManager"]

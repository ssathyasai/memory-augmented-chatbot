"""Configuration package initialization.

Process Flow:
1. Loads and exposes application-wide Pydantic configuration settings.
"""

from .settings import settings

__all__ = ["settings"]

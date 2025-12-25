"""Configuration module for AWS Pricing Assistant."""

# Lazy import to avoid circular dependency
def __getattr__(name):
    if name == "settings":
        from .settings import settings
        return settings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["settings"]

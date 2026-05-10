"""The block-type registry.

A BlockType is a small declarative class with key/label/description/template
and a list of Field instances. Apps register their types via @register_block_type;
the studio reads them via all_block_types() / get_block_type(key).
"""

from __future__ import annotations

import logging
from typing import Optional


_REGISTRY: dict[str, "BlockType"] = {}
log = logging.getLogger("madga.blocks")


class BlockType:
    """Subclass and decorate with @register_block_type to make a block type
    available everywhere (homepage builder, public render, public rendering)."""

    key: str = ""
    label: str = ""
    description: str = ""
    template: str = ""
    fields: list = []  # list of madga.blocks.fields.Field instances
    icon: str = ""     # optional studio_icon name

    def coerce_from_post(self, post) -> dict:
        """Parse a POST QueryDict and produce the config dict for this block."""
        cfg: dict = {}
        for f in self.fields:
            cfg[f.name] = f.coerce_from_post(post, prefix="")
        return cfg

    def default_config(self) -> dict:
        return {f.name: f.default_value() for f in self.fields}


def register_block_type(cls):
    """Class decorator: register a BlockType subclass under cls.key.

    Validates that the class declares the required attributes. Loud failure
    here beats silent broken-block-in-studio later.
    """
    name = cls.__name__
    if not getattr(cls, "key", ""):
        raise ValueError(f"{name} must define a non-empty `key`.")
    if not getattr(cls, "label", ""):
        raise ValueError(f"{name} (key={cls.key!r}) must define a `label`.")
    if not getattr(cls, "template", ""):
        raise ValueError(
            f"{name} (key={cls.key!r}) must define a `template` path."
        )
    if not isinstance(getattr(cls, "fields", None), list):
        raise ValueError(
            f"{name} (key={cls.key!r}) must define `fields` as a list "
            f"(empty list is fine)."
        )
    if cls.key in _REGISTRY:
        existing = type(_REGISTRY[cls.key]).__name__
        log.warning(
            "Block type %r is being re-registered: %s overrides %s",
            cls.key, name, existing,
        )
    _REGISTRY[cls.key] = cls()
    return cls


def get_block_type(key: str) -> Optional[BlockType]:
    return _REGISTRY.get(key)


def all_block_types() -> list[BlockType]:
    """All registered types in registration order."""
    return list(_REGISTRY.values())


def block_type_choices() -> list[tuple[str, str]]:
    """For Django ChoiceField / model choices."""
    return [(bt.key, bt.label) for bt in _REGISTRY.values()]

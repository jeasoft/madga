"""The block-type registry.

A BlockType is a small declarative class with key/label/description/template
and a list of Field instances. Apps register their types via @register_block_type;
the studio reads them via all_block_types() / get_block_type(key).
"""

from __future__ import annotations

from typing import Optional


_REGISTRY: dict[str, "BlockType"] = {}


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
    """Class decorator: register a BlockType subclass under cls.key."""
    if not getattr(cls, "key", ""):
        raise ValueError(f"{cls.__name__} must define a non-empty `key`.")
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

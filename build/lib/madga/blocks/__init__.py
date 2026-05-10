"""Pluggable block-type registry for HomepageBlocks (and any future page sections).

Default usage in app code::

    # myapp/apps.py
    from django.apps import AppConfig

    class MyAppConfig(AppConfig):
        name = "myapp"
        def ready(self):
            from . import blocks  # registers types via decorators

    # myapp/blocks.py
    from madga.blocks import register_block_type, BlockType, TextField, ListField

    @register_block_type
    class MyHero(BlockType):
        key = "myapp_hero"
        label = "Hero del site"
        ...

A registered block type declares: key, label, description, template path,
and a list of Field objects describing its config schema. The studio's
homepage builder generates forms from these field defs at runtime.
"""

from .fields import (
    ChoiceField,
    Field,
    ImageField,
    IntField,
    ListField,
    TextField,
    UrlField,
)
from .registry import (
    BlockType,
    all_block_types,
    get_block_type,
    register_block_type,
)

__all__ = [
    "BlockType",
    "Field",
    "TextField",
    "UrlField",
    "IntField",
    "ImageField",
    "ChoiceField",
    "ListField",
    "register_block_type",
    "get_block_type",
    "all_block_types",
]

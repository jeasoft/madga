"""Template tags for rendering registered blocks."""

from django import template
from django.template.loader import render_to_string

from madga.blocks import get_block_type

register = template.Library()


@register.simple_tag(takes_context=True)
def render_block(context, block):
    """Render a HomepageBlock by dispatching to the registry's template.

    Usage: ``{% render_block block %}`` inside a loop. Falls back to an empty
    string if the block_type is not registered (e.g. dropped after a refactor).
    """
    bt = get_block_type(block.block_type)
    if bt is None or not bt.template:
        return ""
    ctx = context.flatten()
    ctx.update({
        "block": block,
        "config": block.config or {},
        "block_type": bt,
    })
    return render_to_string(bt.template, ctx)

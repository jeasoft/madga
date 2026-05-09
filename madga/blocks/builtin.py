"""Built-in block types: hero, recent_posts, featured_post, newsletter, text, cta.

These mirror the original hardcoded BLOCK_FIELDS in the homepage view so existing
HomepageBlock rows keep rendering. Loaded by madga/apps.py.ready().
"""

from .fields import IntField, TextField, UrlField
from .registry import BlockType, register_block_type


@register_block_type
class HeroBlock(BlockType):
    key = "hero"
    label = "Hero"
    description = "Bloque grande de bienvenida con título, subtítulo y un CTA."
    template = "madga/blog/blocks/hero.html"
    icon = "post"
    fields = [
        TextField("title", "Título", default="Bienvenido"),
        TextField("subtitle", "Subtítulo", multiline=True, default="Subtítulo del hero"),
        TextField("cta_label", "Texto del botón", default="Saber más"),
        UrlField("cta_url", "Destino del botón", default="/blog/"),
    ]


@register_block_type
class RecentPostsBlock(BlockType):
    key = "recent_posts"
    label = "Posts recientes"
    description = "Lista de los últimos N posts publicados."
    template = "madga/blog/blocks/recent_posts.html"
    icon = "post"
    fields = [
        TextField("title", "Título de la sección", default="Últimas publicaciones"),
        IntField("count", "Cuántos posts mostrar", min=1, max=20, default=3),
    ]


@register_block_type
class FeaturedPostBlock(BlockType):
    key = "featured_post"
    label = "Post destacado"
    description = "Un post destacado mostrado a tamaño completo."
    template = "madga/blog/blocks/featured_post.html"
    icon = "post"
    fields = [
        TextField("slug", "Slug del post a destacar"),
    ]


@register_block_type
class NewsletterBlock(BlockType):
    key = "newsletter"
    label = "Newsletter"
    description = "Banda de suscripción al newsletter."
    template = "madga/blog/blocks/newsletter.html"
    icon = "globe"
    fields = [
        TextField("title", "Título", default="Suscríbete"),
        TextField("subtitle", "Subtítulo", multiline=True, default="Una vez al mes, sin spam."),
        TextField("button_label", "Texto del botón", default="Suscribirme"),
    ]


@register_block_type
class TextBlock(BlockType):
    key = "text"
    label = "Texto"
    description = "Bloque de texto libre con título opcional."
    template = "madga/blog/blocks/text.html"
    icon = "edit"
    fields = [
        TextField("title", "Título (opcional)"),
        TextField("body", "Texto", multiline=True, rows=5),
    ]


@register_block_type
class CtaBlock(BlockType):
    key = "cta"
    label = "Call to action"
    description = "Llamada a la acción simple con un botón."
    template = "madga/blog/blocks/cta.html"
    icon = "check"
    fields = [
        TextField("title", "Título", default="Llamada a la acción"),
        TextField("cta_label", "Texto del botón", default="Empezar"),
        UrlField("cta_url", "Destino del botón", default="/blog/"),
    ]

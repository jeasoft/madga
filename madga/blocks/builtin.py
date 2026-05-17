"""Built-in block types: hero, recent_posts, featured_post, newsletter, text, cta.

Labels and descriptions use ``gettext_lazy`` so they translate at render time
based on the active language.
"""

from django.utils.translation import gettext_lazy as _

from .fields import IntField, TextField, UrlField
from .registry import BlockType, register_block_type


@register_block_type
class HeroBlock(BlockType):
    key = "hero"
    label = _("Hero")
    description = _("Large welcome block with title, subtitle and a CTA.")
    template = "madga/blog/blocks/hero.html"
    icon = "post"
    fields = [
        TextField("title", _("Title"), default="Welcome"),
        TextField("subtitle", _("Subtitle"), multiline=True, default="Hero subtitle"),
        TextField("cta_label", _("Button label"), default="Learn more"),
        UrlField("cta_url", _("Button destination"), default="/blog/"),
    ]


@register_block_type
class RecentPostsBlock(BlockType):
    key = "recent_posts"
    label = _("Recent posts")
    description = _("List of the latest N published posts.")
    template = "madga/blog/blocks/recent_posts.html"
    icon = "post"
    fields = [
        TextField("title", _("Section title"), default="Latest posts"),
        IntField("count", _("How many posts to show"), min=1, max=20, default=3),
    ]


@register_block_type
class FeaturedPostBlock(BlockType):
    key = "featured_post"
    label = _("Featured post")
    description = _("One featured post shown at full size.")
    template = "madga/blog/blocks/featured_post.html"
    icon = "post"
    fields = [
        TextField("slug", _("Slug of the post to feature")),
    ]


@register_block_type
class NewsletterBlock(BlockType):
    key = "newsletter"
    label = _("Newsletter")
    description = _("Newsletter signup band.")
    template = "madga/blog/blocks/newsletter.html"
    icon = "globe"
    fields = [
        TextField("title", _("Title"), default="Subscribe"),
        TextField("subtitle", _("Subtitle"), multiline=True, default="Once a month, no spam."),
        TextField("button_label", _("Button label"), default="Subscribe"),
    ]


@register_block_type
class TextBlock(BlockType):
    key = "text"
    label = _("Text")
    description = _("Free-form text block with optional title.")
    template = "madga/blog/blocks/text.html"
    icon = "edit"
    fields = [
        TextField("title", _("Title (optional)")),
        TextField("body", _("Text"), multiline=True, rows=5),
    ]


@register_block_type
class CtaBlock(BlockType):
    key = "cta"
    label = _("Call to action")
    description = _("Simple call-to-action with a button.")
    template = "madga/blog/blocks/cta.html"
    icon = "check"
    fields = [
        TextField("title", _("Title"), default="Call to action"),
        TextField("cta_label", _("Button label"), default="Get started"),
        UrlField("cta_url", _("Button destination"), default="/blog/"),
    ]


@register_block_type
class ContactFormBlock(BlockType):
    """Public form block. Submissions land in /studio/inbox/.

    Each field rendered is a simple text input — for richer forms,
    host projects can subclass and override the template. The form
    POSTs to /madga/form/<block_id>/submit/ which validates the
    block exists, stores a FormSubmission row, optionally emails
    the configured recipient, and fires the form.submitted webhook.
    """
    key = "contact_form"
    label = _("Contact form")
    description = _("A form visitors fill out — submissions show up in the studio inbox.")
    template = "madga/blog/blocks/contact_form.html"
    icon = "mail"
    fields = [
        TextField("title", _("Title"), default="Get in touch"),
        TextField("subtitle", _("Subtitle"), multiline=True, default="We'll reply within a day."),
        TextField("button_label", _("Submit button label"), default="Send"),
        TextField("success_message", _("Message shown after submit"), default="Thanks — we'll be in touch."),
        TextField(
            "recipient_email", _("Notification email"),
            help_text=_("Where to email each submission. Empty = no email, only inbox + webhook."),
        ),
        TextField(
            "form_key", _("Form key"),
            default="contact",
            help_text=_("Short identifier so you can tell submissions apart in the inbox."),
        ),
    ]

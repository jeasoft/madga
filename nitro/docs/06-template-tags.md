# Nitro 0.8 - Template Tags Completos

## 12. Template Tags

### `nitro/templatetags/nitro_tags.py`

```python
"""
Nitro 0.8 - Complete template tags.

{% load nitro_tags %}

HTMX Action Tags:
    {% nitro_search target='#list' placeholder='Buscar...' %}
    {% nitro_filter field='status' options=opts target='#list' %}
    {% nitro_pagination page_obj target='#list' %}
    {% nitro_sort 'name' 'Nombre' target='#list' %}
    {% nitro_delete url=delete_url target='#list' confirm='¿Eliminar?' %}

Form Tags:
    {% nitro_field form.name %}
    {% nitro_select form.category search_url='/api/search/' %}

Component Tags:
    {% nitro_tabs id='tabs' target='#content' %}...{% end_nitro_tabs %}
    {% nitro_modal id='my-modal' title='Título' %}...{% end_nitro_modal %}
    {% nitro_empty_state icon='🏠' title='Sin datos' message='...' %}
    {% nitro_stats_card icon='💰' label='Ingresos' value=total %}
    {% nitro_avatar user size='md' %}
    {% nitro_confirm_modal id='confirm' %}

Display Filters:
    {{ value|status_badge }}
    {{ value|priority_badge }}
    {{ amount|currency:currency_code }}
    {{ phone|phone_format }}
    {{ date|relative_date }}
    {{ uuid|truncate_id:8 }}
    {{ phone|whatsapp_link:"message" }}

Table/Filter Tags:
    {% nitro_table table %}
    {% nitro_filters filterset target='#list' %}
"""

from django import template
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe
from django.utils import timezone
from datetime import datetime, date, timedelta
import json

register = template.Library()


# =============================================================================
# HTMX ACTION TAGS
# =============================================================================

@register.inclusion_tag('nitro/components/search_bar.html', takes_context=True)
def nitro_search(context, target='#list-content', placeholder='Buscar...', name='q'):
    """Search input with HTMX debounce."""
    request = context.get('request')
    return {
        'target': target,
        'placeholder': placeholder,
        'name': name,
        'current_value': request.GET.get(name, '') if request else '',
        'request_path': request.path if request else '',
    }


@register.inclusion_tag('nitro/components/filter_select.html', takes_context=True)
def nitro_filter(context, field, options, target='#list-content', label='', all_label='Todos'):
    """Filter dropdown with HTMX."""
    request = context.get('request')
    return {
        'field': field,
        'options': options,
        'target': target,
        'label': label,
        'all_label': all_label,
        'current_value': request.GET.get(field, '') if request else '',
        'request_path': request.path if request else '',
    }


@register.simple_tag(takes_context=True)
def nitro_delete(context, url, target='#list-content', confirm='', swap='outerHTML'):
    """Generate hx-delete attributes."""
    attrs = f'hx-delete="{escape(url)}" hx-target="{escape(target)}" hx-swap="{escape(swap)}"'
    if confirm:
        attrs += f' hx-confirm="{escape(confirm)}"'
    return mark_safe(attrs)


@register.simple_tag(takes_context=True)
def nitro_form(context, url='', target='#list-content', method='post', swap='outerHTML', encoding=''):
    """Generate hx-* attributes for HTMX form."""
    method_lower = method.lower()
    attrs = f'hx-{method_lower}="{escape(url)}" hx-target="{escape(target)}" hx-swap="{escape(swap)}"'
    if encoding:
        attrs += f' hx-encoding="{escape(encoding)}"'
    return mark_safe(attrs)


@register.inclusion_tag('nitro/components/pagination.html', takes_context=True)
def nitro_pagination(context, page_obj, target='#list-content'):
    """HTMX-powered pagination."""
    request = context.get('request')
    params = request.GET.copy() if request else {}
    params.pop('page', None)
    return {
        'page_obj': page_obj,
        'target': target,
        'query_string': params.urlencode(),
        'request_path': request.path if request else '',
    }


@register.simple_tag(takes_context=True)
def nitro_sort(context, field, label, current_sort='', target='#list-content'):
    """Sort button with toggle direction."""
    request = context.get('request')
    if not current_sort and request:
        current_sort = request.GET.get('sort', '')
    
    if current_sort == field:
        next_sort = f'-{field}'
        indicator = ' <span class="text-primary-500">↑</span>'
    elif current_sort == f'-{field}':
        next_sort = field
        indicator = ' <span class="text-primary-500">↓</span>'
    else:
        next_sort = field
        indicator = ''
    
    params = request.GET.copy() if request else {}
    params['sort'] = next_sort
    url = f'{request.path}?{params.urlencode()}' if request else f'?sort={next_sort}'
    
    return mark_safe(
        f'<button type="button" hx-get="{escape(url)}" hx-target="{escape(target)}" '
        f'hx-replace-url="true" class="text-xs font-medium text-gray-500 hover:text-gray-700 '
        f'uppercase tracking-wider cursor-pointer">{escape(label)}{indicator}</button>'
    )


# =============================================================================
# FORM FIELD TAGS
# =============================================================================

@register.inclusion_tag('nitro/components/form_field.html')
def nitro_field(field, label='', help_text='', css_class=''):
    """Render form field with Tailwind styling."""
    if not hasattr(field, 'field'):
        return {'field': field, 'label': label, 'help_text': help_text, 
                'css_class': css_class, 'is_required': False, 'errors': [], 'field_type': 'input'}
    return {
        'field': field,
        'label': label or field.label,
        'help_text': help_text or (field.help_text if hasattr(field, 'help_text') else ''),
        'css_class': css_class,
        'is_required': field.field.required,
        'errors': field.errors if hasattr(field, 'errors') else [],
        'field_type': _get_field_type(field),
    }


def _get_field_type(field):
    widget_class = field.field.widget.__class__.__name__ if hasattr(field, 'field') else ''
    if widget_class in ('CheckboxInput',):
        return 'checkbox'
    if widget_class in ('Textarea',):
        return 'textarea'
    if widget_class in ('Select', 'SelectMultiple'):
        return 'select'
    if widget_class in ('FileInput', 'ClearableFileInput'):
        return 'file'
    return 'input'


@register.inclusion_tag('nitro/components/select_field.html')
def nitro_select(field, placeholder='Buscar...', search_url='', label='',
                 help_text='', css_class='', parent_input='', cascade_param='parent'):
    """Searchable select (like Select2)."""
    if not hasattr(field, 'field'):
        return {'field': field, 'choices': [], 'placeholder': placeholder}
    
    choices = []
    if hasattr(field.field, 'queryset') and field.field.queryset is not None:
        choices = [(str(obj.pk), str(obj)) for obj in field.field.queryset[:200]]
    elif hasattr(field.field, 'choices'):
        choices = [(str(k), str(v)) for k, v in field.field.choices if k != '' and k is not None]
    
    current_value = str(field.value()) if field.value() else ''
    current_label = ''
    for v, l in choices:
        if v == current_value:
            current_label = l
            break
    
    return {
        'field': field,
        'field_name': field.html_name,
        'field_id': field.id_for_label,
        'choices': choices,
        'options_json': json.dumps([{'value': v, 'label': l} for v, l in choices]),
        'current_value': current_value,
        'current_label': current_label,
        'placeholder': placeholder,
        'search_url': search_url,
        'parent_input': parent_input,
        'cascade_param': cascade_param,
        'label': label or field.label,
        'help_text': help_text or (field.help_text if hasattr(field, 'help_text') else ''),
        'css_class': css_class,
        'is_required': field.field.required,
        'errors': field.errors if hasattr(field, 'errors') else [],
    }


# =============================================================================
# COMPONENT TAGS
# =============================================================================

# Tabs
class NitroTabsNode(template.Node):
    def __init__(self, nodelist, tabs_id, target):
        self.nodelist = nodelist
        self.tabs_id = tabs_id
        self.target = target

    def render(self, context):
        tabs_id = self.tabs_id.resolve(context) if hasattr(self.tabs_id, 'resolve') else self.tabs_id
        target = self.target.resolve(context) if hasattr(self.target, 'resolve') else self.target

        context['_nitro_tabs'] = []
        context['_nitro_tabs_target'] = target
        self.nodelist.render(context)
        tabs = context.get('_nitro_tabs', [])

        if not tabs:
            return ''

        request = context.get('request')
        current_tab = request.GET.get('tab', '') if request else ''
        request_path = request.path if request else ''

        active_tab = current_tab
        if not active_tab:
            for tab in tabs:
                if tab.get('active'):
                    active_tab = tab['name']
                    break
            if not active_tab and tabs:
                active_tab = tabs[0]['name']

        html = [f'<div id="{escape(tabs_id)}" class="border-b border-gray-200 mb-4">',
                '  <nav class="-mb-px flex space-x-6 overflow-x-auto" aria-label="Tabs">']
        
        for tab in tabs:
            is_active = tab['name'] == active_tab
            classes = 'border-primary-500 text-primary-600' if is_active else 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            url = f'{request_path}?tab={escape(tab["name"])}'
            html.append(
                f'    <button type="button" hx-get="{url}" hx-target="{escape(target)}" hx-replace-url="true" '
                f'class="whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm {classes}">'
                f'{escape(tab["label"])}</button>'
            )
        
        html.extend(['  </nav>', '</div>'])
        return '\n'.join(html)


@register.tag('nitro_tabs')
def do_nitro_tabs(parser, token):
    bits = token.split_contents()
    kwargs = {}
    for bit in bits[1:]:
        if '=' in bit:
            key, val = bit.split('=', 1)
            kwargs[key] = val.strip("'\"")
    
    nodelist = parser.parse(('end_nitro_tabs',))
    parser.delete_first_token()
    return NitroTabsNode(nodelist, kwargs.get('id', 'tabs'), kwargs.get('target', '#tab-content'))


@register.simple_tag(takes_context=True)
def nitro_tab(context, name='', label='', active=False):
    tabs = context.get('_nitro_tabs')
    if tabs is not None:
        tabs.append({'name': name, 'label': label, 'active': active})
    return ''


# Empty State
@register.inclusion_tag('nitro/components/empty_state.html')
def nitro_empty_state(icon='📭', title='No hay datos', message='', action_url='', action_text=''):
    return {
        'icon': icon,
        'title': title,
        'message': message,
        'action_url': action_url,
        'action_text': action_text,
    }


# Stats Card
@register.inclusion_tag('nitro/components/stats_card.html')
def nitro_stats_card(icon='📊', label='', value='', change='', change_type='neutral', href=''):
    return {
        'icon': icon,
        'label': label,
        'value': value,
        'change': change,
        'change_type': change_type,  # 'positive', 'negative', 'neutral'
        'href': href,
    }


# Avatar
@register.inclusion_tag('nitro/components/avatar.html')
def nitro_avatar(user=None, name='', image_url='', size='md'):
    if user:
        name = user.get_full_name() or user.username
        image_url = getattr(user, 'avatar_url', '') or ''
    
    initials = ''.join([n[0].upper() for n in name.split()[:2]]) if name else '?'
    
    sizes = {
        'xs': 'w-6 h-6 text-xs',
        'sm': 'w-8 h-8 text-sm',
        'md': 'w-10 h-10 text-base',
        'lg': 'w-12 h-12 text-lg',
        'xl': 'w-16 h-16 text-xl',
    }
    
    return {
        'name': name,
        'image_url': image_url,
        'initials': initials,
        'size_class': sizes.get(size, sizes['md']),
    }


# =============================================================================
# DISPLAY FILTERS
# =============================================================================

@register.filter
def status_badge(value, mapping=''):
    """Render status badge with colors."""
    color_map = {
        'active': ('Activo', 'green'), 'activo': ('Activo', 'green'),
        'inactive': ('Inactivo', 'gray'), 'inactivo': ('Inactivo', 'gray'),
        'pending': ('Pendiente', 'yellow'), 'pendiente': ('Pendiente', 'yellow'),
        'draft': ('Borrador', 'gray'), 'borrador': ('Borrador', 'gray'),
        'expired': ('Vencido', 'red'), 'vencido': ('Vencido', 'red'),
        'available': ('Disponible', 'green'), 'disponible': ('Disponible', 'green'),
        'rented': ('Alquilada', 'blue'), 'alquilada': ('Alquilada', 'blue'),
        'maintenance': ('Mantenimiento', 'yellow'),
        'open': ('Abierto', 'blue'), 'abierto': ('Abierto', 'blue'),
        'closed': ('Cerrado', 'gray'), 'cerrado': ('Cerrado', 'gray'),
        'resolved': ('Resuelto', 'green'), 'resuelto': ('Resuelto', 'green'),
        'in_progress': ('En Progreso', 'blue'),
        'paid': ('Pagado', 'green'), 'pagado': ('Pagado', 'green'),
        'overdue': ('Atrasado', 'red'), 'atrasado': ('Atrasado', 'red'),
        'partial': ('Parcial', 'yellow'), 'parcial': ('Parcial', 'yellow'),
    }
    
    str_value = str(value).lower().strip() if value else ''
    label, color = color_map.get(str_value, (str(value), 'gray'))
    
    colors = {
        'green': 'bg-green-100 text-green-800',
        'red': 'bg-red-100 text-red-800',
        'yellow': 'bg-yellow-100 text-yellow-800',
        'blue': 'bg-blue-100 text-blue-800',
        'gray': 'bg-gray-100 text-gray-800',
        'purple': 'bg-purple-100 text-purple-800',
    }
    
    return mark_safe(
        f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium '
        f'{colors.get(color, colors["gray"])}">{escape(label)}</span>'
    )


@register.filter
def priority_badge(value):
    """Render priority badge."""
    priority_map = {
        'low': ('Baja', 'gray'), 'baja': ('Baja', 'gray'),
        'medium': ('Media', 'yellow'), 'media': ('Media', 'yellow'),
        'high': ('Alta', 'orange'), 'alta': ('Alta', 'orange'),
        'urgent': ('Urgente', 'red'), 'urgente': ('Urgente', 'red'),
    }
    
    str_value = str(value).lower().strip() if value else ''
    label, color = priority_map.get(str_value, (str(value), 'gray'))
    
    colors = {
        'gray': 'bg-gray-100 text-gray-800',
        'yellow': 'bg-yellow-100 text-yellow-800',
        'orange': 'bg-orange-100 text-orange-800',
        'red': 'bg-red-100 text-red-800',
    }
    
    return mark_safe(
        f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium '
        f'{colors.get(color, colors["gray"])}">{escape(label)}</span>'
    )


@register.filter
def currency(value, currency_code='DOP'):
    """Format currency with symbol."""
    symbols = {'DOP': 'RD$', 'USD': 'US$', 'EUR': '€'}
    symbol = symbols.get(currency_code, currency_code)
    try:
        return f'{symbol} {float(value):,.2f}'
    except (ValueError, TypeError):
        return f'{symbol} {value}'


@register.filter
def phone_format(value):
    """Format phone: (809) 555-1234"""
    if not value:
        return ''
    digits = ''.join(c for c in str(value) if c.isdigit())
    if len(digits) == 10:
        return f'({digits[:3]}) {digits[3:6]}-{digits[6:]}'
    if len(digits) == 11 and digits[0] == '1':
        return f'+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}'
    return str(value)


@register.filter
def truncate_id(value, length=8):
    """Truncate UUID for display."""
    s = str(value)
    return s[:length] if len(s) > length else s


@register.filter
def relative_date(value):
    """Show relative date (hoy, ayer, hace X días)."""
    if not value:
        return ''
    
    if isinstance(value, datetime):
        value = value.date()
    
    today = timezone.now().date()
    diff = (today - value).days
    
    if diff == 0:
        return 'Hoy'
    if diff == 1:
        return 'Ayer'
    if diff < 7:
        return f'Hace {diff} días'
    if diff < 30:
        weeks = diff // 7
        return f'Hace {weeks} semana{"s" if weeks > 1 else ""}'
    if diff < 365:
        months = diff // 30
        return f'Hace {months} mes{"es" if months > 1 else ""}'
    
    return value.strftime('%d/%m/%Y')


@register.filter
def whatsapp_link(phone, message=''):
    """Generate WhatsApp link."""
    from apps.core.utils.whatsapp import whatsapp_link as wa_link
    return wa_link(phone, message)


# =============================================================================
# TABLE AND FILTER TAGS
# =============================================================================

@register.inclusion_tag('nitro/components/table.html', takes_context=True)
def nitro_table(context, table, target='#list-content'):
    """Render NitroTable."""
    return {
        'table': table,
        'target': target,
        'request': context.get('request'),
    }


@register.inclusion_tag('nitro/components/filters.html', takes_context=True)
def nitro_filters(context, filterset, target='#list-content'):
    """Render NitroFilterSet."""
    return {
        'filters': filterset.filters,
        'is_active': filterset.is_active(),
        'target': target,
        'request': context.get('request'),
    }
```

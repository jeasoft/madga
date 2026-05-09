# Nitro 0.8 - Tables y Filters

## 7. Declarative Tables

### `nitro/tables.py`

```python
"""
Nitro 0.8 - Declarative table configuration.

Usage:
    class PropertyTable(NitroTable):
        class Meta:
            model = Property
            columns = ['name', 'address', 'status', 'rent_amount']
            sortable = ['name', 'rent_amount', 'created_at']
            row_actions = ['edit', 'delete']
    
    # In view
    table = PropertyTable(queryset, request)
    
    # In template
    {% nitro_table table %}
"""

from django.utils.html import format_html
from django.urls import reverse


class Column:
    """
    Table column definition.
    
    Column('name', label='Nombre', sortable=True)
    Column('status', label='Estado', template='{{ value|status_badge }}')
    Column('rent_amount', label='Renta', format='currency')
    """
    
    def __init__(self, field, label=None, sortable=False, 
                 template=None, format=None, css_class='',
                 visible=True, link=None, empty_value='-'):
        self.field = field
        self.label = label or field.replace('_', ' ').title()
        self.sortable = sortable
        self.template = template
        self.format = format  # 'currency', 'date', 'datetime', 'phone', 'boolean'
        self.css_class = css_class
        self.visible = visible
        self.link = link  # URL name or callable
        self.empty_value = empty_value
    
    def get_value(self, obj):
        """Get value from object, supporting related fields."""
        value = obj
        for part in self.field.split('__'):
            if value is None:
                return self.empty_value
            value = getattr(value, part, None)
        return value if value is not None else self.empty_value
    
    def render(self, obj, request=None):
        """Render the cell value."""
        value = self.get_value(obj)
        
        if value == self.empty_value:
            return self.empty_value
        
        # Apply format
        if self.format:
            value = self._apply_format(value, obj)
        
        # Wrap in link if specified
        if self.link:
            url = self._get_link_url(obj)
            if url:
                value = format_html('<a href="{}" class="text-primary-600 hover:underline">{}</a>', url, value)
        
        return value
    
    def _apply_format(self, value, obj):
        """Apply formatting to value."""
        from django.utils.formats import date_format, number_format
        
        if self.format == 'currency':
            currency = getattr(obj, 'currency', 'DOP')
            symbols = {'DOP': 'RD$', 'USD': 'US$', 'EUR': '€'}
            symbol = symbols.get(currency, currency)
            return f'{symbol} {value:,.2f}'
        
        if self.format == 'date':
            return date_format(value, 'd/m/Y') if value else self.empty_value
        
        if self.format == 'datetime':
            return date_format(value, 'd/m/Y H:i') if value else self.empty_value
        
        if self.format == 'phone':
            digits = ''.join(c for c in str(value) if c.isdigit())
            if len(digits) == 10:
                return f'({digits[:3]}) {digits[3:6]}-{digits[6:]}'
            return value
        
        if self.format == 'boolean':
            return '✓' if value else '✗'
        
        return value
    
    def _get_link_url(self, obj):
        """Get URL for cell link."""
        if callable(self.link):
            return self.link(obj)
        if isinstance(self.link, str):
            try:
                return reverse(self.link, args=[obj.pk])
            except:
                return None
        return None


class RowAction:
    """
    Row action (button in actions column).
    
    RowAction('edit', label='Editar', url='property_edit', icon='✏️')
    RowAction('delete', label='Eliminar', url='property_delete', method='delete', confirm='¿Eliminar?')
    """
    
    def __init__(self, name, label=None, url=None, icon='', 
                 css_class='', method='get', confirm=None,
                 condition=None, permission=None):
        self.name = name
        self.label = label or name.title()
        self.url = url  # URL name or callable
        self.icon = icon
        self.css_class = css_class or self._default_css_class()
        self.method = method.lower()  # 'get', 'post', 'delete'
        self.confirm = confirm  # Confirmation message
        self.condition = condition  # Callable(obj) -> bool
        self.permission = permission  # Permission string
    
    def _default_css_class(self):
        """Default CSS class based on action name."""
        if self.name == 'delete':
            return 'text-red-600 hover:text-red-800'
        if self.name == 'edit':
            return 'text-primary-600 hover:text-primary-800'
        return 'text-gray-600 hover:text-gray-800'
    
    def get_url(self, obj):
        """Get action URL for object."""
        if callable(self.url):
            return self.url(obj)
        if isinstance(self.url, str):
            try:
                return reverse(self.url, args=[obj.pk])
            except:
                return '#'
        return '#'
    
    def is_visible(self, obj, user=None):
        """Check if action should be shown."""
        if self.condition and not self.condition(obj):
            return False
        if self.permission and user and not user.has_perm(self.permission):
            return False
        return True
    
    def render(self, obj, user=None):
        """Render action button/link."""
        if not self.is_visible(obj, user):
            return ''
        
        url = self.get_url(obj)
        content = f'{self.icon} {self.label}'.strip()
        
        if self.method == 'get':
            return format_html(
                '<a href="{}" class="{}">{}</a>',
                url, self.css_class, content
            )
        
        # HTMX for non-GET methods
        attrs = f'hx-{self.method}="{url}"'
        if self.confirm:
            attrs += f' hx-confirm="{self.confirm}"'
        
        return format_html(
            '<button type="button" {} class="{}">{}</button>',
            attrs, self.css_class, content
        )


class BulkAction:
    """
    Bulk action for selected rows.
    
    BulkAction('delete', label='Eliminar seleccionados', url='bulk_delete')
    """
    
    def __init__(self, name, label=None, url=None, confirm=None, permission=None):
        self.name = name
        self.label = label or name.title()
        self.url = url
        self.confirm = confirm
        self.permission = permission


class NitroTableMeta:
    """Metaclass for NitroTable to collect column definitions."""
    
    def __new__(mcs, name, bases, attrs):
        columns = []
        row_actions = []
        bulk_actions = []
        
        # Collect from Meta class
        meta = attrs.get('Meta')
        if meta:
            if hasattr(meta, 'columns'):
                for col in meta.columns:
                    if isinstance(col, str):
                        columns.append(Column(col))
                    elif isinstance(col, Column):
                        columns.append(col)
            
            if hasattr(meta, 'row_actions'):
                for action in meta.row_actions:
                    if isinstance(action, str):
                        row_actions.append(RowAction(action))
                    elif isinstance(action, RowAction):
                        row_actions.append(action)
            
            if hasattr(meta, 'bulk_actions'):
                for action in meta.bulk_actions:
                    if isinstance(action, str):
                        bulk_actions.append(BulkAction(action))
                    elif isinstance(action, BulkAction):
                        bulk_actions.append(action)
        
        attrs['_columns'] = columns
        attrs['_row_actions'] = row_actions
        attrs['_bulk_actions'] = bulk_actions
        
        return super().__new__(mcs, name, bases, attrs)


class NitroTable(metaclass=NitroTableMeta):
    """
    Declarative table.
    
    class PropertyTable(NitroTable):
        class Meta:
            model = Property
            columns = [
                Column('name', sortable=True, link='property_detail'),
                Column('address'),
                Column('status', template='{{ value|status_badge }}'),
                Column('rent_amount', format='currency', sortable=True),
            ]
            row_actions = [
                RowAction('edit', url='property_edit', icon='✏️'),
                RowAction('delete', url='property_delete', method='delete', confirm='¿Eliminar?'),
            ]
    """
    
    _columns = []
    _row_actions = []
    _bulk_actions = []
    
    def __init__(self, queryset, request=None):
        self.queryset = queryset
        self.request = request
        self.user = request.user if request else None
    
    @property
    def columns(self):
        return [c for c in self._columns if c.visible]
    
    @property
    def row_actions(self):
        return self._row_actions
    
    @property
    def bulk_actions(self):
        return [a for a in self._bulk_actions 
                if not a.permission or (self.user and self.user.has_perm(a.permission))]
    
    @property
    def has_bulk_actions(self):
        return bool(self.bulk_actions)
    
    def get_rows(self):
        """Yield (object, cells, actions) for each row."""
        for obj in self.queryset:
            cells = [col.render(obj, self.request) for col in self.columns]
            actions = [a.render(obj, self.user) for a in self.row_actions]
            yield obj, cells, actions
```

---

## 8. Faceted Filters

### `nitro/filters.py`

```python
"""
Nitro 0.8 - Faceted filter system.

Usage:
    class JobFilterSet(NitroFilterSet):
        search = SearchFilter(fields=['title', 'company__name'])
        location = SelectFilter(queryset=Location.objects.all())
        salary = RangeFilter(min=0, max=200000)
        posted = DateRangeFilter()
        remote = BooleanFilter()
    
    # In view
    filterset = JobFilterSet(request.GET, queryset=Job.objects.all())
    jobs = filterset.qs
    
    # In template
    {% nitro_filters filterset target='#job-list' %}
"""

from django.db.models import Q


class BaseFilter:
    """Base filter class."""
    
    def __init__(self, field=None, label=None, required=False):
        self.field = field
        self.label = label
        self.required = required
        self.name = None  # Set by FilterSet
    
    def get_field_name(self):
        return self.field or self.name
    
    def filter(self, qs, value):
        """Apply filter to queryset. Override in subclasses."""
        raise NotImplementedError
    
    def get_value(self, data):
        """Get filter value from request data."""
        return data.get(self.name, '')
    
    def render(self, value, request=None):
        """Render filter widget. Override in subclasses."""
        raise NotImplementedError


class SearchFilter(BaseFilter):
    """
    Text search across multiple fields.
    
    search = SearchFilter(fields=['name', 'description', 'tags__name'])
    """
    
    def __init__(self, fields=None, placeholder='Buscar...', **kwargs):
        super().__init__(**kwargs)
        self.fields = fields or []
        self.placeholder = placeholder
    
    def filter(self, qs, value):
        if not value or not self.fields:
            return qs
        
        q = Q()
        for field in self.fields:
            q |= Q(**{f'{field}__icontains': value})
        return qs.filter(q)
    
    def render(self, value, request=None):
        return {
            'type': 'search',
            'name': self.name,
            'value': value,
            'placeholder': self.placeholder,
        }


class SelectFilter(BaseFilter):
    """
    Select dropdown filter.
    
    status = SelectFilter(choices=[('active', 'Activo'), ('inactive', 'Inactivo')])
    category = SelectFilter(queryset=Category.objects.all())
    """
    
    def __init__(self, choices=None, queryset=None, all_label='Todos', **kwargs):
        super().__init__(**kwargs)
        self.choices = choices
        self.queryset = queryset
        self.all_label = all_label
    
    def get_choices(self):
        if self.choices:
            return self.choices
        if self.queryset is not None:
            return [(str(obj.pk), str(obj)) for obj in self.queryset]
        return []
    
    def filter(self, qs, value):
        if not value:
            return qs
        return qs.filter(**{self.get_field_name(): value})
    
    def render(self, value, request=None):
        return {
            'type': 'select',
            'name': self.name,
            'value': value,
            'choices': self.get_choices(),
            'all_label': self.all_label,
            'label': self.label,
        }


class MultiSelectFilter(SelectFilter):
    """
    Multi-select filter.
    
    tags = MultiSelectFilter(queryset=Tag.objects.all())
    """
    
    def get_value(self, data):
        return data.getlist(self.name, [])
    
    def filter(self, qs, value):
        if not value:
            return qs
        return qs.filter(**{f'{self.get_field_name()}__in': value})
    
    def render(self, value, request=None):
        data = super().render(value, request)
        data['type'] = 'multiselect'
        return data


class BooleanFilter(BaseFilter):
    """
    Boolean toggle filter.
    
    is_active = BooleanFilter(label='Solo activos')
    """
    
    def __init__(self, true_label='Sí', false_label='No', **kwargs):
        super().__init__(**kwargs)
        self.true_label = true_label
        self.false_label = false_label
    
    def filter(self, qs, value):
        if value == '':
            return qs
        return qs.filter(**{self.get_field_name(): value == 'true'})
    
    def render(self, value, request=None):
        return {
            'type': 'boolean',
            'name': self.name,
            'value': value,
            'true_label': self.true_label,
            'false_label': self.false_label,
            'label': self.label,
        }


class RangeFilter(BaseFilter):
    """
    Numeric range filter.
    
    salary = RangeFilter(min=0, max=200000, step=1000, label='Salario')
    """
    
    def __init__(self, min=None, max=None, step=1, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max
        self.step = step
    
    def get_value(self, data):
        return {
            'min': data.get(f'{self.name}_min', ''),
            'max': data.get(f'{self.name}_max', ''),
        }
    
    def filter(self, qs, value):
        field = self.get_field_name()
        if value.get('min'):
            qs = qs.filter(**{f'{field}__gte': value['min']})
        if value.get('max'):
            qs = qs.filter(**{f'{field}__lte': value['max']})
        return qs
    
    def render(self, value, request=None):
        return {
            'type': 'range',
            'name': self.name,
            'value': value,
            'min': self.min,
            'max': self.max,
            'step': self.step,
            'label': self.label,
        }


class DateRangeFilter(BaseFilter):
    """
    Date range filter.
    
    posted = DateRangeFilter(label='Fecha de publicación')
    """
    
    def get_value(self, data):
        return {
            'from': data.get(f'{self.name}_from', ''),
            'to': data.get(f'{self.name}_to', ''),
        }
    
    def filter(self, qs, value):
        field = self.get_field_name()
        if value.get('from'):
            qs = qs.filter(**{f'{field}__gte': value['from']})
        if value.get('to'):
            qs = qs.filter(**{f'{field}__lte': value['to']})
        return qs
    
    def render(self, value, request=None):
        return {
            'type': 'date_range',
            'name': self.name,
            'value': value,
            'label': self.label,
        }


class NitroFilterSetMeta(type):
    """Metaclass to collect filter definitions."""
    
    def __new__(mcs, name, bases, attrs):
        filters = {}
        
        # Collect filters from base classes
        for base in bases:
            if hasattr(base, '_filters'):
                filters.update(base._filters)
        
        # Collect filters from this class
        for key, value in list(attrs.items()):
            if isinstance(value, BaseFilter):
                value.name = key
                if not value.field:
                    value.field = key
                filters[key] = value
                attrs.pop(key)
        
        attrs['_filters'] = filters
        return super().__new__(mcs, name, bases, attrs)


class NitroFilterSet(metaclass=NitroFilterSetMeta):
    """
    Base filter set.
    
    class JobFilterSet(NitroFilterSet):
        q = SearchFilter(fields=['title', 'company__name'])
        location = SelectFilter(queryset=Location.objects.all())
        salary = RangeFilter(min=0, max=200000)
    """
    
    _filters = {}
    
    def __init__(self, data, queryset):
        self.data = data
        self.queryset = queryset
        self._qs = None
    
    @property
    def qs(self):
        """Get filtered queryset."""
        if self._qs is None:
            self._qs = self.queryset
            for name, filter_obj in self._filters.items():
                value = filter_obj.get_value(self.data)
                self._qs = filter_obj.filter(self._qs, value)
        return self._qs
    
    @property
    def filters(self):
        """Get list of filter definitions for template."""
        result = []
        for name, filter_obj in self._filters.items():
            value = filter_obj.get_value(self.data)
            result.append(filter_obj.render(value))
        return result
    
    def is_active(self):
        """Check if any filters are applied."""
        for name, filter_obj in self._filters.items():
            value = filter_obj.get_value(self.data)
            if value and value != '' and value != {'min': '', 'max': ''} and value != {'from': '', 'to': ''}:
                return True
        return False
```

### Filter Template

```django
{# templates/nitro/components/filters.html #}
<div class="bg-white rounded-xl border p-4 mb-4">
    <form hx-get="{{ request.path }}" hx-target="{{ target }}" hx-replace-url="true"
          class="space-y-4">
        
        {% for filter in filters %}
            {% if filter.type == 'search' %}
            <div>
                <input type="search" name="{{ filter.name }}" value="{{ filter.value }}"
                       placeholder="{{ filter.placeholder }}"
                       hx-trigger="input changed delay:300ms"
                       class="w-full px-3 py-2 border rounded-lg text-sm">
            </div>
            
            {% elif filter.type == 'select' %}
            <div>
                {% if filter.label %}<label class="block text-sm font-medium mb-1">{{ filter.label }}</label>{% endif %}
                <select name="{{ filter.name }}" hx-trigger="change"
                        class="w-full px-3 py-2 border rounded-lg text-sm bg-white">
                    <option value="">{{ filter.all_label }}</option>
                    {% for value, label in filter.choices %}
                    <option value="{{ value }}" {% if value == filter.value %}selected{% endif %}>{{ label }}</option>
                    {% endfor %}
                </select>
            </div>
            
            {% elif filter.type == 'range' %}
            <div>
                {% if filter.label %}<label class="block text-sm font-medium mb-1">{{ filter.label }}</label>{% endif %}
                <div class="flex gap-2">
                    <input type="number" name="{{ filter.name }}_min" 
                           value="{{ filter.value.min }}"
                           placeholder="Mín" min="{{ filter.min }}" step="{{ filter.step }}"
                           class="w-1/2 px-3 py-2 border rounded-lg text-sm">
                    <input type="number" name="{{ filter.name }}_max"
                           value="{{ filter.value.max }}"
                           placeholder="Máx" max="{{ filter.max }}" step="{{ filter.step }}"
                           class="w-1/2 px-3 py-2 border rounded-lg text-sm">
                </div>
            </div>
            
            {% elif filter.type == 'date_range' %}
            <div>
                {% if filter.label %}<label class="block text-sm font-medium mb-1">{{ filter.label }}</label>{% endif %}
                <div class="flex gap-2">
                    <input type="date" name="{{ filter.name }}_from" value="{{ filter.value.from }}"
                           class="w-1/2 px-3 py-2 border rounded-lg text-sm">
                    <input type="date" name="{{ filter.name }}_to" value="{{ filter.value.to }}"
                           class="w-1/2 px-3 py-2 border rounded-lg text-sm">
                </div>
            </div>
            
            {% elif filter.type == 'boolean' %}
            <div>
                <label class="flex items-center gap-2">
                    <input type="checkbox" name="{{ filter.name }}" value="true"
                           {% if filter.value == 'true' %}checked{% endif %}
                           hx-trigger="change"
                           class="h-4 w-4 rounded border-gray-300">
                    <span class="text-sm">{{ filter.label }}</span>
                </label>
            </div>
            {% endif %}
        {% endfor %}
        
        <div class="flex gap-2">
            <button type="submit" class="btn btn-primary btn-sm">Filtrar</button>
            <a href="{{ request.path }}" class="btn btn-secondary btn-sm">Limpiar</a>
        </div>
    </form>
</div>
```

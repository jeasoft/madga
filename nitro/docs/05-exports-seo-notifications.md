# Nitro 0.8 - Exports, SEO, Notifications

## 9. Export System

### `nitro/exports.py`

```python
"""
Nitro 0.8 - Data export utilities.

Usage:
    class PropertyListView(ExportMixin, NitroListView):
        export_fields = [
            ExportField('name', 'Nombre'),
            ExportField('address', 'Dirección'),
            ExportField('status', 'Estado', getter=lambda obj: obj.get_status_display()),
            ExportField('rent_amount', 'Renta', format='currency'),
        ]
        export_filename = 'propiedades'
"""

import csv
from io import BytesIO
from datetime import date, datetime
from decimal import Decimal
from django.http import HttpResponse


class ExportField:
    """Define a field for export."""
    
    def __init__(self, field, label=None, getter=None, format=None):
        self.field = field
        self.label = label or field.replace('_', ' ').title()
        self.getter = getter
        self.format = format  # 'currency', 'date', 'datetime', 'boolean'
    
    def get_value(self, obj):
        """Get value from object."""
        if self.getter:
            value = self.getter(obj)
        else:
            value = obj
            for part in self.field.split('__'):
                if value is None:
                    return ''
                value = getattr(value, part, None)
        
        return self._format_value(value)
    
    def _format_value(self, value):
        """Format value for export."""
        if value is None:
            return ''
        
        if self.format == 'currency':
            return f'{value:.2f}' if isinstance(value, (int, float, Decimal)) else value
        
        if self.format == 'date':
            if isinstance(value, (date, datetime)):
                return value.strftime('%Y-%m-%d')
            return value
        
        if self.format == 'datetime':
            if isinstance(value, datetime):
                return value.strftime('%Y-%m-%d %H:%M')
            return value
        
        if self.format == 'boolean':
            return 'Sí' if value else 'No'
        
        return str(value) if value else ''


def export_queryset(queryset, fields, filename, format='csv'):
    """
    Export queryset to CSV or Excel.
    
    Args:
        queryset: Django queryset
        fields: List of ExportField or dicts
        filename: Base filename (without extension)
        format: 'csv' or 'excel'
    """
    # Normalize fields
    export_fields = []
    for f in fields:
        if isinstance(f, ExportField):
            export_fields.append(f)
        elif isinstance(f, dict):
            export_fields.append(ExportField(**f))
        elif isinstance(f, str):
            export_fields.append(ExportField(f))
    
    if format == 'excel':
        return _export_excel(queryset, export_fields, filename)
    return _export_csv(queryset, export_fields, filename)


def _export_csv(queryset, fields, filename):
    """Export to CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    
    # Add BOM for Excel UTF-8 compatibility
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Header row
    writer.writerow([f.label for f in fields])
    
    # Data rows
    for obj in queryset:
        writer.writerow([f.get_value(obj) for f in fields])
    
    return response


def _export_excel(queryset, fields, filename):
    """Export to Excel."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        raise ImportError("Install openpyxl: pip install openpyxl")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Datos'
    
    # Header styling
    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)
    
    # Write headers
    for col, field in enumerate(fields, 1):
        cell = ws.cell(row=1, column=col, value=field.label)
        cell.fill = header_fill
        cell.font = header_font
    
    # Write data
    for row_idx, obj in enumerate(queryset, 2):
        for col_idx, field in enumerate(fields, 1):
            ws.cell(row=row_idx, column=col_idx, value=field.get_value(obj))
    
    # Auto-width columns
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column].width = min(max_length + 2, 50)
    
    # Create response
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    return response


class ExportMixin:
    """
    Mixin to add export functionality to list views.
    
    class PropertyListView(ExportMixin, NitroListView):
        export_fields = [
            ExportField('name', 'Nombre'),
            ExportField('rent_amount', 'Renta', format='currency'),
        ]
        export_filename = 'propiedades'
    """
    
    export_fields = []
    export_filename = 'export'
    export_formats = ['csv', 'excel']
    
    def get(self, request, *args, **kwargs):
        export_format = request.GET.get('export')
        if export_format and export_format in self.export_formats:
            return self.export(export_format)
        return super().get(request, *args, **kwargs)
    
    def export(self, format):
        queryset = self.get_filtered_queryset()
        return export_queryset(
            queryset,
            self.export_fields,
            self.export_filename,
            format
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['export_formats'] = self.export_formats
        return context
```

### Export Template

```django
{# Add to list templates #}
{% if export_formats %}
<div class="flex gap-2">
    {% for format in export_formats %}
    <a href="?export={{ format }}{% if request.GET.urlencode %}&{{ request.GET.urlencode }}{% endif %}"
       class="btn btn-secondary btn-sm">
        {% if format == 'csv' %}📄 CSV{% elif format == 'excel' %}📊 Excel{% endif %}
    </a>
    {% endfor %}
</div>
{% endif %}
```

---

## 10. SEO Helpers

### `nitro/seo.py`

```python
"""
Nitro 0.8 - SEO utilities.

Usage:
    class JobDetailView(SEOMixin, NitroModelView):
        model = Job
        
        def get_seo_title(self):
            return f"{self.object.title} - {self.object.company.name}"
        
        def get_seo_description(self):
            return self.object.description[:160]
        
        def get_structured_data(self):
            return JobPostingSchema(self.object).to_dict()
"""

import json
from django.utils.html import escape
from django.utils.safestring import mark_safe


class SEOMixin:
    """
    Mixin for SEO-optimized views.
    """
    
    seo_title = ''
    seo_description = ''
    seo_keywords = ''
    seo_image = ''
    seo_type = 'website'  # 'website', 'article', 'product', etc.
    
    def get_seo_title(self):
        return self.seo_title
    
    def get_seo_description(self):
        return self.seo_description
    
    def get_seo_keywords(self):
        return self.seo_keywords
    
    def get_seo_image(self):
        return self.seo_image
    
    def get_canonical_url(self):
        return self.request.build_absolute_uri()
    
    def get_structured_data(self):
        """Override to return Schema.org structured data dict."""
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['seo'] = {
            'title': self.get_seo_title(),
            'description': self.get_seo_description(),
            'keywords': self.get_seo_keywords(),
            'image': self.get_seo_image(),
            'canonical': self.get_canonical_url(),
            'type': self.seo_type,
            'structured_data': self.get_structured_data(),
        }
        return context


class BaseSchema:
    """Base class for Schema.org structured data."""
    
    schema_type = 'Thing'
    
    def __init__(self, obj=None):
        self.obj = obj
    
    def to_dict(self):
        """Return schema as dictionary."""
        return {
            '@context': 'https://schema.org',
            '@type': self.schema_type,
        }
    
    def to_json(self):
        """Return schema as JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def to_script(self):
        """Return schema as HTML script tag."""
        return mark_safe(
            f'<script type="application/ld+json">{self.to_json()}</script>'
        )


class OrganizationSchema(BaseSchema):
    """Organization schema for company pages."""
    
    schema_type = 'Organization'
    
    def to_dict(self):
        data = super().to_dict()
        if self.obj:
            data.update({
                'name': self.obj.name,
                'url': getattr(self.obj, 'website', ''),
                'logo': getattr(self.obj, 'logo_url', ''),
                'telephone': getattr(self.obj, 'phone', ''),
                'email': getattr(self.obj, 'email', ''),
            })
        return data


class JobPostingSchema(BaseSchema):
    """JobPosting schema for job listings (AplicaHR)."""
    
    schema_type = 'JobPosting'
    
    def to_dict(self):
        data = super().to_dict()
        if self.obj:
            data.update({
                'title': self.obj.title,
                'description': self.obj.description,
                'datePosted': self.obj.created_at.isoformat() if hasattr(self.obj, 'created_at') else '',
                'employmentType': getattr(self.obj, 'employment_type', 'FULL_TIME'),
                'hiringOrganization': {
                    '@type': 'Organization',
                    'name': self.obj.company.name if hasattr(self.obj, 'company') else '',
                },
                'jobLocation': {
                    '@type': 'Place',
                    'address': {
                        '@type': 'PostalAddress',
                        'addressLocality': getattr(self.obj, 'city', ''),
                        'addressCountry': 'DO',
                    }
                } if hasattr(self.obj, 'city') else None,
            })
            
            # Salary info
            if hasattr(self.obj, 'salary_min') and self.obj.salary_min:
                data['baseSalary'] = {
                    '@type': 'MonetaryAmount',
                    'currency': getattr(self.obj, 'currency', 'DOP'),
                    'value': {
                        '@type': 'QuantitativeValue',
                        'minValue': float(self.obj.salary_min),
                        'maxValue': float(self.obj.salary_max) if hasattr(self.obj, 'salary_max') else None,
                        'unitText': 'MONTH',
                    }
                }
        
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}


class RealEstateListingSchema(BaseSchema):
    """RealEstateListing schema for properties (Statuos)."""
    
    schema_type = 'RealEstateListing'
    
    def to_dict(self):
        data = super().to_dict()
        if self.obj:
            data.update({
                'name': self.obj.name,
                'description': getattr(self.obj, 'description', ''),
                'url': '',  # Set in view
                'address': {
                    '@type': 'PostalAddress',
                    'streetAddress': self.obj.address,
                    'addressCountry': 'DO',
                } if self.obj.address else None,
            })
            
            # Price
            if hasattr(self.obj, 'rent_amount') and self.obj.rent_amount:
                data['offers'] = {
                    '@type': 'Offer',
                    'price': float(self.obj.rent_amount),
                    'priceCurrency': getattr(self.obj, 'currency', 'DOP'),
                }
        
        return {k: v for k, v in data.items() if v is not None}


class BreadcrumbSchema(BaseSchema):
    """BreadcrumbList schema for navigation."""
    
    schema_type = 'BreadcrumbList'
    
    def __init__(self, items):
        """
        items: List of (name, url) tuples
        """
        self.items = items
    
    def to_dict(self):
        data = super().to_dict()
        data['itemListElement'] = [
            {
                '@type': 'ListItem',
                'position': i + 1,
                'name': name,
                'item': url,
            }
            for i, (name, url) in enumerate(self.items)
        ]
        return data
```

### SEO Template Tags

```django
{# In base.html head #}
{% if seo %}
<title>{{ seo.title|default:site_name }}</title>
<meta name="description" content="{{ seo.description }}">
{% if seo.keywords %}<meta name="keywords" content="{{ seo.keywords }}">{% endif %}
<link rel="canonical" href="{{ seo.canonical }}">

{# Open Graph #}
<meta property="og:title" content="{{ seo.title }}">
<meta property="og:description" content="{{ seo.description }}">
<meta property="og:type" content="{{ seo.type }}">
<meta property="og:url" content="{{ seo.canonical }}">
{% if seo.image %}<meta property="og:image" content="{{ seo.image }}">{% endif %}

{# Twitter #}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ seo.title }}">
<meta name="twitter:description" content="{{ seo.description }}">
{% if seo.image %}<meta name="twitter:image" content="{{ seo.image }}">{% endif %}

{# Structured Data #}
{% if seo.structured_data %}
<script type="application/ld+json">
{{ seo.structured_data|safe }}
</script>
{% endif %}
{% endif %}
```

---

## 11. Notification System

### `nitro/notifications.py`

```python
"""
Nitro 0.8 - Notification system.

Usage:
    from nitro.notifications import notify, notify_group
    
    # Single user
    notify(user, 'payment_received', 'Pago recibido', 
           f'Se recibió un pago de {amount}', 
           action_url=f'/payments/{payment.pk}/')
    
    # Group notification
    notify_group(company.users.all(), 'new_ticket', 'Nuevo ticket',
                 f'{tenant.name} reportó un problema')
"""

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Notification(models.Model):
    """In-app notification."""
    
    TYPE_CHOICES = [
        ('info', 'Información'),
        ('success', 'Éxito'),
        ('warning', 'Advertencia'),
        ('error', 'Error'),
    ]
    
    CATEGORY_CHOICES = [
        ('payment', 'Pagos'),
        ('lease', 'Contratos'),
        ('ticket', 'Tickets'),
        ('property', 'Propiedades'),
        ('system', 'Sistema'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='system')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Optional link to related object
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=255, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    action_url = models.CharField(max_length=500, blank=True)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Extra data
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['user', 'category', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user}"
    
    def mark_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


def notify(user, category, title, message, type='info', action_url='', 
           related_object=None, data=None):
    """
    Create a notification for a user.
    
    Args:
        user: User to notify
        category: Category (payment, lease, ticket, etc.)
        title: Short title
        message: Full message
        type: info/success/warning/error
        action_url: URL to link to
        related_object: Optional related model instance
        data: Optional extra data dict
    
    Returns:
        Notification instance
    """
    content_type = None
    object_id = ''
    
    if related_object:
        content_type = ContentType.objects.get_for_model(related_object)
        object_id = str(related_object.pk)
    
    return Notification.objects.create(
        user=user,
        type=type,
        category=category,
        title=title,
        message=message,
        content_type=content_type,
        object_id=object_id,
        action_url=action_url,
        data=data or {},
    )


def notify_group(users, category, title, message, **kwargs):
    """
    Create notifications for multiple users.
    
    Args:
        users: Queryset or list of users
        category: Category
        title: Title
        message: Message
        **kwargs: Same as notify()
    
    Returns:
        List of Notification instances
    """
    notifications = []
    
    content_type = None
    object_id = ''
    related_object = kwargs.get('related_object')
    
    if related_object:
        content_type = ContentType.objects.get_for_model(related_object)
        object_id = str(related_object.pk)
    
    for user in users:
        notifications.append(Notification(
            user=user,
            type=kwargs.get('type', 'info'),
            category=category,
            title=title,
            message=message,
            content_type=content_type,
            object_id=object_id,
            action_url=kwargs.get('action_url', ''),
            data=kwargs.get('data') or {},
        ))
    
    return Notification.objects.bulk_create(notifications)


def get_unread_count(user):
    """Get unread notification count for user."""
    return Notification.objects.filter(user=user, is_read=False).count()


def mark_all_read(user, category=None):
    """Mark all notifications as read."""
    from django.utils import timezone
    
    qs = Notification.objects.filter(user=user, is_read=False)
    if category:
        qs = qs.filter(category=category)
    
    qs.update(is_read=True, read_at=timezone.now())


class NotificationMixin:
    """
    Mixin to add notifications to views.
    
    Adds 'notifications' and 'unread_count' to context.
    """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['unread_notification_count'] = get_unread_count(self.request.user)
            context['recent_notifications'] = (
                Notification.objects
                .filter(user=self.request.user)
                .order_by('-created_at')[:10]
            )
        return context
```

### Notification Views

```python
# In your views.py

from django.http import JsonResponse
from nitro.notifications import Notification, mark_all_read, get_unread_count

class NotificationListView(LoginRequiredMixin, NitroListView):
    model = Notification
    template_name = 'notifications/list.html'
    partial_template = 'notifications/partials/list_content.html'
    paginate_by = 20
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


def notification_bell_partial(request):
    """HTMX partial for notification bell dropdown."""
    notifications = (
        Notification.objects
        .filter(user=request.user)
        .order_by('-created_at')[:10]
    )
    unread_count = get_unread_count(request.user)
    
    return render(request, 'notifications/partials/bell.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


def mark_all_notifications_read(request):
    """Mark all as read."""
    if request.method == 'POST':
        mark_all_read(request.user)
    return JsonResponse({'success': True})
```

### Notification Bell Template

```django
{# templates/notifications/partials/bell.html #}
<div class="relative" x-data="{ open: false }">
    <button @click="open = !open" class="relative p-2 text-gray-400 hover:text-gray-600">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
        </svg>
        {% if unread_count %}
        <span class="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-500 rounded-full">
            {{ unread_count }}
        </span>
        {% endif %}
    </button>
    
    <div x-show="open" @click.away="open = false" x-cloak
         class="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border z-50">
        
        <div class="flex items-center justify-between p-4 border-b">
            <span class="font-medium">Notificaciones</span>
            {% if unread_count %}
            <button hx-post="{% url 'mark_all_read' %}" hx-swap="none"
                    class="text-sm text-primary-600 hover:underline">
                Marcar todas leídas
            </button>
            {% endif %}
        </div>
        
        <div class="max-h-96 overflow-y-auto">
            {% for notification in notifications %}
            <a href="{{ notification.action_url|default:'#' }}"
               class="block p-4 hover:bg-gray-50 border-b last:border-b-0
                      {% if not notification.is_read %}bg-blue-50{% endif %}">
                <div class="flex gap-3">
                    <div class="flex-shrink-0">
                        {% if notification.type == 'success' %}✅
                        {% elif notification.type == 'warning' %}⚠️
                        {% elif notification.type == 'error' %}❌
                        {% else %}ℹ️{% endif %}
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-gray-900">{{ notification.title }}</p>
                        <p class="text-sm text-gray-500 truncate">{{ notification.message }}</p>
                        <p class="text-xs text-gray-400 mt-1">{{ notification.created_at|timesince }} ago</p>
                    </div>
                </div>
            </a>
            {% empty %}
            <div class="p-4 text-center text-gray-500">
                No hay notificaciones
            </div>
            {% endfor %}
        </div>
        
        <a href="{% url 'notification_list' %}" 
           class="block p-4 text-center text-sm text-primary-600 hover:bg-gray-50 border-t">
            Ver todas
        </a>
    </div>
</div>
```

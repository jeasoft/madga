# Nitro 0.8 - Framework Specification

> **Status:** Complete specification, ready for implementation  
> **Philosophy:** Server renders HTML, client swaps it. HTMX for server interactions, Alpine for local UI.

## 📁 Specification Files

| File | Contents |
|------|----------|
| `01-views.md` | Core views: NitroView, NitroListView, NitroModelView, NitroFormView, NitroCreateView, NitroUpdateView, NitroDeleteView |
| `02-models-mixins.md` | Model mixins: UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditModel + View mixins: CompanyMixin, PermissionRequiredMixin + Audit Trail system |
| `03-forms-wizards.md` | NitroFormMixin, NitroModelForm + Multi-step NitroWizard with WizardStep |
| `04-tables-filters.md` | Declarative NitroTable with Column/RowAction + NitroFilterSet with SearchFilter, SelectFilter, RangeFilter, DateRangeFilter |
| `05-exports-seo-notifications.md` | ExportMixin (CSV/Excel), SEOMixin + Schema.org schemas, Notification system |
| `06-template-tags.md` | Complete nitro_tags: HTMX actions, form fields, components, display filters |
| `07-components.md` | HTML templates: card, stats_card, empty_state, modal, dropdown, pagination, toast, file_upload, timeline, table |
| `08-javascript.md` | nitro.js (HTMX config, toasts) + alpine-components.js (fileUpload, clipboard, searchableSelect, etc.) |
| `09-utilities.md` | WhatsApp messages, currency formatting, date utilities |

---

## 🏗️ Framework Components

### Views
```
NitroView              → Base with HTMX helpers, toasts
├── NitroListView      → Search, filter, sort, pagination
├── NitroModelView     → Single object detail
├── NitroFormView      → Form handling
│   ├── NitroCreateView → Auto company/user assignment
│   └── NitroUpdateView → Edit existing
└── NitroDeleteView    → Soft delete support
```

### Model Mixins
```
UUIDMixin          → UUID primary key
TimestampMixin     → created_at, updated_at
UserTrackingMixin  → created_by, updated_by
SoftDeleteMixin    → is_deleted, soft_delete(), restore()
AuditModel         → Combines all above
AuditableMixin     → Change tracking with AuditLog
```

### View Mixins
```
CompanyMixin           → Multi-tenant scoping
PermissionRequiredMixin → Permission checking
OwnerRequiredMixin     → Object ownership
StaffRequiredMixin     → Staff only
CacheMixin             → Response caching
```

### Template Tags
```
HTMX:
  {% nitro_search %}       → Search input with debounce
  {% nitro_filter %}       → Filter dropdown
  {% nitro_pagination %}   → Paginated navigation
  {% nitro_sort %}         → Sortable column header
  {% nitro_delete %}       → Delete attributes

Forms:
  {% nitro_field %}        → Styled form field
  {% nitro_select %}       → Searchable select

Components:
  {% nitro_tabs %}         → Tab navigation
  {% nitro_empty_state %}  → No data state
  {% nitro_stats_card %}   → Statistics card
  {% nitro_avatar %}       → User avatar

Filters:
  {{ value|status_badge }} → Status with color
  {{ amount|currency }}    → Currency formatting
  {{ phone|phone_format }} → Phone formatting
  {{ date|relative_date }} → "Hoy", "Ayer", etc.
  {{ phone|whatsapp_link }}→ WhatsApp URL
```

### Alpine Components
```
toastManager()       → Toast notifications
clipboard()          → Copy to clipboard
fileUpload()         → Drag & drop files
charCounter()        → Character limit
searchableSelect()   → Select2-like
confirmAction()      → Confirm modal
infiniteScroll()     → Load more
currencyInput()      → Currency formatting
phoneInput()         → Phone formatting
darkMode()           → Theme toggle
dirtyForm()          → Unsaved changes warning
```

---

## 🚀 Quick Start

### 1. Install in Django project

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'nitro',
]

# Optional: Nitro configuration
NITRO = {
    'DEFAULT_PAGINATION': 20,
    'TOAST_DURATION': 5000,
}
```

### 2. Include static files

```django
{# base.html #}
{% load static %}

<head>
    <script src="https://unpkg.com/htmx.org@2.0.0"></script>
    <script src="{% static 'nitro/nitro.js' %}"></script>
    <script src="{% static 'nitro/alpine-components.js' %}"></script>
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>

<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
    {% include "nitro/components/toast.html" %}
    {% block content %}{% endblock %}
</body>
```

### 3. Create a view

```python
# views.py
from nitro.views import NitroListView
from nitro.mixins import CompanyMixin

class PropertyListView(CompanyMixin, NitroListView):
    model = Property
    template_name = 'properties/list.html'
    partial_template = 'properties/partials/list_content.html'
    search_fields = ['name', 'address']
    filter_fields = ['status']
    sortable_fields = ['name', 'rent_amount', 'created_at']
    paginate_by = 20
```

### 4. Create templates

```django
{# properties/list.html #}
{% extends "base.html" %}
{% load nitro_tags %}

{% block content %}
<div class="p-4">
    <div class="flex justify-between mb-4">
        {% nitro_search target='#property-list' %}
        <a href="{% url 'property_create' %}" class="btn btn-primary">+ Nueva</a>
    </div>
    
    <div id="property-list">
        {% include "properties/partials/list_content.html" %}
    </div>
</div>
{% endblock %}
```

```django
{# properties/partials/list_content.html #}
{% load nitro_tags %}

{% for property in object_list %}
<div class="card mb-3 p-4">
    <h3>{{ property.name }}</h3>
    <p>{{ property.address }}</p>
    <p>{{ property.rent_amount|currency:property.currency }}</p>
    {{ property.status|status_badge }}
</div>
{% empty %}
{% nitro_empty_state icon="🏠" title="Sin propiedades" action_url="/properties/create/" action_text="Crear primera" %}
{% endfor %}

{% nitro_pagination page_obj target='#property-list' %}
```

---

## 📋 Implementation Checklist

### Core (Required)
- [ ] `nitro/views.py` - All view classes
- [ ] `nitro/models.py` - Model mixins
- [ ] `nitro/mixins.py` - View mixins
- [ ] `nitro/templatetags/nitro_tags.py` - All template tags
- [ ] `nitro/static/nitro/nitro.js` - Core JavaScript
- [ ] `nitro/templates/nitro/components/` - All HTML components

### Forms & Wizards
- [ ] `nitro/forms.py` - Form mixins
- [ ] `nitro/wizards.py` - Wizard system

### Advanced Features
- [ ] `nitro/tables.py` - Declarative tables
- [ ] `nitro/filters.py` - Faceted filters
- [ ] `nitro/exports.py` - CSV/Excel export
- [ ] `nitro/audit.py` - Audit trail
- [ ] `nitro/notifications.py` - Notification system
- [ ] `nitro/seo.py` - SEO helpers

### Utilities
- [ ] `nitro/utils/whatsapp.py` - WhatsApp messages
- [ ] `nitro/utils/currency.py` - Currency formatting
- [ ] `nitro/utils/dates.py` - Date utilities

### JavaScript
- [ ] `nitro/static/nitro/alpine-components.js` - Alpine components

---

## 🔄 Migration from Nitro 0.7

Key changes:
1. **No Pydantic** - Use Django ModelForms
2. **No JSON APIs** - Server renders complete HTML
3. **Alpine for UI only** - No data fetching, just local state
4. **HTMX for everything** - Search, filter, pagination, forms

```python
# OLD (0.7)
class PropertyAPI(NitroAPI):
    schema = PropertySchema

# NEW (0.8)
class PropertyListView(CompanyMixin, NitroListView):
    model = Property
    template_name = 'properties/list.html'
```

---

## 📦 File Structure

```
nitro/
├── __init__.py
├── apps.py
├── views.py
├── forms.py
├── tables.py
├── filters.py
├── wizards.py
├── exports.py
├── seo.py
├── audit.py
├── notifications.py
├── models.py
├── mixins.py
├── utils/
│   ├── __init__.py
│   ├── whatsapp.py
│   ├── currency.py
│   └── dates.py
├── templatetags/
│   └── nitro_tags.py
├── static/nitro/
│   ├── nitro.js
│   └── alpine-components.js
└── templates/nitro/
    └── components/
        ├── card.html
        ├── stats_card.html
        ├── empty_state.html
        ├── confirm_modal.html
        ├── modal.html
        ├── dropdown.html
        ├── pagination.html
        ├── search_bar.html
        ├── filter_select.html
        ├── form_field.html
        ├── select_field.html
        ├── table.html
        ├── file_upload.html
        ├── timeline.html
        ├── avatar.html
        ├── badge.html
        ├── toast.html
        └── loading.html
```

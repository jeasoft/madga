# Nitro 0.8 - Framework Completo

> **Version:** 0.8.0  
> **Philosophy:** Server renders HTML, client swaps it.

## Estructura de Archivos

```
nitro/
├── __init__.py
├── apps.py
├── conf.py                    # Configuración
│
├── views.py                   # NitroView, NitroListView, etc.
├── forms.py                   # NitroFormMixin, NitroModelForm
├── tables.py                  # NitroTable declarativo
├── filters.py                 # NitroFilterSet faceted
├── wizards.py                 # NitroWizard multi-step
├── exports.py                 # CSV/Excel export
├── seo.py                     # SEO helpers
├── audit.py                   # Audit trail
├── notifications.py           # Sistema de notificaciones
│
├── models.py                  # AuditModel, SoftDeleteMixin
├── mixins.py                  # CompanyMixin, etc.
├── serializers.py             # Model → dict
│
├── utils/
│   ├── __init__.py
│   ├── whatsapp.py            # WhatsApp messages
│   ├── currency.py            # Format currency
│   └── dates.py               # Date utilities
│
├── templatetags/
│   └── nitro_tags.py          # Todos los tags
│
├── static/nitro/
│   ├── nitro.js               # HTMX config, toasts
│   └── alpine-components.js   # Alpine reusables
│
└── templates/nitro/
    └── components/            # Partials reutilizables
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

---

## 1. Views Base

### `nitro/views.py`

```python
"""
Nitro 0.8 - Server-rendered views with HTMX + Alpine.
"""

import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views.generic import TemplateView


class NitroView(LoginRequiredMixin, TemplateView):
    """
    Base view for all Nitro views.
    
    Features:
    - HTMX detection
    - Automatic full-page vs partial rendering
    - Toast notifications
    - HTMX redirect/refresh helpers
    """
    
    template_name = None
    partial_template = None
    
    @property
    def is_htmx(self):
        return getattr(self.request, 'htmx', False) and self.request.htmx
    
    def get_template_names(self):
        if self.is_htmx and self.partial_template:
            return [self.partial_template]
        return [self.template_name]
    
    def render_partial(self, template=None, context=None):
        if context is None:
            context = self.get_context_data()
        template = template or self.partial_template or self.template_name
        html = render_to_string(template, context, request=self.request)
        return HttpResponse(html)
    
    # HTMX Helpers
    def htmx_redirect(self, url):
        response = HttpResponse(status=204)
        response['HX-Redirect'] = url
        return response
    
    def htmx_refresh(self):
        response = HttpResponse(status=204)
        response['HX-Refresh'] = 'true'
        return response
    
    def htmx_trigger(self, event, detail=None):
        response = HttpResponse(status=204)
        if detail:
            response['HX-Trigger'] = json.dumps({event: detail})
        else:
            response['HX-Trigger'] = event
        return response
    
    # Toast Notifications
    def toast(self, message, level='success'):
        response = HttpResponse(status=204)
        response['HX-Trigger'] = json.dumps({
            'showToast': {'message': message, 'type': level}
        })
        return response
    
    def toast_with_html(self, html, message, level='success'):
        response = HttpResponse(html)
        response['HX-Trigger'] = json.dumps({
            'showToast': {'message': message, 'type': level}
        })
        return response
    
    def success(self, message):
        return self.toast(message, 'success')
    
    def error(self, message):
        return self.toast(message, 'error')
    
    def warning(self, message):
        return self.toast(message, 'warning')
    
    def info(self, message):
        return self.toast(message, 'info')


class NitroListView(NitroView):
    """
    List with search, filter, sort, pagination.
    
    class PropertyListView(CompanyMixin, NitroListView):
        model = Property
        search_fields = ['name', 'address']
        filter_fields = ['status', 'property_type']
        sortable_fields = ['name', 'rent_amount', 'created_at']
        paginate_by = 20
    """
    
    model = None
    search_fields = []
    filter_fields = []
    sortable_fields = []
    paginate_by = 20
    default_sort = '-created_at'
    select_related = []
    prefetch_related = []
    
    def get_queryset(self):
        qs = self.model.objects.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if self.prefetch_related:
            qs = qs.prefetch_related(*self.prefetch_related)
        return qs
    
    def apply_search(self, qs):
        query = self.request.GET.get('q', '').strip()
        if not query or not self.search_fields:
            return qs
        
        q_objects = Q()
        for field in self.search_fields:
            try:
                q_objects |= Q(**{f'{field}__unaccent__icontains': query})
            except:
                q_objects |= Q(**{f'{field}__icontains': query})
        return qs.filter(q_objects)
    
    def apply_filters(self, qs):
        for field in self.filter_fields:
            value = self.request.GET.get(field, '').strip()
            if value:
                qs = qs.filter(**{field: value})
        return qs
    
    def apply_sort(self, qs):
        sort = self.request.GET.get('sort', '').strip()
        if sort:
            field = sort.lstrip('-')
            if field in self.sortable_fields:
                return qs.order_by(sort)
        if self.default_sort:
            return qs.order_by(self.default_sort)
        return qs
    
    def get_filtered_queryset(self):
        qs = self.get_queryset()
        qs = self.apply_search(qs)
        qs = self.apply_filters(qs)
        qs = self.apply_sort(qs)
        return qs
    
    def get_page_obj(self, queryset=None):
        if queryset is None:
            queryset = self.get_filtered_queryset()
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page', 1)
        return paginator.get_page(page)
    
    def get_filter_options(self):
        """Override to provide filter dropdown options."""
        return {}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = self.get_page_obj()
        context.update({
            'page_obj': page_obj,
            'object_list': page_obj.object_list,
            'filter_options': self.get_filter_options(),
            'current_filters': {f: self.request.GET.get(f, '') for f in self.filter_fields},
            'current_search': self.request.GET.get('q', ''),
            'current_sort': self.request.GET.get('sort', self.default_sort or ''),
            'total_count': page_obj.paginator.count,
        })
        return context


class NitroModelView(NitroView):
    """Single model instance detail."""
    
    model = None
    pk_url_kwarg = 'pk'
    context_object_name = 'object'
    
    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(self.model, pk=pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context['object'] = obj
        context[self.context_object_name] = obj
        return context


class NitroFormView(NitroView):
    """Form handling with HTMX support."""
    
    form_class = None
    success_url = None
    success_message = 'Guardado exitosamente'
    
    def get_form_kwargs(self):
        kwargs = {}
        if self.request.method in ('POST', 'PUT', 'PATCH'):
            kwargs['data'] = self.request.POST
            kwargs['files'] = self.request.FILES
        return kwargs
    
    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.form_class
        return form_class(**self.get_form_kwargs())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.get_form()
        return context
    
    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())
    
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)
    
    def form_valid(self, form):
        self.object = form.save()
        if self.is_htmx:
            return self.success(self.success_message)
        return redirect(self.get_success_url())
    
    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        if self.success_url:
            return self.success_url
        raise NotImplementedError


class NitroCreateView(NitroFormView):
    """Create with auto company/user assignment."""
    
    model = None
    
    def form_valid(self, form):
        obj = form.save(commit=False)
        
        if hasattr(self, 'organization') and hasattr(obj, 'company'):
            obj.company = self.organization
        
        if hasattr(obj, 'created_by'):
            obj.created_by = self.request.user
        
        obj.save()
        form.save_m2m()
        self.object = obj
        
        if self.is_htmx:
            return self.success(self.success_message)
        return redirect(self.get_success_url())


class NitroUpdateView(NitroFormView):
    """Update existing instance."""
    
    model = None
    pk_url_kwarg = 'pk'
    
    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(self.model, pk=pk)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.get_object()
        return context


class NitroDeleteView(NitroView):
    """Delete with soft-delete support."""
    
    model = None
    pk_url_kwarg = 'pk'
    success_url = None
    success_message = 'Eliminado exitosamente'
    
    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(self.model, pk=pk)
    
    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        
        if hasattr(obj, 'soft_delete'):
            obj.soft_delete(user=request.user)
        else:
            obj.delete()
        
        if self.is_htmx:
            return self.success(self.success_message)
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        if self.success_url:
            return self.success_url
        raise NotImplementedError
```

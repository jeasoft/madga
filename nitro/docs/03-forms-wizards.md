# Nitro 0.8 - Forms y Wizards

## 5. Form Utilities

### `nitro/forms.py`

```python
"""
Nitro 0.8 - Form utilities.
"""

from django import forms
from django.forms.widgets import (
    TextInput, NumberInput, EmailInput, URLInput, 
    PasswordInput, Textarea, Select, SelectMultiple,
    CheckboxInput, FileInput, DateInput, DateTimeInput,
    TimeInput
)


# Tailwind CSS classes for form widgets
TAILWIND_CLASSES = {
    'input': 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors',
    'input_error': 'w-full px-3 py-2 border border-red-500 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-red-500',
    'textarea': 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none',
    'select': 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white',
    'checkbox': 'h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500',
    'file': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100',
}


class NitroFormMixin:
    """
    Mixin that applies Tailwind classes to all form fields.
    
    Usage:
        class PropertyForm(NitroFormMixin, forms.ModelForm):
            class Meta:
                model = Property
                fields = ['name', 'address', 'rent_amount']
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind_classes()
    
    def apply_tailwind_classes(self):
        """Apply Tailwind classes to all fields."""
        for field_name, field in self.fields.items():
            widget = field.widget
            
            # Determine widget type and apply appropriate classes
            if isinstance(widget, (TextInput, NumberInput, EmailInput, URLInput, PasswordInput, DateInput, DateTimeInput, TimeInput)):
                self._add_class(widget, TAILWIND_CLASSES['input'])
            elif isinstance(widget, Textarea):
                self._add_class(widget, TAILWIND_CLASSES['textarea'])
            elif isinstance(widget, (Select, SelectMultiple)):
                self._add_class(widget, TAILWIND_CLASSES['select'])
            elif isinstance(widget, CheckboxInput):
                self._add_class(widget, TAILWIND_CLASSES['checkbox'])
            elif isinstance(widget, FileInput):
                self._add_class(widget, TAILWIND_CLASSES['file'])
            
            # Add placeholder if not set
            if hasattr(widget, 'attrs') and 'placeholder' not in widget.attrs:
                if field.label:
                    widget.attrs['placeholder'] = field.label
    
    def _add_class(self, widget, css_class):
        """Add CSS class to widget."""
        existing = widget.attrs.get('class', '')
        widget.attrs['class'] = f'{existing} {css_class}'.strip()


class NitroModelForm(NitroFormMixin, forms.ModelForm):
    """
    ModelForm with Tailwind styling.
    
    Usage:
        class PropertyForm(NitroModelForm):
            class Meta:
                model = Property
                fields = ['name', 'address']
    """
    pass


class NitroForm(NitroFormMixin, forms.Form):
    """
    Regular Form with Tailwind styling.
    """
    pass


# Common form field configurations
class PhoneField(forms.CharField):
    """Phone number field with formatting."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 20)
        kwargs.setdefault('widget', TextInput(attrs={
            'type': 'tel',
            'placeholder': '(809) 555-1234',
        }))
        super().__init__(*args, **kwargs)


class CedulaField(forms.CharField):
    """Dominican cedula field."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 13)
        kwargs.setdefault('widget', TextInput(attrs={
            'placeholder': '001-1234567-8',
        }))
        super().__init__(*args, **kwargs)
    
    def clean(self, value):
        value = super().clean(value)
        if value:
            # Remove dashes and validate format
            digits = value.replace('-', '')
            if len(digits) != 11 or not digits.isdigit():
                raise forms.ValidationError('Formato de cédula inválido')
        return value


class CurrencyField(forms.DecimalField):
    """Currency amount field."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_digits', 12)
        kwargs.setdefault('decimal_places', 2)
        kwargs.setdefault('min_value', 0)
        kwargs.setdefault('widget', NumberInput(attrs={
            'step': '0.01',
            'min': '0',
        }))
        super().__init__(*args, **kwargs)
```

---

## 6. Multi-Step Wizard

### `nitro/wizards.py`

```python
"""
Nitro 0.8 - Multi-step form wizard.

Supports:
- Multiple steps with individual forms
- Session-based data storage
- Back/forward navigation
- Step validation
- Final submission
"""

from django.shortcuts import redirect
from django.urls import reverse
from .views import NitroView


class WizardStep:
    """
    Define a wizard step.
    
    step = WizardStep(
        name='property',
        form_class=PropertyForm,
        template='wizard/property_step.html',
        title='Datos de la Propiedad',
    )
    """
    
    def __init__(self, name, form_class=None, template=None, title='', 
                 skip_allowed=False, condition=None):
        self.name = name
        self.form_class = form_class
        self.template = template
        self.title = title
        self.skip_allowed = skip_allowed
        self.condition = condition  # Callable that returns True if step should show


class NitroWizard(NitroView):
    """
    Multi-step form wizard.
    
    Usage:
        class PropertyWizard(NitroWizard):
            wizard_name = 'property_wizard'
            steps = [
                WizardStep('type', PropertyTypeForm, 'wizard/type.html', 'Tipo'),
                WizardStep('details', PropertyDetailsForm, 'wizard/details.html', 'Detalles'),
                WizardStep('tenant', TenantForm, 'wizard/tenant.html', 'Inquilino', skip_allowed=True),
                WizardStep('confirm', None, 'wizard/confirm.html', 'Confirmar'),
            ]
            
            def done(self, wizard_data):
                # Create all objects
                property = Property.objects.create(**wizard_data['details'])
                if wizard_data.get('tenant'):
                    tenant = Tenant.objects.create(**wizard_data['tenant'])
                return redirect('property_detail', pk=property.pk)
    """
    
    wizard_name = 'wizard'
    steps = []
    template_name = 'nitro/wizard/base.html'
    done_url = '/'
    
    @property
    def session_key(self):
        return f'wizard_{self.wizard_name}'
    
    def get_wizard_data(self):
        """Get all wizard data from session."""
        return self.request.session.get(self.session_key, {})
    
    def save_wizard_data(self, data):
        """Save wizard data to session."""
        self.request.session[self.session_key] = data
        self.request.session.modified = True
    
    def clear_wizard_data(self):
        """Clear wizard data from session."""
        if self.session_key in self.request.session:
            del self.request.session[self.session_key]
    
    def get_step_data(self, step_name):
        """Get data for a specific step."""
        return self.get_wizard_data().get(step_name, {})
    
    def save_step_data(self, step_name, data):
        """Save data for a specific step."""
        wizard_data = self.get_wizard_data()
        wizard_data[step_name] = data
        self.save_wizard_data(wizard_data)
    
    def get_active_steps(self):
        """Get list of steps that should be shown (based on conditions)."""
        wizard_data = self.get_wizard_data()
        active = []
        for step in self.steps:
            if step.condition is None or step.condition(wizard_data):
                active.append(step)
        return active
    
    def get_current_step_index(self):
        """Get current step index from URL or default to 0."""
        step_name = self.kwargs.get('step')
        if step_name:
            for i, step in enumerate(self.get_active_steps()):
                if step.name == step_name:
                    return i
        return 0
    
    def get_current_step(self):
        """Get current WizardStep object."""
        steps = self.get_active_steps()
        index = self.get_current_step_index()
        if 0 <= index < len(steps):
            return steps[index]
        return steps[0] if steps else None
    
    def get_form(self, step=None):
        """Get form for current or specified step."""
        if step is None:
            step = self.get_current_step()
        
        if not step or not step.form_class:
            return None
        
        form_kwargs = self.get_form_kwargs(step)
        return step.form_class(**form_kwargs)
    
    def get_form_kwargs(self, step):
        """Get form kwargs, pre-populated with saved data."""
        kwargs = {'initial': self.get_step_data(step.name)}
        
        if self.request.method == 'POST':
            kwargs['data'] = self.request.POST
            kwargs['files'] = self.request.FILES
        
        return kwargs
    
    def get_template_names(self):
        """Return step-specific template or default."""
        step = self.get_current_step()
        if step and step.template:
            return [step.template]
        return [self.template_name]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        steps = self.get_active_steps()
        current_index = self.get_current_step_index()
        current_step = self.get_current_step()
        
        context.update({
            'wizard_name': self.wizard_name,
            'steps': steps,
            'current_step': current_step,
            'current_step_index': current_index,
            'total_steps': len(steps),
            'is_first_step': current_index == 0,
            'is_last_step': current_index == len(steps) - 1,
            'progress_percent': int((current_index / max(len(steps) - 1, 1)) * 100),
            'wizard_data': self.get_wizard_data(),
            'form': self.get_form(),
        })
        return context
    
    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('wizard_action', 'next')
        
        if action == 'cancel':
            return self.cancel()
        
        if action == 'back':
            return self.go_back()
        
        if action == 'skip':
            return self.skip_step()
        
        # Validate current step
        form = self.get_form()
        if form:
            if not form.is_valid():
                return self.render_to_response(self.get_context_data(form=form))
            
            # Save form data
            self.save_step_data(self.get_current_step().name, form.cleaned_data)
        
        # Go to next step or finish
        if action == 'finish' or self.is_last_step():
            return self.done(self.get_wizard_data())
        
        return self.go_next()
    
    def is_last_step(self):
        steps = self.get_active_steps()
        return self.get_current_step_index() >= len(steps) - 1
    
    def go_next(self):
        """Navigate to next step."""
        steps = self.get_active_steps()
        next_index = self.get_current_step_index() + 1
        if next_index < len(steps):
            return redirect(self.get_step_url(steps[next_index].name))
        return self.done(self.get_wizard_data())
    
    def go_back(self):
        """Navigate to previous step."""
        steps = self.get_active_steps()
        prev_index = self.get_current_step_index() - 1
        if prev_index >= 0:
            return redirect(self.get_step_url(steps[prev_index].name))
        return redirect(self.get_step_url(steps[0].name))
    
    def skip_step(self):
        """Skip current step if allowed."""
        current = self.get_current_step()
        if current and current.skip_allowed:
            return self.go_next()
        return self.render_to_response(self.get_context_data())
    
    def cancel(self):
        """Cancel wizard and clear data."""
        self.clear_wizard_data()
        return redirect(self.get_cancel_url())
    
    def get_step_url(self, step_name):
        """Get URL for a specific step. Override if needed."""
        return f'{self.request.path}?step={step_name}'
    
    def get_cancel_url(self):
        """URL to redirect on cancel."""
        return '/'
    
    def done(self, wizard_data):
        """
        Called when wizard is complete.
        
        Override to handle the final submission.
        Must return an HttpResponse (usually redirect).
        """
        raise NotImplementedError("Subclasses must implement done()")
```

### Wizard Template Example

```django
{# templates/nitro/wizard/base.html #}
{% extends "base.html" %}
{% load nitro_tags %}

{% block content %}
<div class="max-w-2xl mx-auto p-4">
    
    {# Progress #}
    <div class="mb-8">
        <div class="flex justify-between items-center mb-2">
            <span class="text-sm text-gray-500">Paso {{ current_step_index|add:1 }} de {{ total_steps }}</span>
            <span class="text-sm text-gray-500">{{ progress_percent }}%</span>
        </div>
        <div class="h-2 bg-gray-200 rounded-full">
            <div class="h-2 bg-primary-600 rounded-full transition-all" 
                 style="width: {{ progress_percent }}%"></div>
        </div>
    </div>
    
    {# Step indicators #}
    <div class="flex justify-center gap-2 mb-8">
        {% for step in steps %}
        <div class="flex items-center">
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                {% if forloop.counter0 < current_step_index %}bg-green-500 text-white
                {% elif forloop.counter0 == current_step_index %}bg-primary-600 text-white
                {% else %}bg-gray-200 text-gray-500{% endif %}">
                {% if forloop.counter0 < current_step_index %}✓{% else %}{{ forloop.counter }}{% endif %}
            </div>
            {% if not forloop.last %}
            <div class="w-8 h-1 {% if forloop.counter0 < current_step_index %}bg-green-500{% else %}bg-gray-200{% endif %}"></div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    {# Step title #}
    <h2 class="text-xl font-bold text-center mb-6">{{ current_step.title }}</h2>
    
    {# Form #}
    <form method="post" enctype="multipart/form-data">
        {% csrf_token %}
        
        {% if form %}
        <div class="space-y-4 mb-8">
            {% for field in form %}
                {% nitro_field field %}
            {% endfor %}
        </div>
        {% else %}
        {# Confirmation step - show summary #}
        <div class="bg-gray-50 rounded-xl p-6 mb-8">
            {% block wizard_summary %}
            <pre>{{ wizard_data|pprint }}</pre>
            {% endblock %}
        </div>
        {% endif %}
        
        {# Navigation buttons #}
        <div class="flex justify-between">
            <div>
                {% if not is_first_step %}
                <button type="submit" name="wizard_action" value="back" 
                        class="btn btn-secondary">
                    ← Atrás
                </button>
                {% endif %}
            </div>
            
            <div class="flex gap-2">
                {% if current_step.skip_allowed %}
                <button type="submit" name="wizard_action" value="skip"
                        class="btn btn-secondary">
                    Saltar
                </button>
                {% endif %}
                
                {% if is_last_step %}
                <button type="submit" name="wizard_action" value="finish"
                        class="btn btn-primary">
                    Finalizar ✓
                </button>
                {% else %}
                <button type="submit" name="wizard_action" value="next"
                        class="btn btn-primary">
                    Siguiente →
                </button>
                {% endif %}
            </div>
        </div>
        
        {# Cancel link #}
        <div class="text-center mt-4">
            <button type="submit" name="wizard_action" value="cancel"
                    class="text-sm text-gray-500 hover:text-gray-700">
                Cancelar
            </button>
        </div>
    </form>
</div>
{% endblock %}
```

### Wizard Usage Example

```python
# views.py
from nitro.wizards import NitroWizard, WizardStep
from .forms import PropertyTypeForm, PropertyDetailsForm, TenantForm

class PropertySetupWizard(CompanyMixin, NitroWizard):
    wizard_name = 'property_setup'
    
    steps = [
        WizardStep(
            name='type',
            form_class=PropertyTypeForm,
            template='wizard/property_type.html',
            title='¿Qué tipo de propiedad?',
        ),
        WizardStep(
            name='details',
            form_class=PropertyDetailsForm,
            template='wizard/property_details.html',
            title='Detalles de la propiedad',
        ),
        WizardStep(
            name='tenant',
            form_class=TenantForm,
            template='wizard/tenant.html',
            title='¿Tiene inquilino?',
            skip_allowed=True,
            condition=lambda data: data.get('type', {}).get('has_tenant', True),
        ),
        WizardStep(
            name='confirm',
            form_class=None,
            template='wizard/confirm.html',
            title='Confirmar',
        ),
    ]
    
    def done(self, wizard_data):
        # Create property
        property = Property.objects.create(
            company=self.organization,
            created_by=self.request.user,
            **wizard_data['details'],
        )
        
        # Create tenant if provided
        if wizard_data.get('tenant'):
            tenant = Tenant.objects.create(
                company=self.organization,
                created_by=self.request.user,
                **wizard_data['tenant'],
            )
            # Create lease...
        
        self.clear_wizard_data()
        return redirect('property_detail', pk=property.pk)
    
    def get_cancel_url(self):
        return reverse('property_list')
```

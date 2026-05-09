"""
Nitro 0.8 - Form utilities.

Provides NitroFormMixin, NitroModelForm, and NitroForm that automatically
apply Tailwind CSS classes to all form widgets. Also includes custom field
types for Dominican Republic-specific formats (phone, cedula, currency).

Usage:
    class PropertyForm(NitroModelForm):
        class Meta:
            model = Property
            fields = ['name', 'address', 'rent_amount']

    # All widgets automatically get Tailwind classes.
    # You only need to declare widgets for non-default widget types
    # or extra attrs (type='date', rows=3, min=0, etc.)
"""

from django import forms
from django.forms.widgets import (
    TextInput, NumberInput, EmailInput, URLInput,
    PasswordInput, Textarea, Select, SelectMultiple,
    CheckboxInput, FileInput, DateInput, DateTimeInput,
    TimeInput,
)


# Tailwind CSS classes for form widgets (Mint design system)
TAILWIND_CLASSES = {
    'input': (
        'w-full px-4 py-2.5 border border-surface-200 rounded-xl text-sm '
        'text-surface-900 placeholder-surface-400 '
        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 '
        'transition-all'
    ),
    'input_error': (
        'w-full px-4 py-2.5 border border-red-300 rounded-xl text-sm '
        'text-surface-900 bg-red-50 '
        'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500'
    ),
    'textarea': (
        'w-full px-4 py-2.5 border border-surface-200 rounded-xl text-sm '
        'text-surface-900 placeholder-surface-400 '
        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 '
        'resize-none transition-all'
    ),
    'select': (
        'w-full px-4 py-2.5 border border-surface-200 rounded-xl text-sm '
        'text-surface-900 bg-white '
        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 '
        'transition-all'
    ),
    'checkbox': (
        'h-4 w-4 text-primary-600 border-surface-300 rounded '
        'focus:ring-primary-500'
    ),
    'file': (
        'w-full text-sm text-surface-500 file:mr-4 file:py-2 file:px-4 '
        'file:rounded-xl file:border-0 file:text-sm file:font-medium '
        'file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100'
    ),
}


class NitroFormMixin:
    """
    Mixin that applies Tailwind classes to all form fields automatically.

    Usage:
        class PropertyForm(NitroFormMixin, forms.ModelForm):
            class Meta:
                model = Property
                fields = ['name', 'address', 'rent_amount']
    """

    def __init__(self, *args, **kwargs):
        # Pop company kwarg if passed (used by views for company-aware forms)
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        self.apply_tailwind_classes()

    def apply_tailwind_classes(self):
        """Apply Tailwind classes to all fields based on widget type."""
        for field_name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, (TextInput, NumberInput, EmailInput, URLInput,
                                   PasswordInput, DateInput, DateTimeInput, TimeInput)):
                self._add_class(widget, TAILWIND_CLASSES['input'])
            elif isinstance(widget, Textarea):
                self._add_class(widget, TAILWIND_CLASSES['textarea'])
            elif isinstance(widget, (Select, SelectMultiple)):
                self._add_class(widget, TAILWIND_CLASSES['select'])
            elif isinstance(widget, CheckboxInput):
                self._add_class(widget, TAILWIND_CLASSES['checkbox'])
            elif isinstance(widget, FileInput):
                self._add_class(widget, TAILWIND_CLASSES['file'])

            # Add placeholder from label if not already set
            if hasattr(widget, 'attrs') and 'placeholder' not in widget.attrs:
                if field.label:
                    widget.attrs['placeholder'] = field.label

    def _add_class(self, widget, css_class):
        """Add CSS class to widget, preserving any existing classes."""
        existing = widget.attrs.get('class', '')
        widget.attrs['class'] = f'{existing} {css_class}'.strip()


class NitroModelForm(NitroFormMixin, forms.ModelForm):
    """
    ModelForm with automatic Tailwind styling.

    Usage:
        class PropertyForm(NitroModelForm):
            class Meta:
                model = Property
                fields = ['name', 'address']
    """
    pass


class NitroForm(NitroFormMixin, forms.Form):
    """
    Regular Form with automatic Tailwind styling.
    """
    pass


class CompanyFilteredFormMixin:
    """
    Mixin that auto-filters FK querysets by company.

    Eliminates repetitive __init__ overrides that filter related model
    querysets by the current company.

    Usage:
        class LeaseForm(CompanyFilteredFormMixin, NitroModelForm):
            company_filtered_fields = {
                'property': Property,
                'tenant': Tenant,
            }
            class Meta:
                model = Lease
                fields = ['property', 'tenant', 'start_date', 'end_date']

    The mixin relies on NitroFormMixin (or any parent) setting self.company
    from kwargs. It must appear BEFORE NitroModelForm in the MRO so its
    __init__ runs after self.company is set.
    """

    company_filtered_fields = {}  # {'field_name': ModelClass}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.company:
            for field_name, model_class in self.company_filtered_fields.items():
                if field_name in self.fields:
                    self.fields[field_name].queryset = (
                        model_class.objects.filter(company=self.company)
                    )


# =============================================================================
# Custom Field Types (Dominican Republic)
# =============================================================================

class PhoneField(forms.CharField):
    """Phone number field with DR formatting and normalization."""

    # Valid Dominican area codes
    DR_AREA_CODES = {'809', '829', '849'}

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 20)
        kwargs.setdefault('widget', TextInput(attrs={
            'type': 'tel',
            'placeholder': '(809) 555-1234',
        }))
        super().__init__(*args, **kwargs)

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return value

        # Strip to digits only
        digits = ''.join(c for c in value if c.isdigit())

        # Remove leading country code
        if digits.startswith('1') and len(digits) == 11:
            digits = digits[1:]
        elif digits.startswith('001') and len(digits) == 13:
            digits = digits[3:]
        elif digits.startswith('+1'):
            digits = digits[2:]

        if len(digits) == 10:
            # Format as (809) 555-1234
            return f'({digits[:3]}) {digits[3:6]}-{digits[6:]}'

        # If not 10 digits, return cleaned but unformatted (international numbers)
        return value


def validate_cedula_checkdigit(cedula: str) -> bool:
    """
    Validate Dominican cédula check digit using Luhn-like algorithm.

    The cédula format is: XXX-XXXXXXX-D where D is the check digit.
    Algorithm: Alternating multipliers (1,2,1,2...) starting from position 0.

    Based on: https://gist.github.com/ViCMAP/55260ffd138fe150040d
    """
    digits = cedula.replace('-', '').replace(' ', '')
    if len(digits) != 11 or not digits.isdigit():
        return False

    # First 3 digits cannot be 000
    if digits[:3] == '000':
        return False

    # Calculate check digit using first 10 digits
    total = 0
    for i, char in enumerate(digits[:10]):
        digit = int(char)
        # Alternating multipliers: 1 for even positions, 2 for odd
        multiplier = 1 if i % 2 == 0 else 2
        product = digit * multiplier
        # If product > 9, sum individual digits
        if product > 9:
            product = (product // 10) + (product % 10)
        total += product

    # Check digit calculation
    expected_check = (10 - (total % 10)) % 10

    return int(digits[10]) == expected_check


def validate_rnc_checkdigit(rnc: str) -> bool:
    """
    Validate Dominican RNC (Registro Nacional del Contribuyente) check digit.

    RNC format: 9 digits total (often formatted as X-XX-XXXXX-D).
    Algorithm: Weighted sum with weights [7,9,8,6,5,4,3,2] mod 11.

    Based on: https://gist.github.com/gregorypilar/a2423d860f302ea156de2d0a69eba699
    """
    digits = rnc.replace('-', '').replace(' ', '')
    if len(digits) != 9 or not digits.isdigit():
        return False

    # Weights for RNC validation (for first 8 digits)
    weights = [7, 9, 8, 6, 5, 4, 3, 2]

    total = sum(int(d) * w for d, w in zip(digits[:8], weights))
    remainder = total % 11

    # Check digit calculation based on remainder
    if remainder == 0:
        expected_check = 2
    elif remainder == 1:
        expected_check = 1
    else:
        expected_check = 11 - remainder

    return int(digits[8]) == expected_check


class CedulaField(forms.CharField):
    """
    Dominican cédula (ID) field with Luhn algorithm validation.

    Format: XXX-XXXXXXX-X (11 digits with dashes)
    """

    def __init__(self, *args, validate_checkdigit=True, **kwargs):
        self.validate_checkdigit = validate_checkdigit
        kwargs.setdefault('max_length', 13)
        kwargs.setdefault('widget', TextInput(attrs={
            'placeholder': '001-1234567-8',
            'pattern': r'\d{3}-?\d{7}-?\d',
        }))
        super().__init__(*args, **kwargs)

    def clean(self, value):
        value = super().clean(value)
        if value:
            digits = value.replace('-', '').replace(' ', '')
            if len(digits) != 11 or not digits.isdigit():
                raise forms.ValidationError('Formato de cédula inválido. Debe tener 11 dígitos.')

            # Validate check digit if enabled
            if self.validate_checkdigit and not validate_cedula_checkdigit(value):
                raise forms.ValidationError('Cédula inválida. Verifique el número.')

            # Format with dashes: XXX-XXXXXXX-X
            value = f'{digits[:3]}-{digits[3:10]}-{digits[10]}'
        return value


class RNCField(forms.CharField):
    """
    Dominican RNC (Registro Nacional del Contribuyente) field with validation.

    Format: X-XX-XXXXX-X (9 digits with dashes)
    """

    def __init__(self, *args, validate_checkdigit=True, **kwargs):
        self.validate_checkdigit = validate_checkdigit
        kwargs.setdefault('max_length', 12)
        kwargs.setdefault('widget', TextInput(attrs={
            'placeholder': '1-31-12345-6',
            'pattern': r'\d-?\d{2}-?\d{5}-?\d',
        }))
        super().__init__(*args, **kwargs)

    def clean(self, value):
        value = super().clean(value)
        if value:
            digits = value.replace('-', '').replace(' ', '')
            if len(digits) != 9 or not digits.isdigit():
                raise forms.ValidationError('Formato de RNC inválido. Debe tener 9 dígitos.')

            # Validate check digit if enabled
            if self.validate_checkdigit and not validate_rnc_checkdigit(value):
                raise forms.ValidationError('RNC inválido. Verifique el número.')

            # Format with dashes: X-XX-XXXXX-X
            value = f'{digits[0]}-{digits[1:3]}-{digits[3:8]}-{digits[8]}'
        return value


class CurrencyField(forms.DecimalField):
    """Currency amount field (RD$)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_digits', 12)
        kwargs.setdefault('decimal_places', 2)
        kwargs.setdefault('min_value', 0)
        kwargs.setdefault('widget', NumberInput(attrs={
            'step': '0.01',
            'min': '0',
        }))
        super().__init__(*args, **kwargs)


class DRDocumentMixin:
    """
    Mixin for forms with id_type/id_number and phone fields.

    Handles:
    - Normalizes id_number format (strips dashes/spaces)
    - Adds validation warnings (not errors) for invalid cedula/RNC
    - Handles RNC-that-are-cedulas (11-digit RNCs)
    - Applies PhoneField widget to phone/whatsapp fields

    Usage:
        class TenantForm(DRDocumentMixin, NitroModelForm):
            ...

    The mixin stores warnings in self.id_warnings (list of strings)
    which templates can display as yellow alerts.
    """

    # Phone fields to auto-enhance with PhoneField widget
    phone_fields = ('phone', 'whatsapp', 'emergency_contact_phone',
                    'employer_phone', 'guarantor_phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id_warnings = []

        # Enhance phone fields with tel type and placeholder
        for fname in self.phone_fields:
            if fname in self.fields:
                field = self.fields[fname]
                field.widget = TextInput(attrs={
                    'type': 'tel',
                    'placeholder': '(809) 555-1234',
                })

        # Add placeholder to id_number based on id_type
        if 'id_number' in self.fields:
            self.fields['id_number'].widget.attrs.setdefault(
                'placeholder', '001-0000000-0'
            )

    def clean_id_number(self):
        """Normalize and validate id_number based on id_type."""
        value = self.cleaned_data.get('id_number', '')
        if not value:
            return value

        id_type = self.data.get('id_type', self.initial.get('id_type', 'cedula'))
        digits = value.replace('-', '').replace(' ', '')

        if id_type == 'cedula' or (id_type == 'rnc' and len(digits) == 11):
            # Cedula or RNC-that-is-a-cedula (11 digits)
            if len(digits) == 11 and digits.isdigit():
                if not validate_cedula_checkdigit(digits):
                    self.id_warnings.append(
                        'El dígito verificador de la cédula no es válido. Verifique el número.'
                    )
                # Format: XXX-XXXXXXX-X
                value = f'{digits[:3]}-{digits[3:10]}-{digits[10]}'
            elif digits.isdigit():
                self.id_warnings.append(
                    f'La cédula debe tener 11 dígitos (tiene {len(digits)}).'
                )

        elif id_type == 'rnc':
            if len(digits) == 9 and digits.isdigit():
                if not validate_rnc_checkdigit(digits):
                    self.id_warnings.append(
                        'El dígito verificador del RNC no es válido. Verifique el número.'
                    )
                # Format: X-XX-XXXXX-X
                value = f'{digits[0]}-{digits[1:3]}-{digits[3:8]}-{digits[8]}'
            elif digits.isdigit():
                self.id_warnings.append(
                    f'El RNC debe tener 9 dígitos (tiene {len(digits)}).'
                )

        # passport and other: no validation, just return as-is
        return value

    def _clean_phone_value(self, value):
        """Normalize a phone number value."""
        if not value:
            return value
        digits = ''.join(c for c in value if c.isdigit())
        if digits.startswith('1') and len(digits) == 11:
            digits = digits[1:]
        elif digits.startswith('001') and len(digits) == 13:
            digits = digits[3:]
        if len(digits) == 10:
            return digits
        return value

    def clean_phone(self):
        return self._clean_phone_value(self.cleaned_data.get('phone', ''))

    def clean_whatsapp(self):
        return self._clean_phone_value(self.cleaned_data.get('whatsapp', ''))

    def clean_emergency_contact_phone(self):
        return self._clean_phone_value(self.cleaned_data.get('emergency_contact_phone', ''))

    def clean_employer_phone(self):
        return self._clean_phone_value(self.cleaned_data.get('employer_phone', ''))

    def clean_guarantor_phone(self):
        return self._clean_phone_value(self.cleaned_data.get('guarantor_phone', ''))

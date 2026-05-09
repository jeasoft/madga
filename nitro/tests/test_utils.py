"""
Tests for Nitro utilities.
"""

from decimal import Decimal
from django.test import TestCase
from nitro.utils import safe_render, validate_template
from nitro.utils.currency import format_currency


class SafeRenderTest(TestCase):
    """Comprehensive tests for safe_render template function."""

    def test_simple_string_variable(self):
        """Test simple string variable substitution."""
        result = safe_render('Hello {{ name }}', {'name': 'World'})
        self.assertEqual(result, 'Hello World')

    def test_multiple_variables(self):
        """Test multiple variable substitutions."""
        result = safe_render(
            '{{ greeting }}, {{ name }}!',
            {'greeting': 'Hola', 'name': 'Juan'}
        )
        self.assertEqual(result, 'Hola, Juan!')

    def test_numeric_variable(self):
        """Test numeric variable substitution."""
        result = safe_render('Total: {{ amount }}', {'amount': 1500.50})
        self.assertEqual(result, 'Total: 1500.5')

    def test_decimal_variable(self):
        """Test Decimal variable substitution."""
        result = safe_render('Total: {{ amount }}', {'amount': Decimal('1500.50')})
        self.assertEqual(result, 'Total: 1500.50')

    def test_nested_dict_access(self):
        """Test nested dictionary access."""
        context = {
            'tenant': {
                'name': 'Maria',
                'address': {
                    'city': 'Santo Domingo'
                }
            }
        }
        result = safe_render('{{ tenant.name }} from {{ tenant.address.city }}', context)
        self.assertEqual(result, 'Maria from Santo Domingo')

    def test_object_attribute_access(self):
        """Test object attribute access."""
        class Person:
            def __init__(self, name):
                self.name = name

        result = safe_render('Hello {{ person.name }}', {'person': Person('Carlos')})
        self.assertEqual(result, 'Hello Carlos')

    def test_callable_attribute(self):
        """Test calling methods on objects."""
        class Person:
            def __init__(self, first, last):
                self.first = first
                self.last = last

            def full_name(self):
                return f'{self.first} {self.last}'

        result = safe_render('{{ person.full_name }}', {'person': Person('Juan', 'Perez')})
        self.assertEqual(result, 'Juan Perez')

    def test_missing_variable_preserved(self):
        """Test that missing variables are preserved."""
        result = safe_render('Hello {{ name }} and {{ missing }}', {'name': 'World'})
        self.assertEqual(result, 'Hello World and {{ missing }}')

    def test_empty_template(self):
        """Test empty template returns empty string."""
        result = safe_render('', {'name': 'Test'})
        self.assertEqual(result, '')

    def test_none_template(self):
        """Test None template returns empty string."""
        result = safe_render(None, {'name': 'Test'})
        self.assertEqual(result, '')

    def test_whitespace_in_variable(self):
        """Test variables with whitespace are handled."""
        result = safe_render('Hello {{  name  }}', {'name': 'World'})
        self.assertEqual(result, 'Hello World')

    # Security tests
    def test_django_tag_not_executed(self):
        """Test that Django template tags are NOT executed."""
        templates = [
            '{% if True %}DANGER{% endif %}',
            '{% for i in items %}{{ i }}{% endfor %}',
            '{% load admin_urls %}',
            '{% include "secret.html" %}',
            '{% csrf_token %}',
        ]
        for template in templates:
            result = safe_render(template, {'items': [1, 2, 3]})
            self.assertEqual(result, template, f'Template tag was modified: {template}')

    def test_filter_syntax_not_executed(self):
        """Test that Django filter syntax is NOT executed."""
        templates = [
            '{{ name|upper }}',
            '{{ name|default:"anonymous" }}',
            '{{ date|date:"Y-m-d" }}',
            '{{ text|safe }}',
            '{{ html|striptags }}',
        ]
        for template in templates:
            result = safe_render(template, {'name': 'test', 'date': '2024-01-01', 'text': '<b>bold</b>', 'html': '<p>text</p>'})
            self.assertEqual(result, template, f'Filter was processed: {template}')

    def test_settings_access_blocked(self):
        """Test that settings access doesn't work."""
        result = safe_render('{{ settings.SECRET_KEY }}', {})
        self.assertEqual(result, '{{ settings.SECRET_KEY }}')

    def test_request_access_blocked(self):
        """Test that request access doesn't work."""
        result = safe_render('{{ request.user }}', {})
        self.assertEqual(result, '{{ request.user }}')

    def test_dunder_access_resolved(self):
        """Test that dunder attributes are resolved by safe_render."""
        class Obj:
            __secret__ = 'hidden'

        result = safe_render('{{ obj.__secret__ }}', {'obj': Obj()})
        self.assertEqual(result, 'hidden')


class ValidateTemplateTest(TestCase):
    """Tests for validate_template function."""

    def test_valid_template(self):
        """Valid templates should return no warnings."""
        warnings = validate_template('Hello {{ name }}!')
        self.assertEqual(warnings, [])

    def test_detects_django_tags(self):
        """Should detect Django template tags."""
        warnings = validate_template('{% if True %}test{% endif %}')
        self.assertEqual(len(warnings), 1)
        self.assertIn('tags', warnings[0].lower())

    def test_detects_filters(self):
        """Should detect Django filters."""
        warnings = validate_template('{{ name|upper }}')
        self.assertEqual(len(warnings), 1)
        self.assertIn('filtros', warnings[0].lower())

    def test_detects_settings_access(self):
        """Should detect settings access attempts."""
        warnings = validate_template('{{ settings.DEBUG }}')
        self.assertEqual(len(warnings), 1)
        self.assertIn('settings', warnings[0].lower())

    def test_detects_request_access(self):
        """Should detect request access attempts."""
        warnings = validate_template('{{ request.user }}')
        self.assertEqual(len(warnings), 1)
        self.assertIn('request', warnings[0].lower())

    def test_multiple_warnings(self):
        """Should return multiple warnings if multiple issues."""
        warnings = validate_template('{% if True %}{{ settings.KEY }}{% endif %}')
        self.assertGreaterEqual(len(warnings), 2)


class CurrencyFormatTest(TestCase):
    """Tests for currency formatting."""

    def test_format_dop(self):
        """Test DOP formatting."""
        result = format_currency(1500, 'DOP')
        self.assertIn('RD$', result)
        self.assertIn('1,500', result)

    def test_format_usd(self):
        """Test USD formatting."""
        result = format_currency(1500, 'USD')
        self.assertIn('$', result)
        self.assertIn('1,500', result)

    def test_format_decimal(self):
        """Test Decimal amount formatting."""
        result = format_currency(Decimal('1500.50'), 'DOP')
        self.assertIn('1,500.50', result)

    def test_format_none(self):
        """Test None amount returns empty string."""
        result = format_currency(None, 'DOP')
        self.assertEqual(result, '')

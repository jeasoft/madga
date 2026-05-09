# Nitro 0.8 - Utilities

## 17. WhatsApp Utilities

### `nitro/utils/whatsapp.py`

```python
"""
Nitro 0.8 - WhatsApp message utilities.

Usage:
    from nitro.utils.whatsapp import whatsapp_link, WhatsAppMessage
    
    # Simple link
    link = whatsapp_link('8095551234', 'Hello!')
    
    # Pre-built templates
    link = WhatsAppMessage.payment_reminder(tenant, lease, 5000, 'Mi Empresa')
"""

from urllib.parse import quote
from decimal import Decimal


def clean_phone(phone: str, default_country: str = '1') -> str:
    """
    Clean phone number: remove non-digits, add country code if needed.
    
    Args:
        phone: Raw phone number
        default_country: Country code to add if missing (default '1' for DR/US)
    
    Returns:
        Clean phone number with country code, or empty string if invalid
    """
    if not phone:
        return ''
    
    # Remove non-digits
    digits = ''.join(c for c in str(phone) if c.isdigit())
    
    if not digits:
        return ''
    
    # Add country code if needed
    if len(digits) == 10:
        digits = default_country + digits
    elif len(digits) == 11 and digits[0] == '1':
        pass  # Already has US/Canada code
    elif len(digits) < 10:
        return ''  # Too short
    
    return digits


def whatsapp_link(phone: str, message: str = '') -> str:
    """
    Generate WhatsApp wa.me link.
    
    Args:
        phone: Phone number (will be cleaned)
        message: Optional pre-filled message
    
    Returns:
        WhatsApp link or empty string if phone invalid
    """
    clean = clean_phone(phone)
    if not clean:
        return ''
    
    url = f'https://wa.me/{clean}'
    if message:
        url += f'?text={quote(message)}'
    
    return url


def format_currency(amount, currency: str = 'DOP') -> str:
    """Format amount with currency symbol."""
    symbols = {'DOP': 'RD$', 'USD': 'US$', 'EUR': '€'}
    symbol = symbols.get(currency, currency)
    
    if isinstance(amount, (int, float, Decimal)):
        return f'{symbol} {amount:,.2f}'
    return f'{symbol} {amount}'


class WhatsAppMessage:
    """
    Pre-built WhatsApp message templates.
    
    All methods return a WhatsApp link with pre-filled message.
    Returns empty string if phone is invalid.
    """
    
    # -------------------------------------------------------------------------
    # Tenant Messages
    # -------------------------------------------------------------------------
    
    @staticmethod
    def payment_reminder(tenant, lease, amount_due, company_name: str = '', 
                        bank_info: str = '') -> str:
        """
        Payment reminder message.
        
        Args:
            tenant: Tenant object with phone/name attributes
            lease: Lease object with property attribute
            amount_due: Amount to pay
            company_name: Company name for signature
            bank_info: Optional bank account info
        """
        phone = getattr(tenant, 'whatsapp', None) or getattr(tenant, 'phone', '')
        currency = getattr(lease, 'currency', 'DOP')
        property_name = lease.property.name if hasattr(lease, 'property') else 'la propiedad'
        
        message = f"""Hola {tenant.name},

Le recordamos que tiene un pago pendiente de {format_currency(amount_due, currency)} correspondiente a {property_name}.

"""
        if bank_info:
            message += f"""Datos para transferencia:
{bank_info}

"""
        message += """Favor confirmar una vez realizado el pago.

Gracias."""
        
        if company_name:
            message += f"\n\n- {company_name}"
        
        return whatsapp_link(phone, message)
    
    @staticmethod
    def payment_overdue(tenant, lease, days_overdue: int, company_name: str = '') -> str:
        """Payment overdue warning."""
        phone = getattr(tenant, 'whatsapp', None) or getattr(tenant, 'phone', '')
        currency = getattr(lease, 'currency', 'DOP')
        amount = getattr(lease, 'rent_amount', 0)
        property_name = lease.property.name if hasattr(lease, 'property') else 'la propiedad'
        
        message = f"""Hola {tenant.name},

Su pago de {format_currency(amount, currency)} para {property_name} tiene {days_overdue} días de atraso.

Por favor comuníquese con nosotros para regularizar su situación.

Gracias."""
        
        if company_name:
            message += f"\n\n- {company_name}"
        
        return whatsapp_link(phone, message)
    
    @staticmethod
    def payment_received(tenant, payment, company_name: str = '') -> str:
        """Payment confirmation."""
        phone = getattr(tenant, 'whatsapp', None) or getattr(tenant, 'phone', '')
        amount = getattr(payment, 'amount', 0)
        currency = getattr(payment, 'currency', 'DOP')
        
        message = f"""Hola {tenant.name},

Confirmamos la recepción de su pago por {format_currency(amount, currency)}.

¡Gracias por su puntualidad!"""
        
        if company_name:
            message += f"\n\n- {company_name}"
        
        return whatsapp_link(phone, message)
    
    @staticmethod
    def lease_expiring(tenant, lease, days_remaining: int, company_name: str = '') -> str:
        """Lease expiration notice."""
        phone = getattr(tenant, 'whatsapp', None) or getattr(tenant, 'phone', '')
        property_name = lease.property.name if hasattr(lease, 'property') else 'la propiedad'
        
        message = f"""Hola {tenant.name},

Le informamos que su contrato de arrendamiento para {property_name} vence en {days_remaining} días.

¿Le gustaría renovar? Por favor contáctenos para discutir los términos.

Gracias."""
        
        if company_name:
            message += f"\n\n- {company_name}"
        
        return whatsapp_link(phone, message)
    
    @staticmethod
    def ticket_update(tenant, ticket, status_message: str, company_name: str = '') -> str:
        """Ticket status update."""
        phone = getattr(tenant, 'whatsapp', None) or getattr(tenant, 'phone', '')
        ticket_title = getattr(ticket, 'title', 'su solicitud')
        
        message = f"""Hola {tenant.name},

Actualización sobre {ticket_title}:

{status_message}

Gracias."""
        
        if company_name:
            message += f"\n\n- {company_name}"
        
        return whatsapp_link(phone, message)
    
    # -------------------------------------------------------------------------
    # Landlord Messages  
    # -------------------------------------------------------------------------
    
    @staticmethod
    def landlord_monthly_report(landlord, month: str, year: int, 
                                total_income, total_expenses, net_amount,
                                currency: str = 'DOP', report_url: str = '',
                                company_name: str = '') -> str:
        """Monthly financial report to landlord."""
        phone = getattr(landlord, 'whatsapp', None) or getattr(landlord, 'phone', '')
        
        message = f"""Hola {landlord.name},

Resumen financiero de {month} {year}:

📊 Ingresos: {format_currency(total_income, currency)}
📉 Gastos: {format_currency(total_expenses, currency)}
💰 Neto: {format_currency(net_amount, currency)}

"""
        if report_url:
            message += f"Ver reporte completo: {report_url}\n\n"
        
        message += "Gracias."
        
        if company_name:
            message += f"\n\n- {company_name}"
        
        return whatsapp_link(phone, message)
    
    @staticmethod
    def landlord_payment_collected(landlord, property_name: str, amount,
                                   currency: str, tenant_name: str,
                                   company_name: str = '') -> str:
        """Notify landlord of rent collection."""
        phone = getattr(landlord, 'whatsapp', None) or getattr(landlord, 'phone', '')
        
        message = f"""Hola {landlord.name},

Se ha recibido un pago para {property_name}:

💰 Monto: {format_currency(amount, currency)}
👤 Inquilino: {tenant_name}

Gracias."""
        
        if company_name:
            message += f"\n\n- {company_name}"
        
        return whatsapp_link(phone, message)
    
    @staticmethod
    def landlord_payout_sent(landlord, amount, currency: str, period: str,
                            company_name: str = '') -> str:
        """Notify landlord of payout."""
        phone = getattr(landlord, 'whatsapp', None) or getattr(landlord, 'phone', '')
        
        message = f"""Hola {landlord.name},

Se ha procesado su pago correspondiente a {period}:

💰 Monto: {format_currency(amount, currency)}

El depósito debe reflejarse en su cuenta en 1-2 días hábiles.

Gracias."""
        
        if company_name:
            message += f"\n\n- {company_name}"
        
        return whatsapp_link(phone, message)
    
    # -------------------------------------------------------------------------
    # General Messages
    # -------------------------------------------------------------------------
    
    @staticmethod
    def portal_access(person, portal_url: str, portal_name: str = 'Portal',
                     company_name: str = '') -> str:
        """Send portal access link."""
        phone = getattr(person, 'whatsapp', None) or getattr(person, 'phone', '')
        name = getattr(person, 'name', '')
        
        message = f"""Hola {name},

Aquí está su enlace de acceso al {portal_name}:

{portal_url}

Guarde este enlace para acceder a su cuenta.

Gracias."""
        
        if company_name:
            message += f"\n\n- {company_name}"
        
        return whatsapp_link(phone, message)
    
    @staticmethod
    def custom(phone: str, message: str) -> str:
        """Custom message."""
        return whatsapp_link(phone, message)
```

---

## 18. Currency Utilities

### `nitro/utils/currency.py`

```python
"""
Nitro 0.8 - Currency utilities.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union


# Currency configurations
CURRENCIES = {
    'DOP': {
        'symbol': 'RD$',
        'name': 'Peso Dominicano',
        'decimal_places': 2,
        'thousand_sep': ',',
        'decimal_sep': '.',
    },
    'USD': {
        'symbol': 'US$',
        'name': 'Dólar Estadounidense', 
        'decimal_places': 2,
        'thousand_sep': ',',
        'decimal_sep': '.',
    },
    'EUR': {
        'symbol': '€',
        'name': 'Euro',
        'decimal_places': 2,
        'thousand_sep': '.',
        'decimal_sep': ',',
    },
}


def get_currency_symbol(currency_code: str) -> str:
    """Get currency symbol."""
    return CURRENCIES.get(currency_code, {}).get('symbol', currency_code)


def format_currency(amount: Union[int, float, Decimal, str], 
                   currency_code: str = 'DOP',
                   show_symbol: bool = True) -> str:
    """
    Format amount as currency string.
    
    Args:
        amount: The amount to format
        currency_code: Currency code (DOP, USD, EUR)
        show_symbol: Include currency symbol
    
    Returns:
        Formatted string like "RD$ 1,234.56"
    """
    if amount is None:
        return ''
    
    try:
        if isinstance(amount, str):
            amount = Decimal(amount.replace(',', ''))
        elif isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
    except:
        return str(amount)
    
    config = CURRENCIES.get(currency_code, CURRENCIES['DOP'])
    
    # Round to decimal places
    places = config['decimal_places']
    quantize_str = '0.' + '0' * places
    amount = amount.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
    
    # Format number
    parts = str(amount).split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else '00'
    
    # Add thousand separators
    reversed_int = integer_part[::-1]
    groups = [reversed_int[i:i+3] for i in range(0, len(reversed_int), 3)]
    formatted_int = config['thousand_sep'].join(groups)[::-1]
    
    formatted = f"{formatted_int}{config['decimal_sep']}{decimal_part}"
    
    if show_symbol:
        return f"{config['symbol']} {formatted}"
    return formatted


def parse_currency(value: str, currency_code: str = 'DOP') -> Decimal:
    """
    Parse currency string to Decimal.
    
    Args:
        value: String like "RD$ 1,234.56" or "1234.56"
        currency_code: Currency code for parsing rules
    
    Returns:
        Decimal amount
    """
    if not value:
        return Decimal('0')
    
    config = CURRENCIES.get(currency_code, CURRENCIES['DOP'])
    
    # Remove currency symbol and whitespace
    cleaned = str(value)
    for curr in CURRENCIES.values():
        cleaned = cleaned.replace(curr['symbol'], '')
    cleaned = cleaned.strip()
    
    # Remove thousand separators
    cleaned = cleaned.replace(config['thousand_sep'], '')
    
    # Normalize decimal separator
    if config['decimal_sep'] != '.':
        cleaned = cleaned.replace(config['decimal_sep'], '.')
    
    try:
        return Decimal(cleaned)
    except:
        return Decimal('0')


def convert_currency(amount: Decimal, from_currency: str, to_currency: str,
                    rates: dict = None) -> Decimal:
    """
    Convert between currencies using provided rates.
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code
        to_currency: Target currency code
        rates: Dict of rates like {'USD': 58.5, 'EUR': 63.0} (relative to DOP)
    
    Returns:
        Converted amount
    """
    if from_currency == to_currency:
        return amount
    
    if rates is None:
        # Default approximate rates to DOP
        rates = {
            'DOP': Decimal('1'),
            'USD': Decimal('58.5'),
            'EUR': Decimal('63.0'),
        }
    
    # Convert to DOP first, then to target
    if from_currency != 'DOP':
        amount_dop = amount * rates.get(from_currency, Decimal('1'))
    else:
        amount_dop = amount
    
    if to_currency != 'DOP':
        result = amount_dop / rates.get(to_currency, Decimal('1'))
    else:
        result = amount_dop
    
    return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
```

---

## 19. Date Utilities

### `nitro/utils/dates.py`

```python
"""
Nitro 0.8 - Date utilities.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple
from django.utils import timezone


def today() -> date:
    """Get today's date."""
    return timezone.now().date()


def now() -> datetime:
    """Get current datetime."""
    return timezone.now()


def relative_date(value: date) -> str:
    """
    Return relative date string.
    
    Examples: "Hoy", "Ayer", "Hace 3 días", "En 5 días"
    """
    if not value:
        return ''
    
    if isinstance(value, datetime):
        value = value.date()
    
    today_date = today()
    diff = (value - today_date).days
    
    if diff == 0:
        return 'Hoy'
    if diff == 1:
        return 'Mañana'
    if diff == -1:
        return 'Ayer'
    if 1 < diff <= 7:
        return f'En {diff} días'
    if -7 <= diff < -1:
        return f'Hace {abs(diff)} días'
    if 7 < diff <= 30:
        weeks = diff // 7
        return f'En {weeks} semana{"s" if weeks > 1 else ""}'
    if -30 <= diff < -7:
        weeks = abs(diff) // 7
        return f'Hace {weeks} semana{"s" if weeks > 1 else ""}'
    
    return value.strftime('%d/%m/%Y')


def date_range(start: date, end: date) -> str:
    """Format date range as string."""
    if start.year == end.year:
        if start.month == end.month:
            return f'{start.day}-{end.day} {start.strftime("%b %Y")}'
        return f'{start.strftime("%d %b")} - {end.strftime("%d %b %Y")}'
    return f'{start.strftime("%d %b %Y")} - {end.strftime("%d %b %Y")}'


def month_name(month: int) -> str:
    """Get Spanish month name."""
    months = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    return months[month] if 1 <= month <= 12 else ''


def month_year(d: date) -> str:
    """Format as 'Enero 2025'."""
    return f'{month_name(d.month)} {d.year}'


def get_month_range(year: int, month: int) -> Tuple[date, date]:
    """Get first and last day of month."""
    first_day = date(year, month, 1)
    
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    return first_day, last_day


def get_quarter_range(year: int, quarter: int) -> Tuple[date, date]:
    """Get first and last day of quarter."""
    quarters = {
        1: (1, 3),
        2: (4, 6),
        3: (7, 9),
        4: (10, 12),
    }
    start_month, end_month = quarters.get(quarter, (1, 3))
    first_day = date(year, start_month, 1)
    _, last_day = get_month_range(year, end_month)
    return first_day, last_day


def get_year_range(year: int) -> Tuple[date, date]:
    """Get first and last day of year."""
    return date(year, 1, 1), date(year, 12, 31)


def days_until(target_date: date) -> int:
    """Days until target date (negative if past)."""
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    return (target_date - today()).days


def days_since(past_date: date) -> int:
    """Days since past date (negative if future)."""
    if isinstance(past_date, datetime):
        past_date = past_date.date()
    return (today() - past_date).days


def is_overdue(due_date: date) -> bool:
    """Check if date is past."""
    if isinstance(due_date, datetime):
        due_date = due_date.date()
    return due_date < today()


def add_months(d: date, months: int) -> date:
    """Add months to date."""
    month = d.month + months
    year = d.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    day = min(d.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 
                      31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)
```

---

## 20. Utils `__init__.py`

### `nitro/utils/__init__.py`

```python
"""
Nitro 0.8 - Utilities.
"""

from .whatsapp import whatsapp_link, clean_phone, WhatsAppMessage
from .currency import (
    format_currency, parse_currency, convert_currency,
    get_currency_symbol, CURRENCIES
)
from .dates import (
    today, now, relative_date, date_range, month_name, month_year,
    get_month_range, get_quarter_range, get_year_range,
    days_until, days_since, is_overdue, add_months
)

__all__ = [
    # WhatsApp
    'whatsapp_link', 'clean_phone', 'WhatsAppMessage',
    # Currency
    'format_currency', 'parse_currency', 'convert_currency',
    'get_currency_symbol', 'CURRENCIES',
    # Dates
    'today', 'now', 'relative_date', 'date_range', 'month_name', 'month_year',
    'get_month_range', 'get_quarter_range', 'get_year_range',
    'days_until', 'days_since', 'is_overdue', 'add_months',
]
```

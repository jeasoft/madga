# Nitro 0.8 - Componentes HTML

## 13. Template Components

### `templates/nitro/components/card.html`

```django
{# Basic card container #}
<div class="bg-white rounded-xl border shadow-sm {{ class|default:'' }}">
    {% if title %}
    <div class="px-4 py-3 border-b flex items-center justify-between">
        <h3 class="font-semibold text-gray-900">{{ title }}</h3>
        {% if action_url %}
        <a href="{{ action_url }}" class="text-sm text-primary-600 hover:underline">{{ action_text|default:'Ver todo' }}</a>
        {% endif %}
    </div>
    {% endif %}
    <div class="p-4">
        {{ content }}
    </div>
</div>
```

---

### `templates/nitro/components/stats_card.html`

```django
{# Statistics card with icon, value, and change indicator #}
{% if href %}<a href="{{ href }}" class="block">{% endif %}
<div class="bg-white rounded-xl border p-4 hover:shadow-md transition-shadow">
    <div class="flex items-start justify-between">
        <div>
            <p class="text-sm text-gray-500 mb-1">{{ label }}</p>
            <p class="text-2xl font-bold text-gray-900">{{ value }}</p>
            {% if change %}
            <p class="text-xs mt-1 {% if change_type == 'positive' %}text-green-600{% elif change_type == 'negative' %}text-red-600{% else %}text-gray-500{% endif %}">
                {% if change_type == 'positive' %}↑{% elif change_type == 'negative' %}↓{% endif %}
                {{ change }}
            </p>
            {% endif %}
        </div>
        <span class="text-3xl">{{ icon }}</span>
    </div>
</div>
{% if href %}</a>{% endif %}
```

---

### `templates/nitro/components/empty_state.html`

```django
{# Empty state when no data #}
<div class="text-center py-12">
    <span class="text-5xl mb-4 block">{{ icon }}</span>
    <h3 class="text-lg font-medium text-gray-900 mb-1">{{ title }}</h3>
    {% if message %}
    <p class="text-gray-500 mb-4">{{ message }}</p>
    {% endif %}
    {% if action_url %}
    <a href="{{ action_url }}" class="btn btn-primary">{{ action_text }}</a>
    {% endif %}
</div>
```

---

### `templates/nitro/components/confirm_modal.html`

```django
{# Confirmation modal - used with Alpine #}
<div x-data="{ 
    show: false, 
    title: '', 
    message: '', 
    action: '', 
    method: 'delete',
    open(t, m, a, meth = 'delete') { 
        this.title = t; 
        this.message = m; 
        this.action = a;
        this.method = meth;
        this.show = true; 
    },
    close() { this.show = false; }
}"
     @confirm-modal.window="open($event.detail.title, $event.detail.message, $event.detail.action, $event.detail.method || 'delete')"
     x-show="show" x-cloak
     class="fixed inset-0 z-50 overflow-y-auto">
    
    {# Backdrop #}
    <div class="fixed inset-0 bg-black/50" @click="close()"></div>
    
    {# Modal #}
    <div class="relative min-h-screen flex items-center justify-center p-4">
        <div class="relative bg-white rounded-xl shadow-xl max-w-md w-full p-6"
             x-transition>
            
            <div class="text-center">
                <span class="text-5xl mb-4 block">⚠️</span>
                <h3 class="text-lg font-bold text-gray-900 mb-2" x-text="title">¿Confirmar acción?</h3>
                <p class="text-gray-500 mb-6" x-text="message">Esta acción no se puede deshacer.</p>
            </div>
            
            <div class="flex gap-3">
                <button @click="close()" class="btn btn-secondary flex-1">
                    Cancelar
                </button>
                <button @click="$dispatch('confirm-action', { action: action, method: method }); close()"
                        :class="method === 'delete' ? 'btn-danger' : 'btn-primary'"
                        class="btn flex-1">
                    Confirmar
                </button>
            </div>
        </div>
    </div>
</div>

{# Helper: open modal via Alpine event #}
{# Usage: <button @click="$dispatch('confirm-modal', {title: '¿Eliminar?', message: 'Se eliminará', action: '/delete/1/'})">Delete</button> #}
```

---

### `templates/nitro/components/modal.html`

```django
{# General purpose modal #}
{# Usage: 
    <div x-data="{ showModal: false }">
        <button @click="showModal = true">Open</button>
        {% include 'nitro/components/modal.html' with id='my-modal' title='My Modal' %}
    </div>
#}
<template x-teleport="body">
    <div x-show="show{{ id|default:'Modal' }}" x-cloak class="fixed inset-0 z-50">
        <div class="fixed inset-0 bg-black/50" @click="show{{ id|default:'Modal' }} = false"></div>
        <div class="fixed inset-0 flex items-center justify-center p-4">
            <div class="bg-white rounded-xl shadow-xl max-w-{{ size|default:'lg' }} w-full max-h-[90vh] overflow-hidden"
                 x-transition>
                
                {# Header #}
                <div class="flex items-center justify-between px-6 py-4 border-b">
                    <h3 class="text-lg font-bold text-gray-900">{{ title }}</h3>
                    <button @click="show{{ id|default:'Modal' }} = false" 
                            class="text-gray-400 hover:text-gray-600">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
                
                {# Body #}
                <div class="px-6 py-4 overflow-y-auto max-h-[calc(90vh-130px)]">
                    {{ slot }}
                </div>
                
                {# Footer #}
                {% if show_footer %}
                <div class="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
                    <button @click="show{{ id|default:'Modal' }} = false" class="btn btn-secondary">
                        Cancelar
                    </button>
                    <button type="submit" class="btn btn-primary">
                        {{ submit_text|default:'Guardar' }}
                    </button>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</template>
```

---

### `templates/nitro/components/dropdown.html`

```django
{# Action dropdown menu #}
<div x-data="{ open: false }" class="relative">
    <button @click="open = !open" 
            class="p-2 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"/>
        </svg>
    </button>
    
    <div x-show="open" @click.away="open = false" x-cloak
         x-transition
         class="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-lg border z-50">
        {% for item in items %}
        {% if item.divider %}
        <div class="border-t my-1"></div>
        {% else %}
        <a href="{{ item.url|default:'#' }}"
           {% if item.hx_method %}
           hx-{{ item.hx_method }}="{{ item.url }}"
           hx-target="{{ item.target|default:'body' }}"
           {% if item.confirm %}hx-confirm="{{ item.confirm }}"{% endif %}
           {% endif %}
           class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 first:rounded-t-xl last:rounded-b-xl
                  {% if item.danger %}text-red-600 hover:bg-red-50{% endif %}">
            {% if item.icon %}<span class="mr-2">{{ item.icon }}</span>{% endif %}
            {{ item.label }}
        </a>
        {% endif %}
        {% endfor %}
    </div>
</div>
```

---

### `templates/nitro/components/pagination.html`

```django
{# HTMX pagination #}
{% if page_obj.has_other_pages %}
<nav class="flex items-center justify-between py-4" aria-label="Pagination">
    <div class="text-sm text-gray-500">
        Mostrando {{ page_obj.start_index }}-{{ page_obj.end_index }} de {{ page_obj.paginator.count }}
    </div>
    
    <div class="flex items-center gap-2">
        {# Previous #}
        {% if page_obj.has_previous %}
        <button hx-get="{{ request_path }}?page={{ page_obj.previous_page_number }}{% if query_string %}&{{ query_string }}{% endif %}"
                hx-target="{{ target }}" hx-replace-url="true"
                class="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">
            ← Anterior
        </button>
        {% endif %}
        
        {# Page numbers #}
        <div class="hidden sm:flex items-center gap-1">
            {% for num in page_obj.paginator.page_range %}
                {% if page_obj.number == num %}
                <span class="px-3 py-2 text-sm bg-primary-600 text-white rounded-lg">{{ num }}</span>
                {% elif num > page_obj.number|add:'-3' and num < page_obj.number|add:'3' %}
                <button hx-get="{{ request_path }}?page={{ num }}{% if query_string %}&{{ query_string }}{% endif %}"
                        hx-target="{{ target }}" hx-replace-url="true"
                        class="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">
                    {{ num }}
                </button>
                {% elif num == 1 or num == page_obj.paginator.num_pages %}
                <button hx-get="{{ request_path }}?page={{ num }}{% if query_string %}&{{ query_string }}{% endif %}"
                        hx-target="{{ target }}" hx-replace-url="true"
                        class="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">
                    {{ num }}
                </button>
                {% elif num == 2 or num == page_obj.paginator.num_pages|add:'-1' %}
                <span class="px-2">...</span>
                {% endif %}
            {% endfor %}
        </div>
        
        {# Next #}
        {% if page_obj.has_next %}
        <button hx-get="{{ request_path }}?page={{ page_obj.next_page_number }}{% if query_string %}&{{ query_string }}{% endif %}"
                hx-target="{{ target }}" hx-replace-url="true"
                class="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">
            Siguiente →
        </button>
        {% endif %}
    </div>
</nav>
{% endif %}
```

---

### `templates/nitro/components/search_bar.html`

```django
{# HTMX search input #}
<div class="relative">
    <input type="search" 
           name="{{ name }}" 
           value="{{ current_value }}"
           placeholder="{{ placeholder }}"
           hx-get="{{ request_path }}"
           hx-target="{{ target }}"
           hx-trigger="input changed delay:300ms, search"
           hx-replace-url="true"
           class="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
    <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
    </svg>
</div>
```

---

### `templates/nitro/components/filter_select.html`

```django
{# HTMX filter dropdown #}
<div>
    {% if label %}<label class="block text-sm font-medium text-gray-700 mb-1">{{ label }}</label>{% endif %}
    <select name="{{ field }}"
            hx-get="{{ request_path }}"
            hx-target="{{ target }}"
            hx-trigger="change"
            hx-replace-url="true"
            class="w-full px-3 py-2 border rounded-lg text-sm bg-white focus:ring-2 focus:ring-primary-500">
        <option value="">{{ all_label }}</option>
        {% for value, display in options %}
        <option value="{{ value }}" {% if value == current_value %}selected{% endif %}>{{ display }}</option>
        {% endfor %}
    </select>
</div>
```

---

### `templates/nitro/components/form_field.html`

```django
{# Styled form field #}
<div class="mb-4 {{ css_class }}">
    {% if field_type != 'checkbox' %}
    <label for="{{ field.id_for_label }}" class="block text-sm font-medium text-gray-700 mb-1">
        {{ label }}
        {% if is_required %}<span class="text-red-500">*</span>{% endif %}
    </label>
    {% endif %}
    
    {% if field_type == 'checkbox' %}
    <label class="flex items-center gap-2">
        {{ field }}
        <span class="text-sm text-gray-700">{{ label }}</span>
    </label>
    {% else %}
    {{ field }}
    {% endif %}
    
    {% if help_text %}
    <p class="mt-1 text-xs text-gray-500">{{ help_text }}</p>
    {% endif %}
    
    {% if errors %}
    {% for error in errors %}
    <p class="mt-1 text-xs text-red-600">{{ error }}</p>
    {% endfor %}
    {% endif %}
</div>
```

---

### `templates/nitro/components/avatar.html`

```django
{# User avatar with initials fallback #}
{% if image_url %}
<img src="{{ image_url }}" alt="{{ name }}" 
     class="{{ size_class }} rounded-full object-cover">
{% else %}
<div class="{{ size_class }} rounded-full bg-primary-100 text-primary-700 font-medium flex items-center justify-center">
    {{ initials }}
</div>
{% endif %}
```

---

### `templates/nitro/components/badge.html`

```django
{# Generic badge #}
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium 
             {% if color == 'green' %}bg-green-100 text-green-800
             {% elif color == 'red' %}bg-red-100 text-red-800
             {% elif color == 'yellow' %}bg-yellow-100 text-yellow-800
             {% elif color == 'blue' %}bg-blue-100 text-blue-800
             {% elif color == 'purple' %}bg-purple-100 text-purple-800
             {% else %}bg-gray-100 text-gray-800{% endif %}">
    {{ text }}
</span>
```

---

### `templates/nitro/components/toast.html`

```django
{# Toast notification container #}
<div id="toast-container" 
     class="fixed bottom-4 right-4 z-50 space-y-2"
     x-data="toastManager()"
     @show-toast.window="add($event.detail)">
    
    <template x-for="toast in toasts" :key="toast.id">
        <div x-show="toast.visible"
             x-transition:enter="transition ease-out duration-300"
             x-transition:enter-start="opacity-0 translate-y-2"
             x-transition:enter-end="opacity-100 translate-y-0"
             x-transition:leave="transition ease-in duration-200"
             x-transition:leave-start="opacity-100"
             x-transition:leave-end="opacity-0"
             :class="{
                 'bg-green-50 border-green-200 text-green-800': toast.type === 'success',
                 'bg-red-50 border-red-200 text-red-800': toast.type === 'error',
                 'bg-yellow-50 border-yellow-200 text-yellow-800': toast.type === 'warning',
                 'bg-blue-50 border-blue-200 text-blue-800': toast.type === 'info'
             }"
             class="flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg max-w-sm">
            
            <span x-text="toast.type === 'success' ? '✓' : toast.type === 'error' ? '✗' : toast.type === 'warning' ? '⚠' : 'ℹ'"></span>
            <span x-text="toast.message" class="flex-1"></span>
            <button @click="remove(toast.id)" class="text-gray-400 hover:text-gray-600">×</button>
        </div>
    </template>
</div>
```

---

### `templates/nitro/components/loading.html`

```django
{# Loading spinner #}
<div class="flex items-center justify-center py-8">
    <svg class="animate-spin h-8 w-8 text-primary-600" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
    {% if message %}<span class="ml-3 text-gray-500">{{ message }}</span>{% endif %}
</div>
```

---

### `templates/nitro/components/file_upload.html`

```django
{# Drag & drop file upload with Alpine #}
<div x-data="fileUpload()" 
     @dragover.prevent="dragging = true"
     @dragleave.prevent="dragging = false"
     @drop.prevent="handleDrop($event)"
     :class="{ 'border-primary-500 bg-primary-50': dragging }"
     class="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center transition-colors">
    
    <input type="file" 
           name="{{ name|default:'file' }}" 
           id="{{ id|default:'file-upload' }}"
           @change="handleSelect($event)"
           {% if multiple %}multiple{% endif %}
           {% if accept %}accept="{{ accept }}"{% endif %}
           class="hidden">
    
    <template x-if="!file">
        <div>
            <span class="text-4xl mb-4 block">📁</span>
            <p class="text-gray-600 mb-2">
                Arrastra un archivo aquí o 
                <label for="{{ id|default:'file-upload' }}" class="text-primary-600 hover:underline cursor-pointer">
                    selecciona uno
                </label>
            </p>
            {% if help_text %}
            <p class="text-xs text-gray-500">{{ help_text }}</p>
            {% endif %}
        </div>
    </template>
    
    <template x-if="file">
        <div class="flex items-center justify-center gap-4">
            <span class="text-2xl">📄</span>
            <div class="text-left">
                <p class="font-medium text-gray-900" x-text="file.name"></p>
                <p class="text-sm text-gray-500" x-text="formatSize(file.size)"></p>
            </div>
            <button type="button" @click="removeFile()" class="text-red-500 hover:text-red-700">
                ✕
            </button>
        </div>
    </template>
</div>
```

---

### `templates/nitro/components/timeline.html`

```django
{# Activity timeline #}
<div class="flow-root">
    <ul class="-mb-8">
        {% for item in items %}
        <li>
            <div class="relative pb-8">
                {% if not forloop.last %}
                <span class="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200"></span>
                {% endif %}
                
                <div class="relative flex space-x-3">
                    <div>
                        <span class="h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white
                                     {% if item.type == 'success' %}bg-green-500
                                     {% elif item.type == 'error' %}bg-red-500
                                     {% elif item.type == 'warning' %}bg-yellow-500
                                     {% else %}bg-gray-400{% endif %}">
                            <span class="text-white text-sm">{{ item.icon|default:'•' }}</span>
                        </span>
                    </div>
                    <div class="flex-1 min-w-0 pt-1.5">
                        <p class="text-sm text-gray-500">
                            {{ item.text }}
                            <span class="font-medium text-gray-900">{{ item.actor }}</span>
                        </p>
                        <p class="text-xs text-gray-400 mt-0.5">{{ item.timestamp|timesince }} ago</p>
                    </div>
                </div>
            </div>
        </li>
        {% endfor %}
    </ul>
</div>
```

---

### `templates/nitro/components/table.html`

```django
{# NitroTable rendering #}
<div class="overflow-x-auto">
    {% if table.has_bulk_actions %}
    <form method="post" action="{% url 'bulk_action' %}">
        {% csrf_token %}
    {% endif %}
    
    <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
            <tr>
                {% if table.has_bulk_actions %}
                <th class="px-4 py-3 w-10">
                    <input type="checkbox" x-data @click="document.querySelectorAll('[name=selected]').forEach(c => c.checked = $el.checked)"
                           class="h-4 w-4 rounded border-gray-300">
                </th>
                {% endif %}
                
                {% for column in table.columns %}
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider {{ column.css_class }}">
                    {% if column.sortable %}
                    {% nitro_sort column.field column.label target=target %}
                    {% else %}
                    {{ column.label }}
                    {% endif %}
                </th>
                {% endfor %}
                
                {% if table.row_actions %}
                <th class="px-4 py-3 w-20"></th>
                {% endif %}
            </tr>
        </thead>
        
        <tbody class="bg-white divide-y divide-gray-200">
            {% for obj, cells, actions in table.get_rows %}
            <tr class="hover:bg-gray-50">
                {% if table.has_bulk_actions %}
                <td class="px-4 py-3">
                    <input type="checkbox" name="selected" value="{{ obj.pk }}"
                           class="h-4 w-4 rounded border-gray-300">
                </td>
                {% endif %}
                
                {% for cell in cells %}
                <td class="px-4 py-3 text-sm text-gray-900">{{ cell|safe }}</td>
                {% endfor %}
                
                {% if actions %}
                <td class="px-4 py-3 text-right">
                    <div class="flex items-center justify-end gap-2">
                        {% for action in actions %}
                        {{ action|safe }}
                        {% endfor %}
                    </div>
                </td>
                {% endif %}
            </tr>
            {% empty %}
            <tr>
                <td colspan="100" class="px-4 py-12 text-center text-gray-500">
                    No hay datos
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    {% if table.has_bulk_actions %}
    <div class="bg-gray-50 px-4 py-3 border-t flex items-center gap-4">
        <select name="action" class="px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="">Acción en masa...</option>
            {% for action in table.bulk_actions %}
            <option value="{{ action.name }}">{{ action.label }}</option>
            {% endfor %}
        </select>
        <button type="submit" class="btn btn-secondary btn-sm">Aplicar</button>
    </div>
    </form>
    {% endif %}
</div>
```

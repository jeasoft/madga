# Nitro 0.8 - JavaScript

## 14. Core JavaScript

### `static/nitro/nitro.js`

```javascript
/**
 * Nitro 0.8 - Core JavaScript
 * 
 * HTMX configuration, toast notifications, and utilities.
 */

// =============================================================================
// HTMX Configuration
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Configure HTMX
    document.body.addEventListener('htmx:configRequest', function(event) {
        // Add CSRF token to all requests
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value 
            || document.querySelector('meta[name=csrf-token]')?.content;
        if (csrfToken) {
            event.detail.headers['X-CSRFToken'] = csrfToken;
        }
    });
    
    // Handle toast triggers from HTMX responses
    document.body.addEventListener('htmx:afterRequest', function(event) {
        const trigger = event.detail.xhr?.getResponseHeader('HX-Trigger');
        if (trigger) {
            try {
                const data = JSON.parse(trigger);
                if (data.showToast) {
                    window.dispatchEvent(new CustomEvent('show-toast', { 
                        detail: data.showToast 
                    }));
                }
            } catch (e) {
                // Non-JSON trigger, ignore
            }
        }
    });
    
    // Handle errors
    document.body.addEventListener('htmx:responseError', function(event) {
        console.error('HTMX Error:', event.detail);
        window.dispatchEvent(new CustomEvent('show-toast', {
            detail: { message: 'Error de conexión. Intenta de nuevo.', type: 'error' }
        }));
    });
    
    // Loading indicators
    document.body.addEventListener('htmx:beforeRequest', function(event) {
        const target = event.detail.target;
        if (target) {
            target.classList.add('htmx-loading');
        }
    });
    
    document.body.addEventListener('htmx:afterRequest', function(event) {
        const target = event.detail.target;
        if (target) {
            target.classList.remove('htmx-loading');
        }
    });
});


// =============================================================================
// Toast Notifications (Vanilla JS fallback)
// =============================================================================

const NitroToast = {
    container: null,
    toasts: [],
    counter: 0,
    
    init() {
        if (this.container) return;
        
        this.container = document.createElement('div');
        this.container.id = 'nitro-toast-container';
        this.container.className = 'fixed bottom-4 right-4 z-50 space-y-2';
        document.body.appendChild(this.container);
        
        // Listen for events
        window.addEventListener('show-toast', (e) => this.show(e.detail));
        
        // HTMX trigger support
        document.body.addEventListener('showToast', (e) => this.show(e.detail));
    },
    
    show({ message, type = 'info', duration = 5000 }) {
        const id = ++this.counter;
        const colors = {
            success: 'bg-green-50 border-green-200 text-green-800',
            error: 'bg-red-50 border-red-200 text-red-800',
            warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
            info: 'bg-blue-50 border-blue-200 text-blue-800',
        };
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ',
        };
        
        const toast = document.createElement('div');
        toast.id = `toast-${id}`;
        toast.className = `flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg max-w-sm transform transition-all duration-300 translate-y-2 opacity-0 ${colors[type] || colors.info}`;
        toast.innerHTML = `
            <span>${icons[type] || icons.info}</span>
            <span class="flex-1">${this.escapeHtml(message)}</span>
            <button onclick="NitroToast.remove(${id})" class="text-gray-400 hover:text-gray-600">×</button>
        `;
        
        this.container.appendChild(toast);
        
        // Animate in
        requestAnimationFrame(() => {
            toast.classList.remove('translate-y-2', 'opacity-0');
        });
        
        // Auto remove
        if (duration > 0) {
            setTimeout(() => this.remove(id), duration);
        }
        
        return id;
    },
    
    remove(id) {
        const toast = document.getElementById(`toast-${id}`);
        if (toast) {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 300);
        }
    },
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    // Convenience methods
    success(message, duration) { return this.show({ message, type: 'success', duration }); },
    error(message, duration) { return this.show({ message, type: 'error', duration }); },
    warning(message, duration) { return this.show({ message, type: 'warning', duration }); },
    info(message, duration) { return this.show({ message, type: 'info', duration }); },
};

// Auto-init
document.addEventListener('DOMContentLoaded', () => NitroToast.init());


// =============================================================================
// Utility Functions
// =============================================================================

const NitroUtils = {
    /**
     * Copy text to clipboard
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            NitroToast.success('Copiado al portapapeles');
            return true;
        } catch (err) {
            NitroToast.error('Error al copiar');
            return false;
        }
    },
    
    /**
     * Format currency
     */
    formatCurrency(amount, currency = 'DOP') {
        const symbols = { DOP: 'RD$', USD: 'US$', EUR: '€' };
        const symbol = symbols[currency] || currency;
        return `${symbol} ${parseFloat(amount).toLocaleString('es-DO', { minimumFractionDigits: 2 })}`;
    },
    
    /**
     * Format phone number
     */
    formatPhone(phone) {
        const digits = phone.replace(/\D/g, '');
        if (digits.length === 10) {
            return `(${digits.slice(0,3)}) ${digits.slice(3,6)}-${digits.slice(6)}`;
        }
        return phone;
    },
    
    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /**
     * Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * Generate WhatsApp link
     */
    whatsappLink(phone, message = '') {
        const cleanPhone = phone.replace(/\D/g, '');
        let url = `https://wa.me/${cleanPhone}`;
        if (message) {
            url += `?text=${encodeURIComponent(message)}`;
        }
        return url;
    },
};

// Expose globally
window.NitroToast = NitroToast;
window.NitroUtils = NitroUtils;
```

---

## 15. Alpine Components

### `static/nitro/alpine-components.js`

```javascript
/**
 * Nitro 0.8 - Alpine.js Components
 * 
 * Reusable Alpine components for common UI patterns.
 * 
 * Usage:
 *   <script src="{% static 'nitro/alpine-components.js' %}"></script>
 *   <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
 */

document.addEventListener('alpine:init', () => {
    
    // =========================================================================
    // Toast Manager
    // =========================================================================
    Alpine.data('toastManager', () => ({
        toasts: [],
        counter: 0,
        
        add({ message, type = 'info', duration = 5000 }) {
            const id = ++this.counter;
            this.toasts.push({ id, message, type, visible: true });
            
            if (duration > 0) {
                setTimeout(() => this.remove(id), duration);
            }
        },
        
        remove(id) {
            const toast = this.toasts.find(t => t.id === id);
            if (toast) {
                toast.visible = false;
                setTimeout(() => {
                    this.toasts = this.toasts.filter(t => t.id !== id);
                }, 300);
            }
        }
    }));
    
    
    // =========================================================================
    // Clipboard Copy
    // =========================================================================
    Alpine.data('clipboard', () => ({
        copied: false,
        
        async copy(text) {
            try {
                await navigator.clipboard.writeText(text);
                this.copied = true;
                setTimeout(() => this.copied = false, 2000);
            } catch (err) {
                console.error('Copy failed:', err);
            }
        }
    }));
    
    
    // =========================================================================
    // File Upload with Drag & Drop
    // =========================================================================
    Alpine.data('fileUpload', () => ({
        dragging: false,
        file: null,
        files: [],
        multiple: false,
        
        handleDrop(event) {
            this.dragging = false;
            const files = event.dataTransfer.files;
            if (this.multiple) {
                this.files = [...files];
            } else {
                this.file = files[0];
            }
        },
        
        handleSelect(event) {
            const files = event.target.files;
            if (this.multiple) {
                this.files = [...files];
            } else {
                this.file = files[0];
            }
        },
        
        removeFile(index) {
            if (this.multiple) {
                this.files.splice(index, 1);
            } else {
                this.file = null;
            }
        },
        
        formatSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    }));
    
    
    // =========================================================================
    // Character Counter
    // =========================================================================
    Alpine.data('charCounter', (maxLength) => ({
        count: 0,
        max: maxLength,
        
        update(event) {
            this.count = event.target.value.length;
        },
        
        get remaining() {
            return this.max - this.count;
        },
        
        get isOver() {
            return this.count > this.max;
        }
    }));
    
    
    // =========================================================================
    // Searchable Select (like Select2)
    // =========================================================================
    Alpine.data('searchableSelect', (options, initialValue = '', initialLabel = '') => ({
        open: false,
        search: '',
        value: initialValue,
        displayLabel: initialLabel,
        options: options,
        highlightedIndex: -1,
        
        get filteredOptions() {
            if (!this.search) return this.options;
            const query = this.search.toLowerCase();
            return this.options.filter(opt => 
                opt.label.toLowerCase().includes(query)
            );
        },
        
        select(option) {
            this.value = option.value;
            this.displayLabel = option.label;
            this.open = false;
            this.search = '';
            this.$refs.input?.dispatchEvent(new Event('change', { bubbles: true }));
        },
        
        clear() {
            this.value = '';
            this.displayLabel = '';
            this.search = '';
            this.$refs.input?.dispatchEvent(new Event('change', { bubbles: true }));
        },
        
        handleKeydown(event) {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                this.highlightedIndex = Math.min(
                    this.highlightedIndex + 1, 
                    this.filteredOptions.length - 1
                );
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                this.highlightedIndex = Math.max(this.highlightedIndex - 1, 0);
            } else if (event.key === 'Enter' && this.highlightedIndex >= 0) {
                event.preventDefault();
                this.select(this.filteredOptions[this.highlightedIndex]);
            } else if (event.key === 'Escape') {
                this.open = false;
            }
        }
    }));
    
    
    // =========================================================================
    // Confirm Action Modal
    // =========================================================================
    Alpine.data('confirmAction', () => ({
        show: false,
        title: '',
        message: '',
        action: null,
        onConfirm: null,
        confirmText: 'Confirmar',
        cancelText: 'Cancelar',
        danger: false,
        
        ask({ title, message, onConfirm, confirmText = 'Confirmar', cancelText = 'Cancelar', danger = false }) {
            this.title = title;
            this.message = message;
            this.onConfirm = onConfirm;
            this.confirmText = confirmText;
            this.cancelText = cancelText;
            this.danger = danger;
            this.show = true;
        },
        
        confirm() {
            if (this.onConfirm) {
                this.onConfirm();
            }
            this.close();
        },
        
        close() {
            this.show = false;
            this.onConfirm = null;
        }
    }));
    
    
    // =========================================================================
    // Toggle (for collapsible sections)
    // =========================================================================
    Alpine.data('toggle', (initialOpen = false) => ({
        open: initialOpen,
        
        toggle() {
            this.open = !this.open;
        }
    }));
    
    
    // =========================================================================
    // Tabs
    // =========================================================================
    Alpine.data('tabs', (defaultTab = '') => ({
        activeTab: defaultTab,
        
        isActive(tab) {
            return this.activeTab === tab;
        },
        
        setActive(tab) {
            this.activeTab = tab;
        }
    }));
    
    
    // =========================================================================
    // Infinite Scroll
    // =========================================================================
    Alpine.data('infiniteScroll', (loadMoreUrl) => ({
        loading: false,
        page: 1,
        hasMore: true,
        
        async loadMore() {
            if (this.loading || !this.hasMore) return;
            
            this.loading = true;
            this.page++;
            
            try {
                const response = await fetch(`${loadMoreUrl}?page=${this.page}`, {
                    headers: { 'HX-Request': 'true' }
                });
                
                if (!response.ok) throw new Error('Failed to load');
                
                const html = await response.text();
                if (!html.trim()) {
                    this.hasMore = false;
                } else {
                    this.$refs.container.insertAdjacentHTML('beforeend', html);
                }
            } catch (error) {
                console.error('Load more failed:', error);
                this.page--;
            } finally {
                this.loading = false;
            }
        },
        
        checkScroll() {
            const container = this.$refs.container;
            if (!container) return;
            
            const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
            if (scrollTop + clientHeight >= scrollHeight - 200) {
                this.loadMore();
            }
        }
    }));
    
    
    // =========================================================================
    // Currency Input
    // =========================================================================
    Alpine.data('currencyInput', (initialValue = '') => ({
        raw: initialValue,
        
        get formatted() {
            if (!this.raw) return '';
            const num = parseFloat(this.raw);
            if (isNaN(num)) return this.raw;
            return num.toLocaleString('es-DO', { minimumFractionDigits: 2 });
        },
        
        handleInput(event) {
            // Remove non-numeric except decimal
            let value = event.target.value.replace(/[^0-9.]/g, '');
            // Keep only first decimal point
            const parts = value.split('.');
            if (parts.length > 2) {
                value = parts[0] + '.' + parts.slice(1).join('');
            }
            this.raw = value;
        }
    }));
    
    
    // =========================================================================
    // Phone Input
    // =========================================================================
    Alpine.data('phoneInput', () => ({
        raw: '',
        
        get formatted() {
            const digits = this.raw.replace(/\D/g, '');
            if (digits.length >= 10) {
                return `(${digits.slice(0,3)}) ${digits.slice(3,6)}-${digits.slice(6,10)}`;
            }
            return this.raw;
        },
        
        handleInput(event) {
            this.raw = event.target.value.replace(/\D/g, '').slice(0, 10);
        }
    }));
    
    
    // =========================================================================
    // Dark Mode Toggle
    // =========================================================================
    Alpine.data('darkMode', () => ({
        dark: localStorage.getItem('darkMode') === 'true' || 
              (localStorage.getItem('darkMode') === null && 
               window.matchMedia('(prefers-color-scheme: dark)').matches),
        
        init() {
            this.updateClass();
        },
        
        toggle() {
            this.dark = !this.dark;
            localStorage.setItem('darkMode', this.dark);
            this.updateClass();
        },
        
        updateClass() {
            document.documentElement.classList.toggle('dark', this.dark);
        }
    }));
    
    
    // =========================================================================
    // Form Dirty Check
    // =========================================================================
    Alpine.data('dirtyForm', () => ({
        isDirty: false,
        initialData: '',
        
        init() {
            this.$nextTick(() => {
                this.initialData = new FormData(this.$el).toString();
            });
            
            window.addEventListener('beforeunload', (e) => {
                if (this.isDirty) {
                    e.preventDefault();
                    e.returnValue = '';
                }
            });
        },
        
        checkDirty() {
            const currentData = new FormData(this.$el).toString();
            this.isDirty = currentData !== this.initialData;
        },
        
        markClean() {
            this.isDirty = false;
            this.initialData = new FormData(this.$el).toString();
        }
    }));
    
});


// =============================================================================
// HTMX Extensions
// =============================================================================

// Handle confirm-action events from modals
document.body.addEventListener('confirm-action', function(event) {
    const { action, method } = event.detail;
    if (action && method) {
        htmx.ajax(method.toUpperCase(), action, { target: 'body' });
    }
});
```

---

## 16. CSS Utilities

### Tailwind CSS Classes to Add

```css
/* Add to your tailwind.css or global styles */

/* HTMX loading state */
.htmx-loading {
    @apply opacity-50 pointer-events-none;
}

/* Button variants */
.btn {
    @apply inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2;
}

.btn-primary {
    @apply bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500;
}

.btn-secondary {
    @apply bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-primary-500;
}

.btn-danger {
    @apply bg-red-600 text-white hover:bg-red-700 focus:ring-red-500;
}

.btn-ghost {
    @apply text-gray-600 hover:bg-gray-100 focus:ring-gray-500;
}

.btn-sm {
    @apply px-3 py-1.5 text-xs;
}

.btn-lg {
    @apply px-6 py-3 text-base;
}

/* Card */
.card {
    @apply bg-white rounded-xl border shadow-sm;
}

.card-header {
    @apply px-4 py-3 border-b;
}

.card-body {
    @apply p-4;
}

/* Input */
.input {
    @apply w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500;
}

.input-error {
    @apply border-red-500 focus:ring-red-500 focus:border-red-500;
}

/* Mobile FAB */
.fab {
    @apply fixed bottom-20 right-4 z-40 w-14 h-14 bg-primary-600 text-white rounded-full shadow-lg flex items-center justify-center text-2xl hover:bg-primary-700 active:scale-95 transition-transform md:hidden;
}

/* Skeleton loading */
.skeleton {
    @apply bg-gray-200 rounded animate-pulse;
}

/* Hide on x-cloak before Alpine loads */
[x-cloak] {
    display: none !important;
}
```

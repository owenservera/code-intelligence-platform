/**
 * CIP Dashboard v2.0 - Reusable UI Components
 * Handles: Modals, dropdowns, tooltips, badges, progress bars,
 *          confirmations, file viewers, code blocks
 */

// === Modal Component ===
class Modal {
    constructor(options = {}) {
        this.title = options.title || 'Modal';
        this.content = options.content || '';
        this.size = options.size || 'md'; // sm, md, lg, xl, full
        this.footer = options.footer || null;
        this.onClose = options.onClose || null;
        this.element = null;

        this._create();
    }

    _create() {
        this.element = document.createElement('div');
        this.element.className = 'modal-overlay';
        this.element.innerHTML = `
            <div class="modal-dialog size-${this.size}">
                <div class="modal-header">
                    <h3 class="modal-title">${this.title}</h3>
                    <button class="modal-close" aria-label="Close">&times;</button>
                </div>
                <div class="modal-body">${this.content}</div>
                ${this.footer ? `<div class="modal-footer">${this.footer}</div>` : ''}
            </div>
        `;

        // Close handlers
        this.element.querySelector('.modal-close').addEventListener('click', () => this.close());
        this.element.addEventListener('click', (e) => {
            if (e.target === this.element) this.close();
        });

        // Escape key
        document.addEventListener('keydown', this._escHandler = (e) => {
            if (e.key === 'Escape') this.close();
        });
    }

    open() {
        document.body.appendChild(this.element);
        requestAnimationFrame(() => {
            this.element.classList.add('active');
        });
        return this;
    }

    close() {
        this.element.classList.remove('active');
        setTimeout(() => {
            this.element.remove();
            if (this.onClose) this.onClose();
        }, 300);
        document.removeEventListener('keydown', this._escHandler);
    }

    setContent(content) {
        this.element.querySelector('.modal-body').innerHTML = content;
    }

    setTitle(title) {
        this.element.querySelector('.modal-title').textContent = title;
    }
}

// === Confirmation Dialog ===
function showConfirm(options = {}) {
    return new Promise((resolve) => {
        const {
            title = 'Confirm',
            message = 'Are you sure?',
            confirmText = 'Confirm',
            cancelText = 'Cancel',
            danger = false
        } = options;

        const modal = new Modal({
            title,
            size: 'sm',
            content: `<p>${message}</p>`,
            footer: `
                <button class="btn btn-secondary" id="modal-cancel">${cancelText}</button>
                <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" id="modal-confirm">${confirmText}</button>
            `,
            onClose: () => resolve(false)
        });

        modal.open();

        modal.element.querySelector('#modal-cancel').addEventListener('click', () => {
            modal.close();
            resolve(false);
        });

        modal.element.querySelector('#modal-confirm').addEventListener('click', () => {
            modal.close();
            resolve(true);
        });
    });
}

// === Dropdown Component ===
class Dropdown {
    constructor(triggerElement, menuItems, options = {}) {
        this.trigger = triggerElement;
        this.items = menuItems;
        this.align = options.align || 'left';
        this.menuElement = null;
        this.isOpen = false;

        this._create();
        this._bindEvents();
    }

    _create() {
        this.menuElement = document.createElement('div');
        this.menuElement.className = `dropdown-menu align-${this.align}`;

        this.items.forEach(item => {
            if (item.divider) {
                this.menuElement.innerHTML += '<div class="dropdown-divider"></div>';
                return;
            }

            if (item.header) {
                this.menuElement.innerHTML += `<div class="dropdown-header">${item.header}</div>`;
                return;
            }

            const itemEl = document.createElement('button');
            itemEl.className = `dropdown-item ${item.danger ? 'danger' : ''} ${item.disabled ? 'disabled' : ''}`;
            itemEl.innerHTML = `
                ${item.icon ? `<span>${item.icon}</span>` : ''}
                <span>${item.label}</span>
            `;

            if (item.action) {
                itemEl.addEventListener('click', () => {
                    item.action();
                    this.close();
                });
            }

            this.menuElement.appendChild(itemEl);
        });

        // Wrap trigger in dropdown container if not already
        if (!this.trigger.parentElement.classList.contains('dropdown')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'dropdown';
            this.trigger.parentNode.insertBefore(wrapper, this.trigger);
            wrapper.appendChild(this.trigger);
            wrapper.appendChild(this.menuElement);
        } else {
            this.trigger.parentElement.appendChild(this.menuElement);
        }
    }

    _bindEvents() {
        this.trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        document.addEventListener('click', () => {
            if (this.isOpen) this.close();
        });
    }

    toggle() {
        this.isOpen ? this.close() : this.open();
    }

    open() {
        this.menuElement.classList.add('active');
        this.isOpen = true;
    }

    close() {
        this.menuElement.classList.remove('active');
        this.isOpen = false;
    }
}

// === Toast Notification System ===
class ToastManager {
    constructor() {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    show(message, options = {}) {
        const {
            type = 'info', // success, error, warning, info
            title = null,
            duration = 5000,
            icon = null
        } = options;

        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-icon">${icon || icons[type]}</div>
            <div class="toast-content">
                ${title ? `<div class="toast-title">${title}</div>` : ''}
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close">&times;</button>
            ${duration > 0 ? `<div class="toast-progress" style="animation-duration: ${duration}ms"></div>` : ''}
        `;

        this.container.appendChild(toast);

        // Close button
        toast.querySelector('.toast-close').addEventListener('click', () => {
            this._remove(toast);
        });

        // Auto-remove
        if (duration > 0) {
            setTimeout(() => this._remove(toast), duration);
        }

        return toast;
    }

    success(message, options = {}) {
        return this.show(message, { ...options, type: 'success' });
    }

    error(message, options = {}) {
        return this.show(message, { ...options, type: 'error', duration: 8000 });
    }

    warning(message, options = {}) {
        return this.show(message, { ...options, type: 'warning' });
    }

    info(message, options = {}) {
        return this.show(message, { ...options, type: 'info' });
    }

    _remove(toast) {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }
}

// Global toast instance
const toast = new ToastManager();

// === Progress Bar Component ===
class ProgressBar {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        this.label = options.label || '';
        this.type = options.type || 'primary';
        this.striped = options.striped || false;
        this.indeterminate = options.indeterminate || false;

        this._create();
    }

    _create() {
        this.container.innerHTML = `
            <div class="progress-container">
                ${this.label ? `
                    <div class="progress-label">
                        <span>${this.label}</span>
                        <span class="progress-percent">0%</span>
                    </div>
                ` : ''}
                <div class="progress-bar">
                    <div class="progress-fill ${this.type} ${this.striped ? 'striped' : ''} ${this.indeterminate ? 'indeterminate' : ''}"
                         style="width: 0%"></div>
                </div>
            </div>
        `;

        this.fillElement = this.container.querySelector('.progress-fill');
        this.percentElement = this.container.querySelector('.progress-percent');
    }

    update(percent) {
        if (this.indeterminate) return;

        percent = Math.max(0, Math.min(100, percent));
        this.fillElement.style.width = `${percent}%`;

        if (this.percentElement) {
            this.percentElement.textContent = `${Math.round(percent)}%`;
        }
    }

    setLabel(label) {
        const labelEl = this.container.querySelector('.progress-label span:first-child');
        if (labelEl) labelEl.textContent = label;
    }

    complete() {
        this.update(100);
        this.fillElement.style.background = '#4CAF50';
    }

    error() {
        this.fillElement.style.background = '#F44336';
    }
}

// === Code Block Component ===
function createCodeBlock(code, options = {}) {
    const {
        language = 'text',
        filename = null,
        lineNumbers = true,
        highlightLines = []
    } = options;

    const lines = code.split('\n');
    const linesHtml = lines.map((line, index) => {
        const lineNum = index + 1;
        const isHighlighted = highlightLines.includes(lineNum);

        return `
            <div class="code-line ${isHighlighted ? 'highlighted' : ''}">
                ${lineNumbers ? `<span class="line-number">${lineNum}</span>` : ''}
                <span class="line-content">${escapeHtml(line)}</span>
            </div>
        `;
    }).join('');

    return `
        <div class="code-block">
            ${filename ? `
                <div class="code-block-header">
                    <span>${filename}</span>
                    <span>${language}</span>
                </div>
            ` : ''}
            <div class="code-block-body">${linesHtml}</div>
        </div>
    `;
}

// === Tooltip Component ===
function initTooltips() {
    document.querySelectorAll('[data-tooltip]').forEach(element => {
        const text = element.dataset.tooltip;
        const position = element.dataset.tooltipPosition || 'top';

        const wrapper = document.createElement('div');
        wrapper.className = 'tooltip-wrapper';
        element.parentNode.insertBefore(wrapper, element);
        wrapper.appendChild(element);

        const tooltip = document.createElement('div');
        tooltip.className = `tooltip-content position-${position}`;
        tooltip.textContent = text;
        wrapper.appendChild(tooltip);
    });
}

// === File Viewer Component ===
class FileViewer {
    constructor() {
        this.modal = null;
    }

    async open(path, line = null) {
        try {
            // Fetch file content
            const response = await fetch(`/api/file?path=${encodeURIComponent(path)}`);
            if (!response.ok) throw new Error('File not found');

            const data = await response.json();
            const content = data.content || '';

            // Create code block
            const codeBlock = createCodeBlock(content, {
                filename: path,
                language: this._detectLanguage(path),
                lineNumbers: true,
                highlightLines: line ? [line] : []
            });

            // Show in modal
            this.modal = new Modal({
                title: `📄 ${path}`,
                content: codeBlock,
                size: 'lg'
            });

            this.modal.open();

            // Scroll to line if specified
            if (line) {
                setTimeout(() => {
                    const highlighted = this.modal.element.querySelector('.code-line.highlighted');
                    highlighted?.scrollIntoView({ block: 'center' });
                }, 100);
            }

        } catch (e) {
            toast.error(`Failed to open file: ${e.message}`);
        }
    }

    _detectLanguage(path) {
        const ext = path.split('.').pop().toLowerCase();
        const langMap = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'jsx': 'javascript',
            'go': 'go',
            'rs': 'rust',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'h': 'c',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'toml': 'toml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown'
        };
        return langMap[ext] || 'text';
    }
}

// Global file viewer instance
const fileViewer = new FileViewer();

// === Utility Functions ===
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDuration(ms) {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function (...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// === Initialize Components on DOM Ready ===
document.addEventListener('DOMContentLoaded', () => {
    initTooltips();

    // Make components globally available
    window.Modal = Modal;
    window.showConfirm = showConfirm;
    window.Dropdown = Dropdown;
    window.toast = toast;
    window.ProgressBar = ProgressBar;
    window.createCodeBlock = createCodeBlock;
    window.fileViewer = fileViewer;
    window.escapeHtml = escapeHtml;
    window.formatBytes = formatBytes;
    window.formatDuration = formatDuration;
    window.debounce = debounce;
    window.throttle = throttle;
});

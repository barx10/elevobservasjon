// Student Engagement Observation App - Client-side JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if Bootstrap tooltips are present
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-dismissible)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.transition = 'opacity 0.5s ease-out';
                alert.style.opacity = '0';
                setTimeout(() => {
                    alert.remove();
                }, 500);
            }
        }, 5000);
    });

    // Confirm deletion dialogs
    const deleteButtons = document.querySelectorAll('button[onclick*="confirm"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const confirmed = confirm(this.getAttribute('onclick').match(/confirm\('([^']+)'\)/)[1]);
            if (!confirmed) {
                e.preventDefault();
                return false;
            }
        });
    });

    // Add keyboard navigation for observation buttons
    const observationButtons = document.querySelectorAll('.observation-btn');
    observationButtons.forEach(button => {
        button.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });

    // Mobile-friendly tap handling
    if ('ontouchstart' in window) {
        // Add touch feedback for better mobile experience
        const cards = document.querySelectorAll('.student-card');
        cards.forEach(card => {
            card.addEventListener('touchstart', function() {
                this.style.transform = 'scale(0.98)';
            });
            
            card.addEventListener('touchend', function() {
                setTimeout(() => {
                    this.style.transform = '';
                }, 100);
            });
        });
    }

    // Form validation enhancements - only for observation forms, not management forms
    const observationForms = document.querySelectorAll('form[action*="record_observation"]');
    observationForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            console.log('Form submit event triggered for:', form.action);
            const requiredFields = form.querySelectorAll('[required]');
            let hasErrors = false;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    hasErrors = true;
                    console.log('Validation error for field:', field.name);
                } else {
                    field.classList.remove('is-invalid');
                }
            });

            if (hasErrors) {
                console.log('Preventing form submission due to validation errors');
                e.preventDefault();
                const firstError = form.querySelector('.is-invalid');
                if (firstError) {
                    firstError.focus();
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            } else {
                console.log('Form validation passed, allowing submission');
            }
        });

        // Real-time validation feedback
        const inputs = form.querySelectorAll('input[required], select[required]');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (!this.value.trim()) {
                    this.classList.add('is-invalid');
                } else {
                    this.classList.remove('is-invalid');
                }
            });

            input.addEventListener('input', function() {
                if (this.classList.contains('is-invalid') && this.value.trim()) {
                    this.classList.remove('is-invalid');
                }
            });
        });
    });

    // Allow all other forms to submit normally without interference
    console.log('JavaScript validation limited to observation forms only');

    // Statistics page enhancements
    if (window.location.pathname.includes('/statistics')) {
        // Add click handlers for expandable rows or additional details
        const tableRows = document.querySelectorAll('tbody tr');
        tableRows.forEach(row => {
            row.style.cursor = 'pointer';
            row.addEventListener('click', function() {
                // Visual feedback when clicking on statistics rows
                this.style.backgroundColor = 'rgba(13, 110, 253, 0.1)';
                setTimeout(() => {
                    this.style.backgroundColor = '';
                }, 200);
            });
        });
    }

    // Keyboard shortcuts for power users
    document.addEventListener('keydown', function(e) {
        // Alt + H: Go to home
        if (e.altKey && e.key === 'h') {
            e.preventDefault();
            window.location.href = '/';
        }
        
        // Alt + M: Go to manage classes
        if (e.altKey && e.key === 'm') {
            e.preventDefault();
            window.location.href = '/manage_classes';
        }
        
        // Alt + S: Go to statistics
        if (e.altKey && e.key === 's') {
            e.preventDefault();
            window.location.href = '/statistics';
        }
    });

    // Service worker registration for offline functionality (if needed in future)
    if ('serviceWorker' in navigator) {
        // Placeholder for future offline functionality
        console.log('Service Worker support detected - ready for offline features');
    }

    // Add visual feedback for form submissions
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        button.addEventListener('click', function() {
            const form = this.closest('form');
            if (form && form.checkValidity()) {
                this.disabled = true;
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Behandler...';
                
                // Re-enable after 3 seconds as failsafe
                setTimeout(() => {
                    this.disabled = false;
                    this.innerHTML = originalText;
                }, 3000);
            }
        });
    });

    // Enhanced accessibility features
    const focusableElements = document.querySelectorAll('button, input, select, textarea, a[href]');
    focusableElements.forEach(element => {
        element.addEventListener('focus', function() {
            this.style.outline = '2px solid var(--bs-primary)';
            this.style.outlineOffset = '2px';
        });
        
        element.addEventListener('blur', function() {
            this.style.outline = '';
            this.style.outlineOffset = '';
        });
    });

    console.log('Student Engagement Observation App initialized successfully');
});

// Utility functions
function showToast(message, type = 'success') {
    // Create a toast notification
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1060';
    document.body.appendChild(container);
    return container;
}

// Export functions for use in other scripts
window.StudentEngagementApp = {
    showToast: showToast
};

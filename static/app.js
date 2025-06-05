// Student Engagement Observation App - Client-side JavaScript
// Minimal version to avoid blocking form submissions

document.addEventListener('DOMContentLoaded', function() {
    console.log('Student Engagement Observation App initialized successfully');

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

    // Mobile-friendly tap handling
    if ('ontouchstart' in window) {
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

    // Service worker registration for offline functionality (if needed in future)
    if ('serviceWorker' in navigator) {
        console.log('Service Worker support detected - ready for offline features');
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

    console.log('Form submissions enabled without JavaScript interference');
});

// Utility functions
function showToast(message, type = 'success') {
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
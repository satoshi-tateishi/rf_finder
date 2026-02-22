/**
 * Toast Notification System
 */

(function() {
    const toastContainer = document.getElementById('toast-container');

    /**
     * Show a toast notification.
     * @param {string} message - The message to display.
     * @param {'success'|'error'|'info'} type - The type of toast (e.g., 'success', 'error', 'info').
     * @param {number} duration - How long the toast should be visible in milliseconds. Default is 3000ms.
     */
    window.showToast = function(message, type = 'info', duration = 3000) {
        if (!toastContainer) {
            console.warn('Toast container not found. Displaying alert instead:', message);
            alert(`[${type.toUpperCase()}] ${message}`);
            return;
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type} px-4 py-2 rounded-md shadow-lg text-white`;
        toast.textContent = message;

        toastContainer.appendChild(toast);

        // Show the toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 10); // Small delay for CSS transition

        // Hide and remove after duration
        setTimeout(() => {
            toast.classList.remove('show');
            toast.classList.add('hide');
            toast.addEventListener('animationend', () => {
                toast.remove();
            }, { once: true });
        }, duration);
    };
})();

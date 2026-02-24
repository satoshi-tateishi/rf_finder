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

    /**
     * Show a custom decision modal (Promise-based confirm).
     * @param {Object} options - { title, message, okText, cancelText, iconClass }
     * @returns {Promise<boolean>}
     */
    window.showDecisionModal = function(options = {}) {
        console.log('[Modal] showDecisionModal called', options);
        const modal = document.getElementById('decision-modal');
        const titleEl = document.getElementById('decision-title');
        const msgEl = document.getElementById('decision-message');
        const okBtn = document.getElementById('decision-ok-btn');
        const cancelBtn = document.getElementById('decision-cancel-btn');
        const iconEl = document.getElementById('decision-fa-icon');

        if (!modal) {
            console.warn('[Modal] decision-modal not found in DOM');
            return Promise.resolve(confirm(options.message));
        }

        titleEl.textContent = options.title || '確認';
        msgEl.innerHTML = options.message || '';
        okBtn.textContent = options.okText || 'OK';
        cancelBtn.textContent = options.cancelText || 'キャンセル';
        
        // Cancel button color customization
        if (options.cancelColor === 'red') {
            cancelBtn.classList.remove('text-gray-500');
            cancelBtn.classList.add('text-red-500');
        } else {
            cancelBtn.classList.remove('text-red-500');
            cancelBtn.classList.add('text-gray-500');
        }
        
        if (options.iconClass) {
            iconEl.className = `fa-solid ${options.iconClass} fa-2xl`;
        } else {
            iconEl.className = 'fa-solid fa-circle-question fa-2xl';
        }

        console.log('[Modal] Removing hidden class from decision-modal');
        modal.classList.remove('hidden');
        modal.style.display = 'flex'; // Ensure display is flex

        return new Promise((resolve) => {
            const handleOk = () => {
                cleanup();
                resolve(true);
            };
            const handleCancel = () => {
                cleanup();
                resolve(false);
            };
            const cleanup = () => {
                console.log('[Modal] cleanup called');
                okBtn.removeEventListener('click', handleOk);
                cancelBtn.removeEventListener('click', handleCancel);
                modal.classList.add('hidden');
                modal.style.display = ''; // Clear inline style to allow 'hidden' class to work
            };

            okBtn.addEventListener('click', handleOk);
            cancelBtn.addEventListener('click', handleCancel);
        });
    };
})();

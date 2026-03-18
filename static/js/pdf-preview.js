/**
 * PDF Preview Modal module
 */
const PdfPreview = (function() {
    let _currentUrl = null;

    function open(blob) {
        if (_currentUrl) window.URL.revokeObjectURL(_currentUrl);
        _currentUrl = window.URL.createObjectURL(blob);

        const embed = document.getElementById('preview-embed');
        const modal = document.getElementById('preview-modal');
        const mobileMsg = document.getElementById('preview-mobile-msg');

        if (!embed || !modal || !mobileMsg) {
            console.error('Preview modal elements not found');
            return;
        }

        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

        if (isMobile) {
            embed.classList.add('hidden');
            mobileMsg.classList.remove('hidden');
        } else {
            embed.src = _currentUrl;
            embed.classList.remove('hidden');
            mobileMsg.classList.add('hidden');
        }

        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    function close() {
        const modal = document.getElementById('preview-modal');
        const embed = document.getElementById('preview-embed');

        if (modal) modal.classList.add('hidden');
        if (embed) embed.removeAttribute('src');
        document.body.classList.remove('overflow-hidden');

        if (_currentUrl) {
            window.URL.revokeObjectURL(_currentUrl);
            _currentUrl = null;
        }
    }

    function openDirectly() {
        if (_currentUrl) {
            window.open(_currentUrl, '_blank');
        }
    }

    return { open, close, openDirectly };
})();

// Global scope alias for HTML attributes
window.closePreviewModal = PdfPreview.close;
window.openPdfDirectly = PdfPreview.openDirectly;

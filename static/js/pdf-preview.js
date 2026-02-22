/**
 * PDF Preview Modal module
 */
const PdfPreview = (function() {
    let _currentUrl = null;

    function open(blob) {
        if (_currentUrl) window.URL.revokeObjectURL(_currentUrl);
        _currentUrl = window.URL.createObjectURL(blob);
        
        const iframe = document.getElementById('preview-iframe');
        const modal = document.getElementById('preview-modal');
        const mobileMsg = document.getElementById('preview-mobile-msg');
        
        if (!iframe || !modal || !mobileMsg) {
            console.error('Preview modal elements not found');
            return;
        }
        
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        
        if (isMobile) {
            iframe.classList.add('hidden');
            mobileMsg.classList.remove('hidden');
        } else {
            iframe.src = _currentUrl + '#toolbar=0&navpanes=0&scrollbar=0';
            iframe.classList.remove('hidden');
            mobileMsg.classList.add('hidden');
        }
        
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    function close() {
        const modal = document.getElementById('preview-modal');
        const iframe = document.getElementById('preview-iframe');
        
        if (modal) modal.classList.add('hidden');
        if (iframe) iframe.src = '';
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

/**
 * PDF Preview Modal module
 */
const PdfPreview = (function() {
    let _currentUrl = null;

    function open(blob, targetWindow = null) {
        if (_currentUrl) window.URL.revokeObjectURL(_currentUrl);
        _currentUrl = window.URL.createObjectURL(blob);

        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

        // デスクトップ：事前に開いたウィンドウへ PDF をナビゲート
        if (!isMobile && targetWindow && !targetWindow.closed) {
            targetWindow.location.href = _currentUrl;
            return;
        }

        // モバイル or フォールバック：モーダルで「直接開く」ボタンを表示
        const embed = document.getElementById('preview-embed');
        const modal = document.getElementById('preview-modal');
        const mobileMsg = document.getElementById('preview-mobile-msg');

        if (!modal || !mobileMsg) {
            console.error('Preview modal elements not found');
            return;
        }

        if (embed) embed.classList.add('hidden');
        mobileMsg.classList.remove('hidden');
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    function close() {
        const modal = document.getElementById('preview-modal');
        if (modal) modal.classList.add('hidden');
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

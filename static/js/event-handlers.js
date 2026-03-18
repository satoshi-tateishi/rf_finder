// イベントハンドラ登録
// インラインの onclick / oninput 属性を排除し、CSP 準拠の addEventListener 方式で登録する

document.addEventListener('DOMContentLoaded', function () {

    // ---- PDF プレビューモーダル ----
    const previewCloseBtn = document.getElementById('preview-close-btn');
    if (previewCloseBtn) {
        previewCloseBtn.addEventListener('click', closePreviewModal);
    }

    const pdfDirectBtn = document.getElementById('pdf-direct-btn');
    if (pdfDirectBtn) {
        pdfDirectBtn.addEventListener('click', openPdfDirectly);
    }

    // ---- サイドメニュー ----
    const menuToggleBtn = document.getElementById('menu-toggle-btn');
    if (menuToggleBtn) {
        menuToggleBtn.addEventListener('click', toggleMenu);
    }

    const menuOverlay = document.getElementById('menu-overlay');
    if (menuOverlay) {
        menuOverlay.addEventListener('click', toggleMenu);
    }

    const menuCloseBtn = document.getElementById('menu-close-btn');
    if (menuCloseBtn) {
        menuCloseBtn.addEventListener('click', toggleMenu);
    }

    // ---- 管理者メニューボタン ----
    const auditLogMenuBtn = document.getElementById('audit-log-menu-btn');
    if (auditLogMenuBtn) {
        auditLogMenuBtn.addEventListener('click', openAuditLogModal);
    }

    const backupMenuBtn = document.getElementById('backup-menu-btn');
    if (backupMenuBtn) {
        backupMenuBtn.addEventListener('click', openBackupModal);
    }

    // ---- 申請履歴モーダル ----
    const historyOpenBtn = document.getElementById('history-open-btn');
    if (historyOpenBtn) {
        historyOpenBtn.addEventListener('click', openHistoryModal);
    }

    const historyCloseBtn = document.getElementById('history-close-btn');
    if (historyCloseBtn) {
        historyCloseBtn.addEventListener('click', closeHistoryModal);
    }

    const historyRefreshBtn = document.getElementById('history-refresh-btn');
    if (historyRefreshBtn) {
        historyRefreshBtn.addEventListener('click', refreshHistory);
    }

    // ---- 運用調整フォーム操作 ----
    const goToAdjustmentBtn = document.getElementById('go-to-adjustment-btn');
    if (goToAdjustmentBtn) {
        goToAdjustmentBtn.addEventListener('click', createNewAdjustment);
    }

    const saveDraftBtn = document.getElementById('save-draft-btn');
    if (saveDraftBtn) {
        saveDraftBtn.addEventListener('click', saveAdjustmentDraft);
    }

    const previewPdfBtn = document.getElementById('preview-pdf-btn');
    if (previewPdfBtn) {
        previewPdfBtn.addEventListener('click', previewPDF);
    }

    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    if (downloadPdfBtn) {
        downloadPdfBtn.addEventListener('click', downloadPDF);
    }

    const downloadExcelBtn = document.getElementById('download-excel-btn');
    if (downloadExcelBtn) {
        downloadExcelBtn.addEventListener('click', downloadExcel);
    }

    const sendEmailBtn = document.getElementById('send-email-btn');
    if (sendEmailBtn) {
        sendEmailBtn.addEventListener('click', sendEmail);
    }

    const backToSelectionBtn = document.getElementById('back-to-selection-btn');
    if (backToSelectionBtn) {
        backToSelectionBtn.addEventListener('click', backToSelection);
    }

    // ---- 53ch トグル ----
    const toggle53ch = document.getElementById('toggle-53ch');
    if (toggle53ch) {
        toggle53ch.addEventListener('click', function () {
            this.textContent = (this.textContent === '○' ? '' : '○');
        });
    }

    // ---- 文字数カウンター ----
    const eventNameInput = document.getElementById('event_name');
    const eventNameCounter = document.getElementById('event-name-counter');
    if (eventNameInput && eventNameCounter) {
        eventNameInput.addEventListener('input', function () {
            eventNameCounter.textContent = this.value.length + ' / 50';
        });
    }

    const commentTextarea = document.getElementById('comment');
    const commentCounter = document.getElementById('comment-counter');
    if (commentTextarea && commentCounter) {
        commentTextarea.addEventListener('input', function () {
            commentCounter.textContent = this.value.length + ' / 165';
        });
    }

    // ---- 監査ログモーダル ----
    const auditLogCloseBtn = document.getElementById('audit-log-close-btn');
    if (auditLogCloseBtn) {
        auditLogCloseBtn.addEventListener('click', closeAuditLogModal);
    }

    const auditLogRefreshBtn = document.getElementById('audit-log-refresh-btn');
    if (auditLogRefreshBtn) {
        auditLogRefreshBtn.addEventListener('click', refreshAuditLogs);
    }

    // ---- バックアップモーダル ----
    const backupCloseBtn = document.getElementById('backup-close-btn');
    if (backupCloseBtn) {
        backupCloseBtn.addEventListener('click', closeBackupModal);
    }

    const manualBackupBtn = document.getElementById('manual-backup-btn');
    if (manualBackupBtn) {
        manualBackupBtn.addEventListener('click', handleManualBackup);
    }

    // ---- チャンネル編集モーダル ----
    const channelEditCloseBtn = document.getElementById('channel-edit-close-btn');
    if (channelEditCloseBtn) {
        channelEditCloseBtn.addEventListener('click', closeChannelEditModal);
    }

    const channelEditCancelBtn = document.getElementById('channel-edit-cancel-btn');
    if (channelEditCancelBtn) {
        channelEditCancelBtn.addEventListener('click', closeChannelEditModal);
    }

    const channelEditConfirmBtn = document.getElementById('channel-edit-confirm-btn');
    if (channelEditConfirmBtn) {
        channelEditConfirmBtn.addEventListener('click', confirmChannelEdit);
    }
});

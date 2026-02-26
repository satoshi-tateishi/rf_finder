/**
 * Adjustment Form Management module
 */

function updateRequiredHighlight(el) {
    if (!el.hasAttribute('required')) return;
    const val = el.value;
    const isEmpty = !val || (typeof val === 'string' && val.trim() === "");
    
    if (isEmpty) {
        el.classList.add('required-empty');
    } else {
        el.classList.remove('required-empty');
    }
}

function updateMicCountsHighlight() {
    const container = document.getElementById('mic-counts-table-container');
    if (!container) return;

    const inputs = container.querySelectorAll('input, select');
    let hasValue = false;
    inputs.forEach(input => {
        if (input.value && input.value.trim() !== "") {
            hasValue = true;
        }
    });

    if (!hasValue) {
        container.classList.add('required-empty');
    } else {
        container.classList.remove('required-empty');
    }
}

function checkAllRequiredFields() {
    const container = document.getElementById('adjustment-form-section');
    if (!container) return;
    const inputs = container.querySelectorAll('input[required], select[required], textarea[required]');
    inputs.forEach(input => updateRequiredHighlight(input));
    
    // マイク数テーブルのチェック
    updateMicCountsHighlight();
}

// Global delegated listeners for required fields
document.addEventListener('input', (e) => {
    if (e.target.hasAttribute('required')) updateRequiredHighlight(e.target);
    
    // マイク数テーブル内の入力変更を監視
    if (e.target.closest('#mic-counts-table-container')) {
        updateMicCountsHighlight();
    }
});
document.addEventListener('change', (e) => {
    if (e.target.hasAttribute('required')) updateRequiredHighlight(e.target);
    
    // マイク数テーブル内の選択変更を監視
    if (e.target.closest('#mic-counts-table-container')) {
        updateMicCountsHighlight();
    }
});

function goToAdjustment() {
    if (AppState.KeepList.isEmpty()) {
        showToast('施設を選択してください', 'info');
        return;
    }

    // 新規作成時のみユーザー情報を初期入力
    if (!AppState.currentAdjustmentId) {
        AppState.setAdjustment(null, 'draft');
        prefillUserInfo();
    }

    // 使用場所・日程リストの生成
    const container = document.getElementById('form-facilities-list');
    container.innerHTML = '';
    
    AppState.KeepList.get().forEach((f, index) => {
        // AppState に既にデータがある場合はそれを使用し、なければ空（デフォルト）を使用
        // renderer に渡すオブジェクトを構築
        const currentData = {
            start_date: f.start_date || '',
            end_date: f.end_date || '',
            start_time: f.start_time || '09:00',
            end_time: f.end_time || '22:00'
        };
        
        // Renderer を使用して DOM 要素を生成し、追加
        const facilityItem = UIRenderer.createFacilityFormItem(f, index, currentData);
        container.appendChild(facilityItem);
    });

    document.getElementById('ch-selection-section').classList.add('hidden');
    document.getElementById('keep-list-section').classList.add('hidden');
    document.getElementById('adjustment-form-section').classList.remove('hidden');
    
    // ストレージから最新の状態（送信済みステータス等）を最終同期して AppState を更新
    const finalState = FormStorage.load();
    if (finalState && finalState.id === AppState.currentAdjustmentId) {
        AppState.setAdjustment(finalState.id, finalState.status || 'draft');
    }

    // ロールに応じた権限制限の適用 (送信済みロックも含む)
    applyRoleConstraints();

    // バリデーション用ハイライト初期化
    checkAllRequiredFields();

    window.scrollTo(0, 0);
}

function prefillUserInfo() {
    const user = AppState.currentUser;
    if (!user || !user.isAuthenticated) return;

    const nameEl = document.getElementById('user_name');
    const kanaEl = document.getElementById('user_kana');
    const telEl = document.getElementById('user_tel');
    const emailEl = document.getElementById('user_email');

    // 既に値がある場合は上書きしない
    if (!nameEl.value) nameEl.value = user.fullName || '';
    if (!kanaEl.value) kanaEl.value = user.fullKana || '';
    if (!telEl.value) telEl.value = user.phone || '';
    if (!emailEl.value) emailEl.value = user.email || '';
}

function applyRoleConstraints() {
    const role = AppState.currentUser?.role || 'guest';
    const isViewer = (role === 'viewer');
    const isSubmitted = (AppState.currentStatus === 'submitted');
    const isReadOnly = isViewer || isSubmitted;
    
    // 現在の申請区分を取得
    const appTypeEl = document.querySelector('input[name="app_type"]:checked');
    const appType = appTypeEl ? appTypeEl.value : 'new';

    // アクションボタンの制御
    const actionButtons = [
        '#send-email-btn',
        '#save-draft-btn',
        '#preview-pdf-btn',
        '#download-pdf-btn',
        '#download-excel-btn'
    ];

    actionButtons.forEach(selector => {
        const btn = document.querySelector(selector);
        if (btn) {
            const shouldDisable = isViewer || (selector === '#send-email-btn' && isSubmitted);
            btn.disabled = shouldDisable;
            if (shouldDisable) btn.classList.add('opacity-50', 'cursor-not-allowed');
            else btn.classList.remove('opacity-50', 'cursor-not-allowed');

            if (selector === '#send-email-btn') {
                btn.innerHTML = isSubmitted ? '<i class="fa-solid fa-check"></i> 送信済み' : '<i class="fa-solid fa-envelope"></i> 特ラ機構へ送信';
            }
        }
    });

    // 入力フィールドの全般的な制限
    const inputs = document.querySelectorAll('#adjustment-form-section input, #adjustment-form-section textarea, #adjustment-form-section select');
    inputs.forEach(el => {
        if (isReadOnly) {
            el.setAttribute('disabled', 'true');
            el.classList.add('bg-gray-100');
        } else {
            // 基本は有効化。ただし、app_type ラジオボタンと event_name は別途個別制御
            if (el.name !== 'app_type' && el.id !== 'event_name') {
                el.removeAttribute('disabled');
                el.classList.remove('bg-gray-100');
            }
        }
    });

    // 特定のフィールドに対する追加制限 (催事名)
    const eventNameInput = document.getElementById('event_name');
    if (eventNameInput) {
        if (isReadOnly || appType !== 'new') {
            eventNameInput.setAttribute('disabled', 'true');
            eventNameInput.classList.add('bg-gray-100');
        } else {
            eventNameInput.removeAttribute('disabled');
            eventNameInput.classList.remove('bg-gray-100');
        }
    }

    // 申請区分のラジオボタンの厳格な制御
    document.querySelectorAll('input[name="app_type"]').forEach(radio => {
        radio.setAttribute('disabled', 'true'); // 常に変更不可
        const label = radio.closest('label');
        if (label) {
            if (radio.value === appType) {
                label.classList.remove('cursor-not-allowed', 'opacity-50', 'bg-gray-100', 'text-gray-400');
                label.classList.add('cursor-default');
            } else {
                label.classList.add('cursor-not-allowed', 'opacity-50', 'bg-gray-100', 'text-gray-400');
                label.classList.remove('has-[:checked]:bg-blue-50', 'has-[:checked]:border-blue-500', 'has-[:checked]:text-blue-700',
                                     'has-[:checked]:bg-yellow-50', 'has-[:checked]:border-yellow-500', 'has-[:checked]:text-yellow-700',
                                     'has-[:checked]:bg-red-50', 'has-[:checked]:border-red-500', 'has-[:checked]:text-red-700');
            }
        }
    });

    if (isViewer) {
        showToast('閲覧専用モードです（編集・送信はできません）', 'info');
    }
}

function backToSelection() {
    document.getElementById('adjustment-form-section').classList.add('hidden');
    document.getElementById('keep-list-section').classList.remove('hidden');
    document.getElementById('ch-selection-section').classList.remove('hidden');
    window.scrollTo(0, 0);
}

/**
 * Validation and UI Feedback
 */
function handleValidationErrors(errOrList) {
    console.log('[Validation] Handling errors:', errOrList);
    
    // 以前のエラースタイルをクリア
    const container = document.getElementById('adjustment-form-section');
    if (container) {
        container.querySelectorAll('.bg-red-50').forEach(el => clearError(el));
    }

    let errorList = [];
    if (Array.isArray(errOrList)) {
        errorList = errOrList;
    } else {
        // API からの単一エラーまたは例外
        const msg = errOrList.message || errOrList;
        showToast(msg, 'error', 5000);
        return;
    }

    if (errorList.length === 0) return;

    // 最初のエラーメッセージを表示
    showToast(errorList[0].message, 'error', 5000);
    
    const fieldMap = {
        'user_name': 'user_name',
        'user_kana': 'user_kana',
        'user_tel': 'user_tel',
        'user_email': 'user_email',
        'event_name': 'event_name',
        'mic_counts': 'mic-counts-table-container',
        'facilities': 'form-facilities-list'
    };

    let firstErrEl = null;

    errorList.forEach(err => {
        let id = fieldMap[err.field];
        
        // 施設ごとのエラー対応 (facility_0, facility_1 ...)
        if (!id && err.field.startsWith('facility_')) {
            const index = parseInt(err.field.split('_')[1]);
            const facilitiesList = document.getElementById('form-facilities-list');
            if (facilitiesList && facilitiesList.children[index]) {
                const el = facilitiesList.children[index];
                applyErrorStyle(el);
                
                const inputs = el.querySelectorAll('input');
                inputs.forEach(input => {
                    input.addEventListener('input', () => clearError(el), { once: true });
                });
                
                if (!firstErrEl) firstErrEl = el;
            }
            return;
        }

        const el = document.getElementById(id);
        if (el) {
            applyErrorStyle(el);
            
            // 特別な処理: マイク数テーブル内の全入力にイベントリスナーを貼る
            if (err.field === 'mic_counts') {
                const inputs = el.querySelectorAll('input, select');
                inputs.forEach(input => {
                    const eventName = (input.tagName === 'SELECT') ? 'change' : 'input';
                    input.addEventListener(eventName, () => clearError(el), { once: true });
                });
            }
            
            if (!firstErrEl) firstErrEl = el;
        }
    });

    // 最初のエラー箇所へスクロール
    if (firstErrEl) {
        firstErrEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function applyErrorStyle(el) {
    el.classList.add('bg-red-50', 'border-red-500', 'ring-1', 'ring-red-500');
    const eventName = (el.tagName === 'SELECT') ? 'change' : 'input';
    el.addEventListener(eventName, () => clearError(el), { once: true });
}

function clearError(el) {
    el.classList.remove('bg-red-50', 'border-red-500', 'ring-1', 'ring-red-500');
}

/**
 * Main Actions
 */
async function previewPDF() {
    const data = FormService.collect();
    const btn = document.getElementById('preview-pdf-btn');
    const originalText = btn.innerHTML;
    
    // クライアント側バリデーション
    const errors = ValidationService.validate(data);
    if (errors.length > 0) {
        handleValidationErrors(errors);
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        const blob = await Api.previewPDF(data);
        PdfPreview.open(blob);
        showToast('PDFプレビューを表示しました', 'success');
    } catch (err) {
        // API から返ってくる構造化されたエラーまたは一般的なエラー
        handleValidationErrors(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function downloadPDF() {
    const data = FormService.collect();
    const btn = document.getElementById('download-pdf-btn');
    const originalText = btn.innerHTML;
    
    const errors = ValidationService.validate(data);
    if (errors.length > 0) {
        handleValidationErrors(errors);
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        const blob = await Api.previewPDF(data, 'attachment');
        
        if (blob.size < 1000) throw new Error('PDFの生成に失敗しました。');

        const url = window.URL.createObjectURL(blob);
        const appTypeMap = { 'new': '新規', 'change': '変更', 'delete': '削除' };
        const appTypeJp = appTypeMap[data.app_type] || '新規';
        const eventName = data.event.name || '無題の催事';
        const startDate = data.facilities[0]?.start_date?.replace(/-/g, '') || '未定';
        const filename = `運用連絡票_${appTypeJp}_${eventName}_${startDate}.pdf`;

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 1000);
        
        showToast('PDFをダウンロードしました', 'success');
    } catch (err) {
        handleValidationErrors(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function downloadExcel() {
    const data = FormService.collect();
    const btn = document.getElementById('download-excel-btn');
    const originalText = btn.innerHTML;
    
    const errors = ValidationService.validate(data);
    if (errors.length > 0) {
        handleValidationErrors(errors);
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        const blob = await Api.downloadExcel(data);

        if (blob.size < 100) throw new Error('Excelの生成に失敗しました。');

        const url = window.URL.createObjectURL(blob);
        const appTypeMap = { 'new': '新規', 'change': '変更', 'delete': '削除' };
        const appTypeJp = appTypeMap[data.app_type] || '新規';
        const eventName = data.event.name || '無題の催事';
        const startDate = data.facilities[0]?.start_date?.replace(/-/g, '') || '未定';
        const filename = `運用連絡票_${appTypeJp}_${eventName}_${startDate}.xlsx`;

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();

        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 1000);

        showToast('Excelをダウンロードしました', 'success');
    } catch (err) {
        handleValidationErrors(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function sendEmail() {
    const data = FormService.collect();
    
    // バリデーション
    const errors = ValidationService.validate(data);
    if (errors.length > 0) {
        handleValidationErrors(errors);
        return;
    }

    const confirmed = await showDecisionModal({
        title: '特ラ機構へ送信',
        message: '運用調整届を特ラ機構へ送信してもよろしいですか？',
        okText: '送信する',
        cancelText: '戻る',
        iconClass: 'fa-paper-plane'
    });
    if (!confirmed) return;

    const btn = document.getElementById('send-email-btn');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 送信中...';

    try {
        await Api.sendEmail(data);
        showToast('特ラ機構への送信が完了しました', 'success');
        
        // 送信成功時はボタンをロック
        AppState.setAdjustment(AppState.currentAdjustmentId, 'submitted');
        applyRoleConstraints();
        
        // クリアせずに現在の状態（submitted）を保存して同期を維持
        FormStorage.save(FormService.collect());
    } catch (err) {
        handleValidationErrors(err);
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

/**
 * State Management Integration
 */
async function restoreFormState() {
    const state = FormStorage.load();
    if (!state) return;
    // 第2引数に 'storage' を渡し、status の復元をスキップさせる
    await applyStateToForm(state, 'storage');
    showToast('前回の入力内容を復元しました', 'info');
}

async function applyStateToForm(state, source = 'api') {
    if (!state) return;

    try {
        console.log('[Form] Applying state...', state);
        
        // ステータスは API 由来のみを信用し、localStorage (FormStorage) 由来は無視する
        const status = (source === 'api') ? (state.status || 'draft') : AppState.currentStatus;
        AppState.setAdjustment(state.id || null, status, state.parent_id || null);
        
        const radio = document.querySelector(`input[name="app_type"][value="${state.app_type}"]`);
        if (radio) radio.checked = true;

        if (state.user) {
            document.getElementById('user_name').value = state.user.name || '';
            document.getElementById('user_kana').value = state.user.kana || '';
            document.getElementById('user_tel').value = state.user.tel || '';
            document.getElementById('user_email').value = state.user.email || '';
        }

        if (state.event) {
            document.getElementById('event_name').value = state.event.name || '';
            document.getElementById('comment').value = state.event.comment || '';
            const eventNameCounter = document.getElementById('event-name-counter');
            const commentCounter = document.getElementById('comment-counter');
            if (eventNameCounter) eventNameCounter.innerText = `${(state.event.name || '').length} / 50`;
            if (commentCounter) commentCounter.innerText = `${(state.event.comment || '').length} / 165`;
        }

        if (state.mic_counts) {
            const mc = state.mic_counts;
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val || '';
            };

            if (mc.analog_rm) setVal('mic-analog-rm-10mw', mc.analog_rm['10mw']);
            if (mc.analog_em) setVal('mic-analog-em-10mw', mc.analog_em['10mw']);
            if (mc.digital_rm) {
                setVal('mic-digital-rm-10mw', mc.digital_rm['10mw']);
                setVal('mic-digital-rm-20mw', mc.digital_rm['20mw']);
                setVal('mic-digital-rm-50mw', mc.digital_rm['50mw']);
            }
            if (mc.analog_53ch) {
                setVal('mic-analog-rm-53ch-10mw', mc.analog_53ch.rm_10mw);
                setVal('mic-analog-em-53ch-10mw', mc.analog_53ch.em_10mw);
            }
            if (mc.digital_53ch) {
                setVal('mic-digital-rm-53ch-10mw', mc.digital_53ch['10mw']);
                setVal('mic-digital-rm-53ch-20mw', mc.digital_53ch['20mw']);
                setVal('mic-digital-rm-53ch-50mw', mc.digital_53ch['50mw']);
            }
            if (mc.digital_12g) {
                setVal('mic-digital-rm-12g-10mw', mc.digital_12g['10mw']);
                setVal('mic-digital-rm-12g-20mw', mc.digital_12g['20mw']);
                setVal('mic-digital-rm-12g-50mw', mc.digital_12g['50mw']);
            }
            setVal('mic-12g-lmh', mc['12g_lmh']);
        }

        if (state.extra_53ch) {
            const toggle = document.getElementById('toggle-53ch');
            if (toggle) toggle.innerText = state.extra_53ch;
        }

        if (state.facilities && state.facilities.length > 0) {
            AppState.KeepList.clear();
            
            // 施設詳細を並列で取得して高速化
            try {
                const facilityPromises = state.facilities.map(sf => Api.getFacilityDetail(sf.id));
                const detailResults = await Promise.all(facilityPromises);
                
                detailResults.forEach((detail, index) => {
                    const sf = state.facilities[index];
                    AppState.KeepList.add({
                        ...detail.facility,
                        selectedChannels: sf.selectedChannels || [],
                        availableChannels: detail.available_channels,
                        // スケジュール情報も同期
                        start_date: sf.start_date || '',
                        end_date: sf.end_date || '',
                        start_time: sf.start_time || '09:00',
                        end_time: sf.end_time || '22:00'
                    });
                });
            } catch (e) {
                console.error('Failed to restore some facilities:', e);
            }
            
            if (!AppState.KeepList.isEmpty()) {
                renderKeepList();
                renderChannelSelection();
                document.getElementById('welcome-msg').classList.add('hidden');
                document.getElementById('keep-list-section').classList.remove('hidden');
                document.getElementById('ch-selection-section').classList.remove('hidden');
                
                goToAdjustment();
            }
        }
        checkAllRequiredFields();
    } catch (e) {
        console.error('Failed to apply state to form:', e);
        throw e;
    }
}

/**
 * History / Persistence Actions
 */
async function saveAdjustmentDraft() {
    try {
        const data = FormService.collect();
        const result = await Api.saveAdjustment(data);
        AppState.setAdjustment(result.id, 'draft');
        showToast('下書きを保存しました', 'success');
    } catch (err) {
        showToast(`保存に失敗しました: ${err.message}`, 'error');
    }
}

function openHistoryModal() {
    document.getElementById('history-modal').classList.remove('hidden');
    refreshHistory();
}

function closeHistoryModal() {
    document.getElementById('history-modal').classList.add('hidden');
}

async function refreshHistory() {
    const event_name = document.getElementById('history-search-event').value;
    const facility_name = document.getElementById('history-search-facility').value;
    const user_name = document.getElementById('history-search-user').value;
    
    const container = document.getElementById('history-list');
    container.innerHTML = '<div class="text-center py-10"><i class="fa-solid fa-spinner fa-spin fa-2x text-gray-300"></i></div>';
    
    try {
        const items = await Api.listAdjustments({ event_name, facility_name, user_name });
        container.innerHTML = '';
        
        if (items.length === 0) {
            container.innerHTML = '<div class="text-center py-10 text-gray-400 text-sm">データが見つかりません</div>';
            return;
        }
        
        items.forEach(item => {
            // Renderer を使用して DOM 要素を生成し、追加
            const card = UIRenderer.createHistoryCard(item, {
                onLoad: loadAdjustment,
                onPreview: previewHistoryItem,
                onCreateChange: (id) => createDerivedAdjustment(id, 'change'),
                onCreateDelete: (id) => createDerivedAdjustment(id, 'delete')
            });
            container.appendChild(card);
        });
    } catch (err) {
        container.innerHTML = `<div class="text-center py-10 text-red-500 text-sm">エラー: ${err.message}</div>`;
    }
}

async function loadAdjustment(id) {
    const confirmed = await showDecisionModal({
        title: 'データの読み込み',
        message: '現在入力中の内容は破棄されます。<br>よろしいですか？',
        okText: '読み込む',
        cancelText: 'キャンセル'
    });
    if (!confirmed) return;
    
    try {
        const data = await Api.getAdjustment(id);
        await applyStateToForm(data);
        closeHistoryModal();
        applyRoleConstraints(); // ロール制限を再適用
        showToast('データを読み込みました', 'success');
        FormStorage.save(data); // 復元用ストレージも同期
    } catch (err) {
        showToast(`読み込みに失敗しました: ${err.message}`, 'error');
    }
}

/**
 * 既存の「新規」または「変更」申請から、さらに「変更」または「削除」申請を作成する
 */
async function createDerivedAdjustment(parentId, type) {
    try {
        // 先に元データを取得して、正しいメッセージを表示できるようにする
        const data = await Api.getAdjustment(parentId);
        const originalTypeMap = { 'new': '新規', 'change': '変更' };
        const originalTypeName = originalTypeMap[data.app_type] || '新規';
        
        const typeName = type === 'change' ? '変更' : '削除';
        const confirmed = await showDecisionModal({
            title: `${typeName}申請の作成`,
            message: `【${data.event.name}】<br>の「${originalTypeName}」申請を元に、${typeName}申請を作成しますか？<br><br>※催事名は変更できません。`,
            okText: '作成する',
            cancelText: 'キャンセル',
            iconClass: type === 'change' ? 'fa-pen-to-square' : 'fa-trash-can'
        });
        if (!confirmed) return;

        // 派生申請として初期化
        data.id = null;
        data.status = 'draft';
        data.app_type = type;
        data.parent_id = parentId; // 親IDを保持

        await applyStateToForm(data);
        closeHistoryModal();
        applyRoleConstraints();
        showToast(`${typeName}申請を作成しました`, 'success');
        FormStorage.save(data);
    } catch (err) {
        showToast(`作成に失敗しました: ${err.message}`, 'error');
    }
}

async function previewHistoryItem(id) {
    showToast('プレビューを生成中...', 'info');
    try {
        const data = await Api.getAdjustment(id);
        const blob = await Api.previewPDF(data);
        PdfPreview.open(blob);
        showToast('プレビューを表示しました', 'success');
    } catch (err) {
        showToast(`プレビューの生成に失敗しました: ${err.message}`, 'error');
    }
}

let isWatcherInitialized = false;
function initChangeWatchers() {
    if (isWatcherInitialized) return;
    
    const container = document.getElementById('adjustment-form-section');
    if (!container) return;

    const handleChange = () => {
        const data = FormService.collect();
        FormStorage.save(data);
        
        // AppState にもスケジュール情報を同期
        if (data.facilities) {
            data.facilities.forEach(f => {
                AppState.KeepList.updateFacilityData(f.id, f);
            });
        }
    };
    container.addEventListener('input', handleChange);
    container.addEventListener('change', handleChange);
    
    const toggle53 = document.getElementById('toggle-53ch');
    if (toggle53) {
        const observer = new MutationObserver(handleChange);
        observer.observe(toggle53, { childList: true, characterData: true, subtree: true });
    }
    
    isWatcherInitialized = true;
}

// 初期化時に実行
window.addEventListener('DOMContentLoaded', async () => {
    // 他の初期化（KeepList等）が完了するのを待つ必要があるため、
    // ここではなく index.html の末尾で明示的に呼び出す形を維持
});

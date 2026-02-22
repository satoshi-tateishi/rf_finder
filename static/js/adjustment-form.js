/**
 * State Persistence
 */
const STORAGE_KEY = 'rf_finder_form_state';

function saveFormState() {
    const data = collectFormData();
    // 施設の基本情報（利用可能チャンネル等）は重いので除外、選択内容のみ保存
    const state = {
        app_type: data.app_type,
        user: data.user,
        event: data.event,
        mic_counts: data.mic_counts,
        extra_53ch: data.extra_53ch,
        // 施設はIDと日付・時間・選択チャンネルのみ保存
        facilities: data.facilities.map(f => ({
            id: f.id,
            start_date: f.start_date,
            end_date: f.end_date,
            start_time: f.start_time,
            end_time: f.end_time,
            selectedChannels: f.selectedChannels
        }))
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    console.log('[Form] State saved to localStorage');
}

async function restoreFormState() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return;

    try {
        const state = JSON.parse(saved);
        console.log('[Form] Restoring state...', state);

        // 1. 申請区分
        const radio = document.querySelector(`input[name="app_type"][value="${state.app_type}"]`);
        if (radio) radio.checked = true;

        // 2. 現地使用者
        if (state.user) {
            document.getElementById('user_name').value = state.user.name || '';
            document.getElementById('user_kana').value = state.user.kana || '';
            document.getElementById('user_tel').value = state.user.tel || '';
            document.getElementById('user_email').value = state.user.email || '';
        }

        // 3. 催事情報
        if (state.event) {
            document.getElementById('event_name').value = state.event.name || '';
            document.getElementById('comment').value = state.event.comment || '';
            document.getElementById('event-name-counter').innerText = `${(state.event.name || '').length} / 50`;
            document.getElementById('comment-counter').innerText = `${(state.event.comment || '').length} / 165`;
        }

        // 4. マイク数 (Matrix)
        if (state.mic_counts) {
            const mc = state.mic_counts;
            if (mc.analog_rm) document.getElementById('mic-analog-rm-10mw').value = mc.analog_rm['10mw'] || '';
            if (mc.analog_em) document.getElementById('mic-analog-em-10mw').value = mc.analog_em['10mw'] || '';
            if (mc.digital_rm) {
                document.getElementById('mic-digital-rm-10mw').value = mc.digital_rm['10mw'] || '';
                document.getElementById('mic-digital-rm-20mw').value = mc.digital_rm['20mw'] || '';
                document.getElementById('mic-digital-rm-50mw').value = mc.digital_rm['50mw'] || '';
            }
            if (mc.analog_53ch) {
                document.getElementById('mic-analog-rm-53ch-10mw').value = mc.analog_53ch.rm_10mw || '';
                document.getElementById('mic-analog-em-53ch-10mw').value = mc.analog_53ch.em_10mw || '';
            }
            if (mc.digital_53ch) {
                document.getElementById('mic-digital-rm-53ch-10mw').value = mc.digital_53ch['10mw'] || '';
                document.getElementById('mic-digital-rm-53ch-20mw').value = mc.digital_53ch['20mw'] || '';
                document.getElementById('mic-digital-rm-53ch-50mw').value = mc.digital_53ch['50mw'] || '';
            }
            if (mc.digital_12g) {
                document.getElementById('mic-digital-rm-12g-10mw').value = mc.digital_12g['10mw'] || '';
                document.getElementById('mic-digital-rm-12g-20mw').value = mc.digital_12g['20mw'] || '';
                document.getElementById('mic-digital-rm-12g-50mw').value = mc.digital_12g['50mw'] || '';
            }
            document.getElementById('mic-12g-lmh').value = mc['12g_lmh'] || '';
        }

        if (state.extra_53ch) {
            document.getElementById('toggle-53ch').innerText = state.extra_53ch;
        }

        // 5. 施設リストの復元 (キープリストを再構築)
        if (state.facilities && state.facilities.length > 0) {
            window.keepList = [];
            for (const sf of state.facilities) {
                try {
                    const facilityBase = await Api.getFacilityDetail(sf.id);
                    window.keepList.push({
                        ...facilityBase,
                        selectedChannels: sf.selectedChannels || [],
                        availableChannels: facilityBase.available_channels
                    });
                } catch (e) { console.error(`Failed to restore facility ${sf.id}:`, e); }
            }
            
            // UI更新
            if (window.keepList.length > 0) {
                renderKeepList();
                renderChannelSelection();
                document.getElementById('welcome-msg').classList.add('hidden');
                document.getElementById('keep-list-section').classList.remove('hidden');
                document.getElementById('ch-selection-section').classList.remove('hidden');
                
                // 調整フォームを表示
                goToAdjustment();
                
                // 各施設の日付・時間をセット
                state.facilities.forEach((sf, index) => {
                    const container = document.getElementById('form-facilities-list').children[index];
                    if (container) {
                        const inputs = container.querySelectorAll('input');
                        inputs[0].value = sf.start_date || '';
                        inputs[1].value = sf.end_date || '';
                        inputs[2].value = sf.start_time || '09:00';
                        inputs[3].value = sf.end_time || '22:00';
                    }
                });
            }
        }

        showToast('前回の入力内容を復元しました', 'info');
    } catch (e) {
        console.error('Failed to restore form state:', e);
        localStorage.removeItem(STORAGE_KEY);
    }
}

function clearFormState() {
    localStorage.removeItem(STORAGE_KEY);
}

// フォームの入力変更を監視して保存
function initChangeWatchers() {
    const container = document.getElementById('adjustment-form-section');
    if (!container) return;

    container.addEventListener('input', (e) => {
        saveFormState();
    });
    
    // ラジオボタンやセレクトボックスの変化も監視
    container.addEventListener('change', (e) => {
        saveFormState();
    });
    
    // 53chトグルも監視
    const toggle53 = document.getElementById('toggle-53ch');
    if (toggle53) {
        const observer = new MutationObserver(() => saveFormState());
        observer.observe(toggle53, { childList: true, characterData: true, subtree: true });
    }
}

/**
 * Adjustment Form Management module
 */
let currentPreviewUrl = null;

function goToAdjustment() {
    if (window.keepList.length === 0) {
        showToast('施設を選択してください', 'info');
        return;
    }

    // 使用場所・日程リストの生成
    const container = document.getElementById('form-facilities-list');
    container.innerHTML = '';
    
    window.keepList.forEach((f, index) => {
        const div = document.createElement('div');
        div.className = 'p-4 bg-gray-50 rounded-lg border border-gray-200';
        const formattedChannels = Api.formatChannels(f.selectedChannels);
        div.innerHTML = `
            <div class="flex items-center gap-2 mb-1">
                <span class="flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold">${index + 1}</span>
                <span class="font-bold text-sm text-gray-800">${f.name}</span>
            </div>
            <div class="ml-7 mb-3 text-[10px] text-blue-600 font-medium">
                使用チャンネル : ${formattedChannels}
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用開始日</label>
                    <input type="date" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" required oninput="clearError(this)">
                </div>
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用終了日</label>
                    <input type="date" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" required oninput="clearError(this)">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-3">
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用開始時間</label>
                    <input type="time" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" value="09:00" required oninput="clearError(this)">
                </div>
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用終了時間</label>
                    <input type="time" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" value="22:00" required oninput="clearError(this)">
                </div>
            </div>
        `;
        container.appendChild(div);
    });

    document.getElementById('ch-selection-section').classList.add('hidden');
    document.getElementById('keep-list-section').classList.add('hidden');
    document.getElementById('adjustment-form-section').classList.remove('hidden');
    window.scrollTo(0, 0);
}

function backToSelection() {
    document.getElementById('adjustment-form-section').classList.add('hidden');
    document.getElementById('keep-list-section').classList.remove('hidden');
    document.getElementById('ch-selection-section').classList.remove('hidden');
    window.scrollTo(0, 0);
}

function collectFormData() {
    const appType = document.querySelector('input[name="app_type"]:checked').value;
    const user = {
        name: document.getElementById('user_name').value,
        kana: document.getElementById('user_kana').value,
        tel: document.getElementById('user_tel').value,
        email: document.getElementById('user_email').value
    };
    const event = {
        name: document.getElementById('event_name').value,
        comment: document.getElementById('comment').value
    };
    
    const facilitiesData = keepList.map((f, index) => {
        const container = document.getElementById('form-facilities-list').children[index];
        const inputs = container.querySelectorAll('input');
        return {
            ...f,
            start_date: inputs[0].value,
            end_date: inputs[1].value,
            start_time: inputs[2].value,
            end_time: inputs[3].value
        };
    });

    const extra_53ch = document.getElementById('toggle-53ch').innerText;

    const mic_counts = {
        analog_rm: { '10mw': document.getElementById('mic-analog-rm-10mw').value },
        analog_em: { '10mw': document.getElementById('mic-analog-em-10mw').value },
        digital_rm: {
            '10mw': document.getElementById('mic-digital-rm-10mw').value,
            '20mw': document.getElementById('mic-digital-rm-20mw').value,
            '50mw': document.getElementById('mic-digital-rm-50mw').value
        },
        analog_53ch: {
            rm_10mw: document.getElementById('mic-analog-rm-53ch-10mw').value,
            em_10mw: document.getElementById('mic-analog-em-53ch-10mw').value
        },
        digital_53ch: {
            '10mw': document.getElementById('mic-digital-rm-53ch-10mw').value,
            '20mw': document.getElementById('mic-digital-rm-53ch-20mw').value,
            '50mw': document.getElementById('mic-digital-rm-53ch-50mw').value
        },
        digital_12g: {
            '10mw': document.getElementById('mic-digital-rm-12g-10mw').value,
            '20mw': document.getElementById('mic-digital-rm-12g-20mw').value,
            '50mw': document.getElementById('mic-digital-rm-12g-50mw').value
        },
        '12g_lmh': document.getElementById('mic-12g-lmh').value
    };

    return {
        app_type: appType,
        user: user,
        event: event,
        facilities: facilitiesData,
        extra_53ch: extra_53ch,
        mic_counts: mic_counts
    };
}

function handleValidationErrors(err) {
    console.error('[Validation] Full error:', err);
    const errorText = err.message || "Unknown error";
    
    // 1. 一般的な入力項目のハイライト
    const fieldMap = {
        'user_name': 'user_name',
        'user_kana': 'user_kana',
        'user_tel': 'user_tel',
        'user_email': 'user_email',
        'event_name': 'event_name'
    };

    let foundField = false;
    Object.keys(fieldMap).forEach(key => {
        if (errorText.includes(key)) {
            const el = document.getElementById(fieldMap[key]);
            if (el) {
                applyErrorStyle(el);
                foundField = true;
            }
        }
    });

    // 2. マイク数のハイライト (テーブル全体)
    if (errorText.includes('mic_counts')) {
        const container = document.getElementById('mic-counts-table-container');
        if (container) {
            applyErrorStyle(container);
            foundField = true;
            // テーブル内のいずれかの入力が変わったらエラー表示を消す
            const inputs = container.querySelectorAll('input, select');
            inputs.forEach(input => {
                const eventName = (input.tagName === 'SELECT') ? 'change' : 'input';
                input.addEventListener(eventName, () => clearError(container), { once: true });
            });
        }
    }

    // 3. 施設日程のハイライト
    if (errorText.includes('facilities')) {
        const container = document.getElementById('form-facilities-list');
        if (container) {
            foundField = true;
            const inputs = container.querySelectorAll('input');
            inputs.forEach(input => {
                if (!input.value) applyErrorStyle(input);
            });
        }
    }

    const displayMsg = foundField 
        ? '入力内容に不備があります。赤色の項目を確認してください。'
        : `エラーが発生しました: ${errorText}`;

    showToast(displayMsg, 'error', 5000);
}

function applyErrorStyle(el) {
    el.classList.add('bg-red-50', 'border-red-500', 'ring-1', 'ring-red-500');
    // 入力されたら解除するイベントを追加
    const eventName = (el.tagName === 'SELECT') ? 'change' : 'input';
    el.addEventListener(eventName, () => clearError(el), { once: true });
}

function clearError(el) {
    el.classList.remove('bg-red-50', 'border-red-500', 'ring-1', 'ring-red-500');
}

async function previewPDF() {
    console.log('[Preview] Data collection started...');
    const data = collectFormData();
    console.log('[Preview] Data collected:', data);
    
    const btn = document.querySelector('button[onclick="previewPDF()"]');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        console.log('[Preview] Calling API...');
        const blob = await Api.previewPDF(data);
        console.log('[Preview] API Success, blob size:', blob.size);
        
        if (currentPreviewUrl) window.URL.revokeObjectURL(currentPreviewUrl);
        currentPreviewUrl = window.URL.createObjectURL(blob);
        
        const iframe = document.getElementById('preview-iframe');
        const modal = document.getElementById('preview-modal');
        const mobileMsg = document.getElementById('preview-mobile-msg');
        
        // モバイル（特にiOS）の判定
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        
        if (isMobile) {
            // モバイルの場合はインライン表示ができないことが多いため、
            // 直接新しいタブで開くことを促す
            iframe.classList.add('hidden');
            mobileMsg.classList.remove('hidden');
        } else {
            // #toolbar=0 でツールバー（ダウンロードボタン等）を隠す指示を出す
            iframe.src = currentPreviewUrl + '#toolbar=0&navpanes=0&scrollbar=0';
            iframe.classList.remove('hidden');
            mobileMsg.classList.add('hidden');
        }
        
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden'); // 背景スクロール禁止
        
    } catch (err) {
        console.error('[Preview] Error caught:', err);
        handleValidationErrors(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function closePreviewModal() {
    const modal = document.getElementById('preview-modal');
    const iframe = document.getElementById('preview-iframe');
    
    modal.classList.add('hidden');
    iframe.src = '';
    document.body.classList.remove('overflow-hidden');
    
    if (currentPreviewUrl) {
        window.URL.revokeObjectURL(currentPreviewUrl);
        currentPreviewUrl = null;
    }
}

function openPdfDirectly() {
    if (currentPreviewUrl) {
        window.open(currentPreviewUrl, '_blank');
    }
}

async function downloadPDF() {
    const data = collectFormData();
    const btn = document.querySelector('button[onclick="previewPDF()"]') || document.querySelector('button[onclick="downloadPDF()"]');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        const blob = await Api.previewPDF(data);
        const url = window.URL.createObjectURL(blob);
        
        // ファイル名の生成
        const appTypeMap = { 'new': '新規', 'change': '変更', 'delete': '削除' };
        const appTypeJp = appTypeMap[data.app_type] || '新規';
        const eventName = data.event.name || '無題の催事';
        const startDate = data.facilities[0]?.start_date?.replace(/-/g, '') || '未定';
        const filename = `運用連絡票_${appTypeJp}_${eventName}_${startDate}.pdf`;

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        
        showToast('PDFをダウンロードしました', 'success');
    } catch (err) {
        console.error(err);
        handleValidationErrors(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function downloadExcel() {
    const data = collectFormData();
    const btn = document.querySelector('button[onclick="downloadExcel()"]');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        const blob = await Api.downloadExcel(data);
        const url = window.URL.createObjectURL(blob);
        
        // ファイル名の生成
        const appTypeMap = { 'new': '新規', 'change': '変更', 'delete': '削除' };
        const appTypeJp = appTypeMap[data.app_type] || '新規';
        const eventName = data.event.name || '無題の催事';
        const startDate = data.facilities[0]?.start_date?.replace(/-/g, '') || '未定';
        const filename = `運用連絡票_${appTypeJp}_${eventName}_${startDate}.xlsx`;

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Excelをダウンロードしました', 'success');
    } catch (err) {
        console.error(err);
        handleValidationErrors(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function sendEmail() {
    if (!confirm('運用調整届を特ラ機構へ送信してもよろしいですか？')) return;

    const data = collectFormData();
    const btn = document.getElementById('send-email-btn');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 送信中...';

    try {
        await Api.sendEmail(data);
        showToast('特ラ機構への送信が完了しました', 'success');
    } catch (err) {
        console.error(err);
        handleValidationErrors(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

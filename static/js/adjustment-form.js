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
                    <label class="text-[10px] text-gray-500 block mb-1">使用開始日 <span class="text-red-500">*</span></label>
                    <input type="date" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" required>
                </div>
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用終了日 <span class="text-red-500">*</span></label>
                    <input type="date" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" required>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-3">
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用開始時間 <span class="text-red-500">*</span></label>
                    <input type="time" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" value="09:00" required>
                </div>
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用終了時間 <span class="text-red-500">*</span></label>
                    <input type="time" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" value="22:00" required>
                </div>
            </div>
        `;
        container.appendChild(div);
    });

    document.getElementById('ch-selection-section').classList.add('hidden');
    document.getElementById('keep-list-section').classList.add('hidden');
    document.getElementById('adjustment-form-section').classList.remove('hidden');
    
    // バリデーション用ハイライト初期化
    checkAllRequiredFields();

    window.scrollTo(0, 0);
}

function backToSelection() {
    document.getElementById('adjustment-form-section').classList.add('hidden');
    document.getElementById('keep-list-section').classList.remove('hidden');
    document.getElementById('ch-selection-section').classList.remove('hidden');
    window.scrollTo(0, 0);
}

function collectFormData() {
    const appTypeEl = document.querySelector('input[name="app_type"]:checked');
    const appType = appTypeEl ? appTypeEl.value : 'new';
    
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
    
    const facilitiesData = window.keepList.map((f, index) => {
        const container = document.getElementById('form-facilities-list').children[index];
        if (!container) return f;
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

/**
 * Validation and UI Feedback
 */
function handleValidationErrors(err) {
    console.error('[Validation] Full error:', err);
    const errorText = err.message || "Unknown error";
    
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
            if (el) { applyErrorStyle(el); foundField = true; }
        }
    });

    if (errorText.includes('mic_counts')) {
        const container = document.getElementById('mic-counts-table-container');
        if (container) {
            applyErrorStyle(container);
            foundField = true;
            const inputs = container.querySelectorAll('input, select');
            inputs.forEach(input => {
                const eventName = (input.tagName === 'SELECT') ? 'change' : 'input';
                input.addEventListener(eventName, () => clearError(container), { once: true });
            });
        }
    }

    if (errorText.includes('facilities')) {
        const container = document.getElementById('form-facilities-list');
        if (container) {
            foundField = true;
            const inputs = container.querySelectorAll('input');
            inputs.forEach(input => { if (!input.value) applyErrorStyle(input); });
        }
    }

    const displayMsg = foundField 
        ? '入力内容に不備があります。赤色の項目を確認してください。'
        : `エラーが発生しました: ${errorText}`;

    showToast(displayMsg, 'error', 5000);
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
    const data = collectFormData();
    const btn = document.querySelector('button[onclick="previewPDF()"]');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        const blob = await Api.previewPDF(data);
        PdfPreview.open(blob);
        showToast('PDFプレビューを表示しました', 'success');
    } catch (err) {
        handleValidationErrors(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function downloadPDF() {
    const data = collectFormData();
    const btn = document.querySelector('button[onclick="downloadPDF()"]');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        const blob = await Api.previewPDF(data);
        const url = window.URL.createObjectURL(blob);
        
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
        FormStorage.clear(); // 送信成功時は保存内容をクリア
    } catch (err) {
        handleValidationErrors(err);
    } finally {
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

    try {
        console.log('[Form] Restoring state...', state);

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
            document.getElementById('event-name-counter').innerText = `${(state.event.name || '').length} / 50`;
            document.getElementById('comment-counter').innerText = `${(state.event.comment || '').length} / 165`;
        }

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

        if (state.facilities && state.facilities.length > 0) {
            window.keepList = [];
            for (const sf of state.facilities) {
                try {
                    const data = await Api.getFacilityDetail(sf.id);
                    window.keepList.push({
                        ...data.facility, // 施設基本情報を展開 (name, address等)
                        selectedChannels: sf.selectedChannels || [],
                        availableChannels: data.available_channels
                    });
                } catch (e) { console.error(`Failed to restore facility ${sf.id}:`, e); }
            }
            
            if (window.keepList.length > 0) {
                renderKeepList();
                renderChannelSelection();
                document.getElementById('welcome-msg').classList.add('hidden');
                document.getElementById('keep-list-section').classList.remove('hidden');
                document.getElementById('ch-selection-section').classList.remove('hidden');
                
                goToAdjustment();
                
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
        
        // ハイライトの更新
        checkAllRequiredFields();
        
        showToast('前回の入力内容を復元しました', 'info');
    } catch (e) {
        console.error('Failed to restore form state:', e);
        FormStorage.clear();
    }
}

function initChangeWatchers() {
    const container = document.getElementById('adjustment-form-section');
    if (!container) return;

    const handleChange = () => FormStorage.save(collectFormData());
    container.addEventListener('input', handleChange);
    container.addEventListener('change', handleChange);
    
    const toggle53 = document.getElementById('toggle-53ch');
    if (toggle53) {
        const observer = new MutationObserver(handleChange);
        observer.observe(toggle53, { childList: true, characterData: true, subtree: true });
    }
}

// 初期化時に実行
window.addEventListener('DOMContentLoaded', async () => {
    // 他の初期化（KeepList等）が完了するのを待つ必要があるため、
    // ここではなく index.html の末尾で明示的に呼び出す形を維持
});

/**
 * Adjustment Form Management module
 */

function goToAdjustment() {
    if (keepList.length === 0) {
        alert('施設を選択してください');
        return;
    }

    // 使用場所・日程リストの生成
    const container = document.getElementById('form-facilities-list');
    container.innerHTML = '';
    
    keepList.forEach((f, index) => {
        const div = document.createElement('div');
        div.className = 'p-4 bg-gray-50 rounded-lg border border-gray-200';
        div.innerHTML = `
            <div class="flex items-center gap-2 mb-3">
                <span class="flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold">${index + 1}</span>
                <span class="font-bold text-sm text-gray-800">${f.name}</span>
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用開始日</label>
                    <input type="date" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" required>
                </div>
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用終了日</label>
                    <input type="date" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" required>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-3">
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用開始時間</label>
                    <input type="time" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" value="09:00" required>
                </div>
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用終了時間</label>
                    <input type="time" class="w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" value="22:00" required>
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

async function downloadExcel() {
    const data = collectFormData();
    const btn = document.querySelector('button[onclick="downloadExcel()"]');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        const response = await Api.downloadExcel(data);

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `運用連絡票_${new Date().toISOString().slice(0,10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } else {
            alert('Excelの生成に失敗しました');
        }
    } catch (err) {
        console.error(err);
        alert('通信エラーが発生しました');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function previewPDF() {
    const data = collectFormData();
    const btn = document.querySelector('button[onclick="previewPDF()"]');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        const response = await Api.previewPDF(data);

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            window.open(url, '_blank');
        } else {
            const errorText = await response.text();
            alert('PDFの生成に失敗しました: ' + errorText);
        }
    } catch (err) {
        console.error(err);
        alert('通信エラーが発生しました');
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
        alert('送信が完了しました。');
    } catch (err) {
        console.error(err);
        alert('送信に失敗しました: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

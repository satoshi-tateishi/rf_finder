/**
 * Adjustment Form Management module
 */

function autoFillUserProfile(profile) {
    if (!profile) return;
    
    // 1. 氏名の自動入力 ({姓} {名})
    const nameInput = document.getElementById('user_name');
    if (nameInput && !nameInput.value) {
        if (profile.userName) {
            const fullName = `${profile.userName.lastName} ${profile.userName.firstName}`;
            nameInput.value = fullName;
            console.log(`[WOFF] Auto-filled user name (detailed): ${fullName}`);
        } else if (profile.displayName) {
            nameInput.value = profile.displayName;
            console.log(`[WOFF] Auto-filled user name (basic): ${profile.displayName}`);
        }
    }

    // 2. ふりがなの自動入力 (カタカナをひらがなに変換)
    const kanaInput = document.getElementById('user_kana');
    if (kanaInput && !kanaInput.value && profile.userName) {
        if (profile.userName.phoneticLastName || profile.userName.phoneticFirstName) {
            let fullPhonetic = `${profile.userName.phoneticLastName || ''} ${profile.userName.phoneticFirstName || ''}`.trim();
            
            // カタカナからひらがなへの変換
            fullPhonetic = fullPhonetic.replace(/[\u30a1-\u30f6]/g, (match) => {
                const chr = match.charCodeAt(0) - 0x60;
                return String.fromCharCode(chr);
            });
            
            kanaInput.value = fullPhonetic;
            console.log(`[WOFF] Auto-filled user phonetic name (to hiragana): ${fullPhonetic}`);
        }
    }

    // 3. メールの自動入力 (個人メールを優先)
    const emailInput = document.getElementById('user_email');
    if (emailInput && !emailInput.value) {
        const email = profile.privateEmail || profile.email;
        if (email) {
            emailInput.value = email;
            console.log(`[WOFF] Auto-filled user email: ${email}`);
        }
    }

    // 4. 電話番号の自動入力 (電話番号を優先)
    const telInput = document.getElementById('user_tel');
    if (telInput && !telInput.value) {
        const phone = profile.telephone || profile.cellPhone;
        if (phone) {
            telInput.value = phone;
            console.log(`[WOFF] Auto-filled user tel: ${phone}`);
        }
    }
}

function goToAdjustment() {
    if (keepList.length === 0) {
        alert('施設を選択してください');
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
    // エラーメッセージ（文字列）からキーワードを抽出してハイライト
    const errorText = err.message || "";
    
    // 1. 一般的な入力項目のハイライト
    const fieldMap = {
        'user_name': 'user_name',
        'user_kana': 'user_kana',
        'user_tel': 'user_tel',
        'user_email': 'user_email',
        'event_name': 'event_name'
    };

    Object.keys(fieldMap).forEach(key => {
        if (errorText.includes(key)) {
            const el = document.getElementById(fieldMap[key]);
            if (el) applyErrorStyle(el);
        }
    });

    // 2. マイク数のハイライト (テーブル全体)
    if (errorText.includes('mic_counts')) {
        const container = document.getElementById('mic-counts-table-container');
        if (container) {
            applyErrorStyle(container);
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
            const inputs = container.querySelectorAll('input');
            inputs.forEach(input => {
                if (!input.value) applyErrorStyle(input);
            });
        }
    }

    alert('入力内容に不備があります。赤色の項目を確認してください。\n\n' + errorText);
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

async function downloadExcel() {
    const data = collectFormData();
    const btn = document.querySelector('button[onclick="downloadExcel()"]');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 生成中...';

    try {
        const blob = await Api.downloadExcel(data);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `運用連絡票_${new Date().toISOString().slice(0,10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
    } catch (err) {
        console.error(err);
        handleValidationErrors(err);
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
        const blob = await Api.previewPDF(data);
        const url = window.URL.createObjectURL(blob);
        window.open(url, '_blank');
    } catch (err) {
        console.error(err);
        handleValidationErrors(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function sendCompletionFlexMessage(data) {
    if (typeof WoffService === 'undefined' || !WoffService.isInClient()) return;

    const now = new Date();
    const timestamp = `${now.getFullYear()}/${now.getMonth() + 1}/${now.getDate()} ${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}`;
    
    // 施設名のリストを作成
    const facilityNames = data.facilities.map(f => f.name).join(' / ');

    const flexContents = {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "運用調整届 送信完了",
                    "weight": "bold",
                    "color": "#ffffff",
                    "size": "sm"
                }
            ],
            "backgroundColor": "#00c300"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": data.event.name || "無題の催事",
                    "weight": "bold",
                    "size": "md",
                    "wrap": true
                },
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "sm",
                            "contents": [
                                { "type": "text", "text": "使用者", "color": "#aaaaaa", "size": "xs", "flex": 2 },
                                { "type": "text", "text": data.user.name || "未入力", "wrap": true, "color": "#666666", "size": "xs", "flex": 5 }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "sm",
                            "contents": [
                                { "type": "text", "text": "施設", "color": "#aaaaaa", "size": "xs", "flex": 2 },
                                { "type": "text", "text": facilityNames, "wrap": true, "color": "#666666", "size": "xs", "flex": 5 }
                            ]
                        }
                    ]
                },
                {
                    "type": "text",
                    "text": `送信日時: ${timestamp}`,
                    "size": "xxs",
                    "color": "#cccccc",
                    "margin": "xl",
                    "align": "end"
                }
            ]
        }
    };

    console.log('[WOFF] Attempting to send completion flex message...');
    const result = await WoffService.sendFlexMessage(flexContents);
    console.log(`[WOFF] Message send result:`, result);
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
        
        // WOFF環境の場合、トークルームへ完了メッセージを送信 (Flex Message)
        await sendCompletionFlexMessage(data);

        alert('送信が完了しました。');
    } catch (err) {
        console.error(err);
        handleValidationErrors(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

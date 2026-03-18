/**
 * UI Renderers module
 * Responsible for generating HTML elements from data.
 */

const UIRenderer = (function() {
    
    /**
     * 履歴カードの DOM 要素を生成する
     */
    function createHistoryCard(item, handlers = {}) {
        const { onLoad, onPreview, onCreateChange, onCreateDelete, onCreateResend } = handlers;
        const div = document.createElement('div');
        const isDeleteType = (item.app_type === '削除');
        const isDerivableType = (item.app_type === '新規' || item.app_type === '変更');
        const isSubmitted = (item.status === '送信済み');
        const isDraft = (item.status === '下書き');
        const hasParent = !!item.parent_id;

        // 削除申請のみクリック不可（内容確認の必要がないため）
        const isReadLayer = isDeleteType;

        div.className = `p-3 bg-white border rounded-xl shadow-sm transition-all ${isReadLayer ? 'bg-gray-50' : 'hover:border-blue-500 cursor-pointer'}`;

        if (!isReadLayer && onLoad) {
            div.onclick = () => onLoad(item.id);
        }

        const statusColor = isDraft ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-700';

        let typeColor = 'bg-gray-100 text-gray-600';
        if (item.app_type === '新規') typeColor = 'bg-blue-100 text-blue-700';
        if (item.app_type === '変更') typeColor = 'bg-yellow-100 text-yellow-700';
        if (item.app_type === '削除') typeColor = 'bg-red-100 text-red-700';

        const contentOpacity = isDeleteType ? 'opacity-50' : '';

        // 親申請バッジ（派生申請の場合）
        const parentBadgeHtml = hasParent
            ? `<span class="text-[9px] text-purple-600 bg-purple-50 border border-purple-200 px-1.5 py-0.5 rounded font-medium"><i class="fa-solid fa-code-branch fa-xs"></i> 派生申請</span>`
            : '';

        // 送信済みの新規・変更に対して「変更/削除を作成」と「修正コピーを作成」を表示
        const derivedButtonsHtml = (isDerivableType && isSubmitted) ? `
                <button class="create-change-btn flex-1 text-[9px] font-bold text-yellow-600 border border-yellow-600 py-1 rounded hover:bg-yellow-50 transition-colors">
                    <i class="fa-solid fa-pen-to-square"></i> 変更を作成
                </button>
                <button class="create-delete-btn flex-1 text-[9px] font-bold text-red-600 border border-red-600 py-1 rounded hover:bg-red-50 transition-colors">
                    <i class="fa-solid fa-trash-can"></i> 削除を作成
                </button>
        ` : '';

        // 送信済みの場合「修正コピーを作成」を表示（削除を除く）
        const resendButtonHtml = (isSubmitted && !isDeleteType) ? `
                <button class="create-resend-btn flex-1 text-[9px] font-bold text-purple-600 border border-purple-600 py-1 rounded hover:bg-purple-50 transition-colors">
                    <i class="fa-solid fa-copy"></i> 修正コピーを作成
                </button>
        ` : '';

        const actionButtonsHtml = (derivedButtonsHtml || resendButtonHtml) ? `
            <div class="flex gap-2 mt-2 pt-2 border-t border-gray-100">
                ${derivedButtonsHtml}${resendButtonHtml}
            </div>
        ` : '';

        div.innerHTML = `
            <div class="${contentOpacity}">
                <div class="flex justify-between items-start mb-1">
                    <div class="flex items-center gap-1 flex-wrap">
                        <span class="text-xs font-bold px-2 py-0.5 rounded ${statusColor}">${item.status}</span>
                        ${parentBadgeHtml}
                    </div>
                    <span class="text-[10px] text-gray-400">${item.updated_at}</span>
                </div>
                <div class="flex items-center gap-2 mb-1">
                    <div class="font-bold text-gray-800 flex-1">${item.event_name || '（催事名なし）'}</div>
                    <span class="text-[9px] font-bold px-1.5 py-0.5 rounded ${typeColor} shrink-0">${item.app_type}</span>
                </div>
                <div class="text-xs text-gray-500 truncate mb-2">${item.facility_names.join(', ')}</div>
            </div>
            <div class="flex justify-between items-end">
                <div class="text-[10px] text-gray-400 ${contentOpacity}">
                    <div>現地使用者: ${item.user_name}</div>
                    <div class="mt-0.5">申請者&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: ${item.sender_name}</div>
                </div>
                <button class="preview-btn text-[10px] font-bold text-blue-600 border border-blue-600 px-2 py-1 rounded hover:bg-blue-50 transition-colors bg-white shrink-0">
                    <i class="fa-solid fa-eye"></i> プレビュー
                </button>
            </div>
            ${actionButtonsHtml}
        `;

        const previewBtn = div.querySelector('.preview-btn');
        if (previewBtn && onPreview) {
            previewBtn.onclick = (e) => {
                e.stopPropagation();
                onPreview(item.id);
            };
        }

        const changeBtn = div.querySelector('.create-change-btn');
        if (changeBtn && onCreateChange) {
            changeBtn.onclick = (e) => {
                e.stopPropagation();
                onCreateChange(item.id);
            };
        }

        const deleteBtn = div.querySelector('.create-delete-btn');
        if (deleteBtn && onCreateDelete) {
            deleteBtn.onclick = (e) => {
                e.stopPropagation();
                onCreateDelete(item.id);
            };
        }

        const resendBtn = div.querySelector('.create-resend-btn');
        if (resendBtn && onCreateResend) {
            resendBtn.onclick = (e) => {
                e.stopPropagation();
                onCreateResend(item.id, item.app_type);
            };
        }

        return div;
    }

    /**
     * 施設フォーム（使用場所・日程）の DOM 要素を生成する
     */
    function createFacilityFormItem(facility, index, savedData = {}, onChangeChannels = null) {
        const div = document.createElement('div');
        div.className = 'p-4 bg-gray-50 rounded-lg border border-gray-200';
        div.setAttribute('data-facility-id', facility.id);
        
        const formattedChannels = (typeof Api !== 'undefined' && Api.formatChannels) 
            ? Api.formatChannels(facility.selectedChannels) 
            : facility.selectedChannels.join(', ');

        div.innerHTML = `
            <div class="flex items-center gap-2 mb-1">
                <span class="flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold">${index + 1}</span>
                <span class="font-bold text-sm text-gray-800">${facility.name}</span>
            </div>
            <div class="ml-7 mb-3 flex items-center gap-2">
                <span class="channel-display text-[10px] text-blue-600 font-medium">使用チャンネル : ${formattedChannels}</span>
                <button class="change-channels-btn text-xs font-medium px-3 py-1.5 rounded-lg border border-blue-400 text-blue-600 hover:bg-blue-50 active:bg-blue-100 transition-colors flex items-center gap-1.5">
                    <i class="fa-solid fa-pen-to-square fa-xs"></i> 変更
                </button>
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用開始日 <span class="text-red-500">*</span></label>
                    <input type="date" data-field="start_date" class="start-date w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" 
                        value="${savedData.start_date || ''}" required>
                </div>
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用終了日 <span class="text-red-500">*</span></label>
                    <input type="date" data-field="end_date" class="end-date w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" 
                        value="${savedData.end_date || ''}" required>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-3">
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用開始時間 <span class="text-red-500">*</span></label>
                    <input type="time" data-field="start_time" class="start-time w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" 
                        value="${savedData.start_time || '09:00'}" required>
                </div>
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用終了時間 <span class="text-red-500">*</span></label>
                    <input type="time" data-field="end_time" class="end-time w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" 
                        value="${savedData.end_time || '22:00'}" required>
                </div>
            </div>
        `;
        const changeBtn = div.querySelector('.change-channels-btn');
        if (changeBtn && onChangeChannels) {
            changeBtn.onclick = () => onChangeChannels(facility.id, div);
        } else if (changeBtn) {
            changeBtn.classList.add('hidden');
        }

        return div;
    }

    /**
     * チャンネル選択画面の施設セクションを生成する
     */
    function createFacilitySection(facility, onExportWSM) {
        const section = document.createElement('div');
        section.className = 'bg-white p-4 rounded-lg shadow-sm border-l-4 border-blue-500';
        
        const categoryBadge = facility.category ? `<span class="bg-gray-100 text-gray-600 text-[9px] px-1.5 py-0.5 rounded border border-gray-200 whitespace-nowrap">${facility.category}</span>` : '';
        const areaBadge = facility.applied_area ? `<span class="bg-blue-50 text-blue-600 text-[9px] px-1.5 py-0.5 rounded border border-blue-100 whitespace-nowrap">${facility.applied_area}</span>` : '';
        const zipDisplay = facility.postal_code ? `<span class="mr-1">〒${facility.postal_code}</span>` : '';

        section.innerHTML = `
            <div class="mb-4 flex justify-between items-start">
                <div class="flex flex-col gap-1">
                    <div class="flex items-center gap-1 flex-wrap">
                        <span class="font-bold text-sm text-gray-800">${facility.name}</span>
                        ${categoryBadge}
                        ${areaBadge}
                    </div>
                    <div class="text-[10px] text-gray-400">${zipDisplay}${facility.address}</div>
                </div>
                <button id="wsm-btn-${facility.id}" class="wsm-btn bg-orange-500 hover:bg-orange-600 text-white text-[10px] font-bold py-1.5 px-3 rounded shadow-sm transition-colors flex items-center gap-1 shrink-0 opacity-50 cursor-not-allowed bg-gray-400" disabled>
                    <i class="fa-solid fa-file-csv"></i> WSM CSV
                </button>
            </div>
            <div class="grid-container ch-grid"></div>
        `;

        const wsmBtn = section.querySelector('.wsm-btn');
        if (wsmBtn && onExportWSM) {
            wsmBtn.onclick = () => onExportWSM(facility.id);
        }

        return section;
    }

    /**
     * チャンネルボタンを生成する
     */
    function createChannelButton(ch, chData, isSelected, devices, onClick) {
        const btn = document.createElement('div');
        btn.className = `ch-btn ${chData ? 'available' : 'disabled'} ${isSelected ? 'selected' : ''}`;
        btn.innerHTML = `<span>${ch}</span>`;
        
        if (chData && onClick) {
            btn.onclick = onClick;
            
            const chWidth = RADIO_SPEC.SPECIAL_WIDTHS[ch] ?? RADIO_SPEC.DEFAULT_WIDTH;

            // ガードバンド表示
            if (chData.gb_lower > 0) {
                const gb = document.createElement('div');
                gb.className = 'gb-indicator';
                gb.style.left = '0';
                gb.style.width = `${(chData.gb_lower / chWidth) * 100}%`;
                btn.appendChild(gb);
            }
            if (chData.gb_upper > 0) {
                const gb = document.createElement('div');
                gb.className = 'gb-indicator';
                gb.style.right = '0';
                gb.style.width = `${(chData.gb_upper / chWidth) * 100}%`;
                btn.appendChild(gb);
            }

            // デバイスインジケーター
            const indicators = document.createElement('div');
            indicators.className = 'device-indicators';
            
            const base_start = RADIO_SPEC.calculateChannelBase(ch);
            const base_end = base_start + chWidth;

            if (devices) {
                devices.forEach((d) => {
                    const overlap_min = Math.max(d.min, base_start);
                    const overlap_max = Math.min(d.max, base_end);
                    
                    const bar = document.createElement('div');
                    bar.className = 'device-bar';
                    
                    if (overlap_min < overlap_max) {
                        if (typeof getDeviceColor === 'function') {
                            bar.style.backgroundColor = getDeviceColor(d.name);
                        }
                        bar.style.width = `${(overlap_max - overlap_min) / chWidth * 100}%`;
                        bar.style.marginLeft = `${(overlap_min - base_start) / chWidth * 100}%`;
                    } else {
                        bar.style.backgroundColor = 'transparent';
                        bar.style.width = '100%';
                    }
                    indicators.appendChild(bar);
                });
            }
            btn.appendChild(indicators);
        }
        return btn;
    }

    /**
     * キープリストの項目を生成する
     */
    function createKeepItem(facility, index, onRemove) {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100';
        
        const categoryBadge = facility.category ? `<span class="bg-gray-100 text-gray-600 text-[9px] px-1.5 py-0.5 rounded border border-gray-200 whitespace-nowrap">${facility.category}</span>` : '';
        const areaBadge = facility.applied_area ? `<span class="bg-blue-50 text-blue-600 text-[9px] px-1.5 py-0.5 rounded border border-blue-100 whitespace-nowrap">${facility.applied_area}</span>` : '';
        const zipDisplay = facility.postal_code ? `<span class="mr-1">〒${facility.postal_code}</span>` : '';

        div.innerHTML = `
            <div class="drag-handle text-gray-400 cursor-grab active:cursor-grabbing px-1 py-2">
                <i class="fa-solid fa-grip-vertical"></i>
            </div>
            <div class="flex items-center justify-center w-6 h-6 rounded-full bg-green-100 text-green-700 text-xs font-bold shrink-0">
                ${index + 1}
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex flex-col gap-1">
                    <div class="flex items-center gap-1 flex-wrap">
                        <span class="font-bold text-sm text-gray-800">${facility.name}</span>
                        ${categoryBadge}
                        ${areaBadge}
                    </div>
                    <div class="text-[10px] text-gray-400">${zipDisplay}${facility.address}</div>
                </div>
            </div>
            <button class="remove-btn text-gray-300 hover:text-red-500 shrink-0">
                <i class="fa-solid fa-circle-xmark fa-lg"></i>
            </button>
        `;
        
        const removeBtn = div.querySelector('.remove-btn');
        if (removeBtn && onRemove) {
            removeBtn.onclick = () => onRemove(facility.id);
        }
        
        return div;
    }

    return {
        createHistoryCard,
        createFacilityFormItem,
        createFacilitySection,
        createChannelButton,
        createKeepItem
    };

})();

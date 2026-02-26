/**
 * UI Renderers module
 * Responsible for generating HTML elements from data.
 */

const UIRenderer = (function() {
    
    /**
     * 履歴カードの DOM 要素を生成する
     */
    function createHistoryCard(item, onLoad, onPreview) {
        const div = document.createElement('div');
        const isDeleteType = (item.app_type === '削除');
        
        div.className = `p-3 bg-white border rounded-xl shadow-sm transition-all ${isDeleteType ? 'bg-gray-50' : 'hover:border-blue-500 cursor-pointer'}`;
        
        if (!isDeleteType && onLoad) {
            div.onclick = () => onLoad(item.id);
        }
        
        const statusColor = item.status === '下書き' ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-700';
        
        let typeColor = 'bg-gray-100 text-gray-600';
        if (item.app_type === '新規') typeColor = 'bg-blue-100 text-blue-700';
        if (item.app_type === '変更') typeColor = 'bg-yellow-100 text-yellow-700';
        if (item.app_type === '削除') typeColor = 'bg-red-100 text-red-700';

        const contentOpacity = isDeleteType ? 'opacity-50' : '';

        div.innerHTML = `
            <div class="${contentOpacity}">
                <div class="flex justify-between items-start mb-1">
                    <span class="text-xs font-bold px-2 py-0.5 rounded ${statusColor}">${item.status}</span>
                    <span class="text-[10px] text-gray-400">${item.updated_at}</span>
                </div>
                <div class="flex items-center gap-2 mb-1">
                    <div class="font-bold text-gray-800 flex-1">${item.event_name || '（催事名なし）'}</div>
                    <span class="text-[9px] font-bold px-1.5 py-0.5 rounded ${typeColor} shrink-0">${item.app_type}</span>
                </div>
                <div class="text-xs text-gray-500 truncate mb-2">${item.facility_names.join(', ')}</div>
            </div>
            <div class="flex justify-between items-center">
                <div class="text-[10px] text-gray-400 ${contentOpacity}">${item.user_name}</div>
                <button class="preview-btn text-[10px] font-bold text-blue-600 border border-blue-600 px-2 py-1 rounded hover:bg-blue-50 transition-colors bg-white">
                    <i class="fa-solid fa-eye"></i> プレビュー
                </button>
            </div>
        `;

        const previewBtn = div.querySelector('.preview-btn');
        if (previewBtn && onPreview) {
            previewBtn.onclick = (e) => {
                e.stopPropagation();
                onPreview(item.id);
            };
        }

        return div;
    }

    /**
     * 施設フォーム（使用場所・日程）の DOM 要素を生成する
     */
    function createFacilityFormItem(facility, index, savedData = {}) {
        const div = document.createElement('div');
        div.className = 'p-4 bg-gray-50 rounded-lg border border-gray-200';
        
        const formattedChannels = (typeof Api !== 'undefined' && Api.formatChannels) 
            ? Api.formatChannels(facility.selectedChannels) 
            : facility.selectedChannels.join(', ');

        div.innerHTML = `
            <div class="flex items-center gap-2 mb-1">
                <span class="flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] font-bold">${index + 1}</span>
                <span class="font-bold text-sm text-gray-800">${facility.name}</span>
            </div>
            <div class="ml-7 mb-3 text-[10px] text-blue-600 font-medium">
                使用チャンネル : ${formattedChannels}
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用開始日 <span class="text-red-500">*</span></label>
                    <input type="date" class="start-date w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" 
                        value="${savedData.start_date || ''}" required>
                </div>
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用終了日 <span class="text-red-500">*</span></label>
                    <input type="date" class="end-date w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" 
                        value="${savedData.end_date || ''}" required>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-3">
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用開始時間 <span class="text-red-500">*</span></label>
                    <input type="time" class="start-time w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" 
                        value="${savedData.start_time || '09:00'}" required>
                </div>
                <div>
                    <label class="text-[10px] text-gray-500 block mb-1">使用終了時間 <span class="text-red-500">*</span></label>
                    <input type="time" class="end-time w-full border border-gray-300 p-2 rounded text-xs outline-none focus:ring-1 focus:ring-blue-500" 
                        value="${savedData.end_time || '22:00'}" required>
                </div>
            </div>
        `;
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
    function createChannelButton(ch, chData, isSelected, onClick) {
        const btn = document.createElement('div');
        btn.className = `ch-btn ${chData ? 'available' : 'disabled'} ${isSelected ? 'selected' : ''}`;
        btn.innerHTML = `<span>${ch}</span>`;
        
        if (chData && onClick) {
            btn.onclick = onClick;
            
            const chWidth = (ch === 53) ? 4000 : 6000;

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
            
            const base_start = 470000 + (ch - 13) * 6000;
            const base_end = base_start + chWidth;

            if (window.devices) {
                window.devices.forEach((d) => {
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

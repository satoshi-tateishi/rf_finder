/**
 * UI Controller module
 */

function toggleMenu() {
    const menu = document.getElementById('side-menu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

function openAuditLogModal() {
    toggleMenu();
    const modal = document.getElementById('audit-log-modal');
    if (modal) {
        modal.classList.remove('hidden');
        refreshAuditLogs();
    }
}

function closeAuditLogModal() {
    const modal = document.getElementById('audit-log-modal');
    if (modal) modal.classList.add('hidden');
}

/**
 * Backup Manager Functions
 */
function openBackupModal() {
    toggleMenu();
    const modal = document.getElementById('backup-modal');
    if (modal) {
        modal.classList.remove('hidden');
        refreshBackupList();
    }
}

function closeBackupModal() {
    const modal = document.getElementById('backup-modal');
    if (modal) modal.classList.add('hidden');
}

async function refreshBackupList() {
    const list = document.getElementById('backup-list');
    if (!list) return;

    list.innerHTML = '<div class="text-center py-10"><i class="fa-solid fa-spinner fa-spin text-gray-300 fa-2x"></i><p class="text-xs text-gray-400 mt-2">一覧を取得中...</p></div>';

    try {
        const data = await Api.listBackups();
        renderBackupList(data);
    } catch (err) {
        console.error(err);
        showToast('一覧の取得中にエラーが発生しました: ' + err.message, 'error');
        list.innerHTML = '<div class="text-center py-10 text-red-400 text-xs">データの取得に失敗しました</div>';
    }
}

function renderBackupList(backups) {
    const list = document.getElementById('backup-list');
    if (!list) return;

    if (!backups || backups.length === 0) {
        list.innerHTML = '<div class="text-center py-5 text-gray-400 text-xs">バックアップが見つかりません</div>';
        return;
    }

    list.innerHTML = '';
    backups.forEach(backup => {
        const div = document.createElement('div');
        div.className = 'flex items-center justify-between p-2 border-b border-gray-100 last:border-0 hover:bg-gray-50';
        
        const sizeMb = (backup.size / (1024 * 1024)).toFixed(2);
        const dateDisplay = backup.server_modified;

        div.innerHTML = `
            <div class="flex-1 min-w-0">
                <div class="text-[11px] font-bold text-gray-700 truncate">${backup.name}</div>
                <div class="text-[9px] text-gray-400">${dateDisplay} (${sizeMb} MB)</div>
            </div>
            <button onclick="confirmRestore('${backup.path}', '${backup.name}')" class="ml-2 bg-red-50 text-red-600 hover:bg-red-100 px-2 py-1 rounded text-[10px] font-bold transition-colors">
                復元
            </button>
        `;
        list.appendChild(div);
    });
}

async function handleManualBackup() {
    const btn = document.getElementById('manual-backup-btn');
    const originalContent = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 実行中...';
    
    try {
        await Api.runBackup();
        showToast('バックアップが完了しました', 'success');
        // Dropboxの検索インデックスへの反映を少し待ってからリストを更新
        setTimeout(async () => {
            await refreshBackupList();
        }, 1500);
    } catch (err) {
        console.error(err);
        showToast('バックアップ実行中にエラーが発生しました: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalContent;
    }
}

function confirmRestore(path, name) {
    showDecisionModal({
        title: 'データベースの復元',
        message: `バックアップ「${name}」からデータを復元しますか？<br><br><span class="text-red-600 font-bold">警告：現在のすべてのデータが上書きされ、元に戻せません。</span>`,
        okText: '復元する',
        cancelText: 'キャンセル',
        iconClass: 'fa-triangle-exclamation',
        cancelColor: 'red'
    }).then(async (confirmed) => {
        if (!confirmed) return;
        
        showToast('復元処理を開始しました。ブラウザを閉じないでください...', 'info', 10000);
        try {
            await Api.restoreBackup(path);
            showToast('復元が正常に完了しました。画面を再読み込みします。', 'success');
            setTimeout(() => location.reload(), 2000);
        } catch (err) {
            console.error(err);
            showToast('復元の実行に失敗しました: ' + err.message, 'error');
        }
    });
}

async function refreshAuditLogs() {
    const list = document.getElementById('audit-log-list');
    const action = document.getElementById('audit-filter-action').value;
    const description = document.getElementById('audit-search-desc').value;

    if (list) {
        list.innerHTML = '<div class="text-center py-10"><i class="fa-solid fa-spinner fa-spin text-gray-300 fa-2x"></i></div>';
    }

    try {
        const logs = await Api.listAuditLogs({ action, description });
        renderAuditLogs(logs);
    } catch (err) {
        console.error(err);
        showToast('監査ログの取得に失敗しました', 'error');
    }
}

function renderAuditLogs(logs) {
    const list = document.getElementById('audit-log-list');
    if (!list) return;

    if (!logs || logs.length === 0) {
        list.innerHTML = '<div class="text-center py-20 text-gray-400">ログがありません</div>';
        return;
    }

    list.innerHTML = '';
    logs.forEach(log => {
        const div = document.createElement('div');
        div.className = 'p-3 rounded-lg border border-gray-100 shadow-sm bg-white hover:bg-gray-50 transition-all';
        
        let actionColor = 'bg-gray-100 text-gray-600';
        if (log.action === 'LOGIN') actionColor = 'bg-green-100 text-green-700';
        if (log.action === 'LOGIN_FAILED') actionColor = 'bg-red-100 text-red-700';
        if (log.action.includes('EXPORT')) actionColor = 'bg-blue-100 text-blue-700';
        if (log.action === 'EMAIL_SEND') actionColor = 'bg-purple-100 text-purple-700';

        div.innerHTML = `
            <div class="flex justify-between items-start mb-1">
                <span class="text-[10px] font-bold px-2 py-0.5 rounded ${actionColor}">${log.action}</span>
                <span class="text-[10px] text-gray-400">${log.timestamp}</span>
            </div>
            <div class="text-sm font-medium text-gray-800 mb-1">${log.description}</div>
            <div class="flex justify-between text-[10px] text-gray-500">
                <span>ユーザー: ${log.user_display || log.user}</span>
                <span>IP: ${log.ip_address || '---'}</span>
            </div>
        `;
        list.appendChild(div);
    });
}

// デバイス名に基づく色設定
function getDeviceColor(name) {
    if (name.includes('SR2050')) return '#f97316'; // オレンジ (Tailwind orange-500)
    if (name.includes('3732') && name.includes('N')) return '#3b82f6'; // ブルー (Tailwind blue-500)
    if (name.includes('3732') && name.includes('L')) return '#22c55e'; // グリーン (Tailwind green-500)
    return '#94a3b8'; // デフォルト (gray-400)
}

function updateAdjustmentButtonState() {
    const btn = document.getElementById('go-to-adjustment-btn');
    if (!btn) return;

    // 少なくとも1つの施設で、1つ以上のチャンネルが選択されているか確認
    const hasSelection = window.keepList && window.keepList.some(f => f.selectedChannels && f.selectedChannels.length > 0);
    
    if (hasSelection) {
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed', 'bg-gray-400');
        btn.classList.add('bg-blue-600', 'hover:bg-blue-700');
    } else {
        btn.disabled = true;
        btn.classList.add('opacity-50', 'cursor-not-allowed', 'bg-gray-400');
        btn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
    }
}

function updateWsmButtonState(facilityId) {
    const btn = document.getElementById(`wsm-btn-${facilityId}`);
    if (!btn) return;

    const facility = window.keepList.find(f => f.id === facilityId);
    const hasSelection = facility && facility.selectedChannels && facility.selectedChannels.length > 0;

    if (hasSelection) {
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed', 'bg-gray-400');
        btn.classList.add('bg-orange-500', 'hover:bg-orange-600');
    } else {
        btn.disabled = true;
        btn.classList.add('opacity-50', 'cursor-not-allowed', 'bg-gray-400');
        btn.classList.remove('bg-orange-500', 'hover:bg-orange-600');
    }
}

function renderChannelSelection() {
    const container = document.getElementById('facility-channels-container');
    if (!container) return;
    container.innerHTML = '';
    
    window.keepList.forEach(f => {
        const section = UIRenderer.createFacilitySection(f, handleExportWSM);
        container.appendChild(section);
        
        const gridContainer = section.querySelector('.grid-container');
        renderRFGrid(f, gridContainer);
        updateWsmButtonState(f.id);
    });

    updateAdjustmentButtonState();
}

function renderRFGrid(facility, gridElement) {
    if (!gridElement) return;
    gridElement.innerHTML = '';
    
    for (let ch = 13; ch <= 53; ch++) {
        const chData = facility.availableChannels.find(c => c.channel === ch);
        const isSelected = facility.selectedChannels.includes(ch);
        
        const btn = UIRenderer.createChannelButton(ch, chData, isSelected, () => {
            if (facility.selectedChannels.includes(ch)) {
                facility.selectedChannels = facility.selectedChannels.filter(c => c !== ch);
                btn.classList.remove('selected');
            } else {
                facility.selectedChannels.push(ch);
                btn.classList.add('selected');
            }
            updateWsmButtonState(facility.id);
            updateAdjustmentButtonState();
        });
        
        gridElement.appendChild(btn);
    }
}

// Global scope initialization
window.addEventListener('DOMContentLoaded', () => {
    // Legend initialization
    const legend = document.getElementById('device-legend');
    if (legend && typeof window.devices !== 'undefined') {
        window.devices.forEach((d) => {
            const div = document.createElement('div');
            div.className = 'flex items-center gap-1';
            div.innerHTML = `<span class="w-2 h-2 rounded-full" style="background-color: ${getDeviceColor(d.name)}"></span> ${d.name}`;
            legend.appendChild(div);
        });
    }

    // Search input initialization
    const searchInput = document.getElementById('facility-search-input');
    const resultsDiv = document.getElementById('search-results');

    if (searchInput) {
        searchInput.addEventListener('input', async (e) => {
            const q = e.target.value;
            if (q.length < 2) { resultsDiv.classList.add('hidden'); return; }

            try {
                const data = await Api.searchFacilities(q);
                resultsDiv.innerHTML = '';
                if (data.results && data.results.length > 0) {
                    data.results.forEach(f => {
                        const item = document.createElement('div');
                        item.className = 'p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-0';
                        const categoryBadge = f.category ? `<span class="bg-gray-100 text-gray-600 text-[9px] px-1.5 py-0.5 rounded border border-gray-200 whitespace-nowrap">${f.category}</span>` : '';
                        const areaBadge = f.applied_area ? `<span class="bg-blue-50 text-blue-600 text-[9px] px-1.5 py-0.5 rounded border border-blue-100 whitespace-nowrap">${f.applied_area}</span>` : '';
                        const zipDisplay = f.postal_code ? `<span class="mr-1">〒${f.postal_code}</span>` : '';
                        
                        item.innerHTML = `
                            <div class="flex flex-col gap-1">
                                <div class="flex items-center gap-1 flex-wrap">
                                    <span class="font-bold text-sm text-gray-800">${f.name}</span>
                                    ${categoryBadge}
                                    ${areaBadge}
                                </div>
                                <div class="text-[10px] text-gray-400">${zipDisplay}${f.address}</div>
                            </div>
                        `;
                        item.onclick = () => addToKeepList(f);
                        resultsDiv.appendChild(item);
                    });
                    resultsDiv.classList.remove('hidden');
                } else {
                    resultsDiv.classList.add('hidden');
                }
            } catch (err) { console.error(err); }
        });
    }

    // 初期状態のボタン更新
    updateAdjustmentButtonState();
});

/**
 * Handle WSM CSV export for a specific facility
 */
async function handleExportWSM(facilityId) {
    const facility = window.keepList.find(f => f.id === facilityId);
    if (!facility) return;

    if (!facility.selectedChannels || facility.selectedChannels.length === 0) {
        showToast('チャンネルが選択されていません', 'error');
        return;
    }

    try {
        const blob = await Api.exportWSM(facilityId, facility.selectedChannels);
        
        // ファイル名を生成
        const dateStr = new Date().toISOString().split('T')[0].replace(/-/g, '');
        const filename = `wsm_${facility.name}_${dateStr}.csv`;
        
        // ダウンロード実行
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.style.display = 'none';
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }, 100);
        
        showToast('CSVのダウンロードを開始しました', 'success');
    } catch (err) {
        console.error(err);
        showToast('CSVの生成に失敗しました: ' + err.message, 'error');
    }
}

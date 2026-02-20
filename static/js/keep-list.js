/**
 * Keep List Management module
 */
let keepList = [];
let sortable = null;

function initSortable() {
    const el = document.getElementById('keep-list');
    if (sortable) sortable.destroy();
    
    sortable = Sortable.create(el, {
        handle: '.drag-handle',
        animation: 150,
        onEnd: (evt) => {
            const movedItem = keepList.splice(evt.oldIndex, 1)[0];
            keepList.splice(evt.newIndex, 0, movedItem);
            renderKeepList(); // Update numbers
            
            // TVチャンネル選択UIが表示されている場合は、その順番も更新する
            if (!document.getElementById('ch-selection-section').classList.contains('hidden')) {
                renderChannelSelection();
            }
        }
    });
}

async function addToKeepList(f) {
    const resultsDiv = document.getElementById('search-results');
    const searchInput = document.getElementById('facility-search-input');
    
    resultsDiv.classList.add('hidden');
    searchInput.value = '';
    
    // 重複チェック
    if (!keepList.find(item => item.id === f.id)) {
        try {
            const data = await Api.getFacilityDetail(f.id);
            
            keepList.push({ 
                ...f, 
                selectedChannels: [], 
                availableChannels: data.available_channels 
            });
            renderKeepList();
            renderChannelSelection();
            document.getElementById('ch-selection-section').classList.remove('hidden');
        } catch (err) {
            console.error('Error fetching facility details:', err);
        }
    }
    
    document.getElementById('welcome-msg').classList.add('hidden');
    document.getElementById('keep-list-section').classList.remove('hidden');
}

function removeFromKeepList(id) {
    keepList = keepList.filter(f => f.id !== id);
    renderKeepList();
    
    if (keepList.length === 0) {
        document.getElementById('keep-list-section').classList.add('hidden');
        document.getElementById('welcome-msg').classList.remove('hidden');
        document.getElementById('ch-selection-section').classList.add('hidden');
    } else {
        renderChannelSelection();
    }
}

function renderKeepList() {
    const container = document.getElementById('keep-list');
    container.innerHTML = '';
    
    keepList.forEach((f, index) => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100';
        
        const categoryBadge = f.category ? `<span class="bg-gray-100 text-gray-600 text-[9px] px-1.5 py-0.5 rounded border border-gray-200 whitespace-nowrap">${f.category}</span>` : '';
        const areaBadge = f.applied_area ? `<span class="bg-blue-50 text-blue-600 text-[9px] px-1.5 py-0.5 rounded border border-blue-100 whitespace-nowrap">${f.applied_area}</span>` : '';
        const zipDisplay = f.postal_code ? `<span class="mr-1">〒${f.postal_code}</span>` : '';

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
                        <span class="font-bold text-sm text-gray-800">${f.name}</span>
                        ${categoryBadge}
                        ${areaBadge}
                    </div>
                    <div class="text-[10px] text-gray-400">${zipDisplay}${f.address}</div>
                </div>
            </div>
            <button onclick="removeFromKeepList(${f.id})" class="text-gray-300 hover:text-red-500 shrink-0">
                <i class="fa-solid fa-circle-xmark fa-lg"></i>
            </button>
        `;
        container.appendChild(div);
    });
    initSortable();
}

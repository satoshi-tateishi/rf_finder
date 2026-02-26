/**
 * Keep List Management module
 */
window.keepList = [];
let sortable = null;

function initSortable() {
    const el = document.getElementById('keep-list');
    if (sortable) sortable.destroy();
    
    sortable = Sortable.create(el, {
        handle: '.drag-handle',
        animation: 150,
        onEnd: (evt) => {
            const movedItem = window.keepList.splice(evt.oldIndex, 1)[0];
            window.keepList.splice(evt.newIndex, 0, movedItem);
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
    if (!window.keepList.find(item => item.id === f.id)) {
        try {
            const data = await Api.getFacilityDetail(f.id);
            
            window.keepList.push({ 
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
    window.keepList = window.keepList.filter(f => f.id !== id);
    renderKeepList();
    
    if (window.keepList.length === 0) {
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
    
    window.keepList.forEach((f, index) => {
        const item = UIRenderer.createKeepItem(f, index, removeFromKeepList);
        container.appendChild(item);
    });
    initSortable();
}

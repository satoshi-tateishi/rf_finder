/**
 * App State Management module
 * Centralizes the application's reactive data.
 */

const AppState = (function() {
    // 内部的な状態保持
    const _state = {
        currentAdjustmentId: null,
        currentStatus: 'draft',
        keepList: [],
        devices: [],
        currentUser: {
            role: 'guest',
            isAuthenticated: false
        }
    };

    /**
     * 初期データの読み込み (index.html のインラインスクリプトから移行)
     */
    function init(initialData = {}) {
        if (initialData.devices) _state.devices = initialData.devices;
        if (initialData.currentUser) _state.currentUser = initialData.currentUser;
        console.log('[State] Initialized', _state);
    }

    /**
     * 申請データの情報をセット
     */
    function setAdjustment(id, status = 'draft') {
        _state.currentAdjustmentId = id;
        _state.currentStatus = status;
        console.log(`[State] Adjustment updated: id=${id}, status=${status}`);
    }

    /**
     * 施設リストの管理
     */
    const KeepList = {
        get: () => _state.keepList,
        set: (list) => { _state.keepList = list; },
        add: (facility) => { _state.keepList.push(facility); },
        remove: (id) => { _state.keepList = _state.keepList.filter(f => f.id !== id); },
        updateFacilityData: (id, data) => {
            const f = _state.keepList.find(item => item.id === id);
            if (f) {
                if (data.start_date !== undefined) f.start_date = data.start_date;
                if (data.end_date !== undefined) f.end_date = data.end_date;
                if (data.start_time !== undefined) f.start_time = data.start_time;
                if (data.end_time !== undefined) f.end_time = data.end_time;
            }
        },
        clear: () => { _state.keepList = []; },
        find: (id) => _state.keepList.find(f => f.id === id),
        isEmpty: () => _state.keepList.length === 0
    };

    return {
        init,
        setAdjustment,
        KeepList,
        get currentAdjustmentId() { return _state.currentAdjustmentId; },
        get currentStatus() { return _state.currentStatus; },
        get devices() { return _state.devices; },
        get currentUser() { return _state.currentUser; }
    };

})();

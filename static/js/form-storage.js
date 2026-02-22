/**
 * Form State Persistence module
 */
const FormStorage = (function() {
    const STORAGE_KEY = 'rf_finder_form_state';

    function save(data) {
        // 施設の基本情報は重いので除外、選択内容のみ保存
        const state = {
            app_type: data.app_type,
            user: data.user,
            event: data.event,
            mic_counts: data.mic_counts,
            extra_53ch: data.extra_53ch,
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
        console.log('[Storage] State saved');
    }

    function load() {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) : null;
    }

    function clear() {
        localStorage.removeItem(STORAGE_KEY);
    }

    return { save, load, clear };
})();

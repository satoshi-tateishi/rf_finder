/**
 * Form Service module
 * Responsible for collecting and normalizing form data from the UI.
 */

const FormService = (function() {
    // DOM 要素のキャッシュ
    let cache = {};

    /**
     * キャッシュを初期化する
     */
    function initCache() {
        const staticIds = [
            'user_name', 'user_kana', 'user_tel', 'user_email',
            'event_name', 'comment', 'toggle-53ch',
            'mic-analog-rm-10mw', 'mic-analog-em-10mw',
            'mic-digital-rm-10mw', 'mic-digital-rm-20mw', 'mic-digital-rm-50mw',
            'mic-analog-rm-53ch-10mw', 'mic-analog-em-53ch-10mw',
            'mic-digital-rm-53ch-10mw', 'mic-digital-rm-53ch-20mw', 'mic-digital-rm-53ch-50mw',
            'mic-digital-rm-12g-10mw', 'mic-digital-rm-12g-20mw', 'mic-digital-rm-12g-50mw',
            'mic-12g-lmh', 'mic-counts-table-container', 'form-facilities-list'
        ];
        
        cache = {};
        staticIds.forEach(id => {
            cache[id] = document.getElementById(id);
        });
    }

    /**
     * キャッシュが有効（DOMに存在）か確認し、必要なら再構築する
     */
    function ensureCache() {
        if (!cache['user_name'] || !document.body.contains(cache['user_name'])) {
            initCache();
        }
    }

    /**
     * 現在のフォーム入力値を全て収集し、DTO (Data Transfer Object) を生成する
     */
    function collect() {
        ensureCache();

        return {
            id: AppState.currentAdjustmentId,
            status: AppState.currentStatus,
            app_type: getAppType(),
            user: getUser(),
            event: getEvent(),
            facilities: getFacilities(),
            extra_53ch: cache['toggle-53ch']?.innerText ?? '',
            mic_counts: getMicCounts()
        };
    }

    function getAppType() {
        const el = document.querySelector('input[name="app_type"]:checked');
        return el?.value ?? 'new';
    }

    function getUser() {
        return {
            name: cache['user_name']?.value ?? '',
            kana: cache['user_kana']?.value ?? '',
            tel: cache['user_tel']?.value ?? '',
            email: cache['user_email']?.value ?? ''
        };
    }

    function getEvent() {
        return {
            name: cache['event_name']?.value ?? '',
            comment: cache['comment']?.value ?? ''
        };
    }

    function getFacilities() {
        const facilitiesList = cache['form-facilities-list'];
        if (!facilitiesList) return AppState.KeepList.get();

        return AppState.KeepList.get().map((f, index) => {
            const container = facilitiesList.children[index];
            if (!container) return { ...f };
            
            const getVal = (field) => container.querySelector(`[data-field="${field}"]`)?.value ?? '';

            return {
                ...f,
                start_date: getVal('start_date'),
                end_date: getVal('end_date'),
                start_time: getVal('start_time'),
                end_time: getVal('end_time')
            };
        });
    }

    function getMicCounts() {
        return {
            analog_rm: { '10mw': cache['mic-analog-rm-10mw']?.value ?? '' },
            analog_em: { '10mw': cache['mic-analog-em-10mw']?.value ?? '' },
            digital_rm: {
                '10mw': cache['mic-digital-rm-10mw']?.value ?? '',
                '20mw': cache['mic-digital-rm-20mw']?.value ?? '',
                '50mw': cache['mic-digital-rm-50mw']?.value ?? ''
            },
            analog_53ch: {
                rm_10mw: cache['mic-analog-rm-53ch-10mw']?.value ?? '',
                em_10mw: cache['mic-analog-em-53ch-10mw']?.value ?? ''
            },
            digital_53ch: {
                '10mw': cache['mic-digital-rm-53ch-10mw']?.value ?? '',
                '20mw': cache['mic-digital-rm-53ch-20mw']?.value ?? '',
                '50mw': cache['mic-digital-rm-53ch-50mw']?.value ?? ''
            },
            digital_12g: {
                '10mw': cache['mic-digital-rm-12g-10mw']?.value ?? '',
                '20mw': cache['mic-digital-rm-12g-20mw']?.value ?? '',
                '50mw': cache['mic-digital-rm-12g-50mw']?.value ?? ''
            },
            '12g_lmh': cache['mic-12g-lmh']?.value ?? ''
        };
    }

    return {
        collect,
        initCache
    };
})();

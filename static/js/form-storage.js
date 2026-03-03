/**
 * Form State Persistence module
 *
 * sessionStorage を使用してフォーム状態を管理する。
 * - タブ/ブラウザを閉じると自動クリア（間違ったブラウザバックからの復帰が目的）
 * - SESSION_TTL_MS 経過後はロード時に自動クリア（タブを開きっぱなしでセッション期限切れのケース対策）
 * - 保存時と異なるユーザーが検出された場合は自動クリア（同一ブラウザで別ユーザーがログインしたケース対策）
 *
 * ユーザー属性（氏名・ふりがな・Tel・E-mail）の初期値は AppState.currentUser（サーバーレンダリング）
 * から取得する prefillUserInfo() の責務であり、このモジュールは関与しない。
 */
const FormStorage = (function() {
    const STORAGE_KEY = 'rf_finder_form_state';
    // ポータルセッション長の近似値。これより古いデータはロード時に破棄する。
    const SESSION_TTL_MS = 4 * 60 * 60 * 1000; // 4時間

    function _getCurrentUserEmail() {
        if (typeof AppState !== 'undefined' && AppState.currentUser) {
            return AppState.currentUser.email || '';
        }
        return '';
    }

    function save(data) {
        const state = {
            _saved_at: Date.now(),
            _saved_by: _getCurrentUserEmail(),
            id: data.id,
            status: data.status,
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
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }

    function load() {
        const saved = sessionStorage.getItem(STORAGE_KEY);
        if (!saved) return null;

        let state;
        try {
            state = JSON.parse(saved);
        } catch {
            clear();
            return null;
        }

        // セッション有効期限チェック
        if (state._saved_at && (Date.now() - state._saved_at) > SESSION_TTL_MS) {
            clear();
            return null;
        }

        // ユーザー一致チェック（異なるユーザーのデータは使用しない）
        const currentEmail = _getCurrentUserEmail();
        if (currentEmail && state._saved_by && currentEmail !== state._saved_by) {
            clear();
            return null;
        }

        return state;
    }

    function clear() {
        sessionStorage.removeItem(STORAGE_KEY);
    }

    return { save, load, clear };
})();

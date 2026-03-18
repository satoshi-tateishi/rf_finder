// bfcache対策: 戻るボタンで戻った際に古い状態が残らないようリロードする
window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        window.location.reload();
    }
});

// toggleMenu のフォールバック実装（UIController が読み込まれる前に呼ばれた場合の安全弁）
function toggleMenu() {
    const menu = document.getElementById('side-menu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    // Django テンプレートデータを JSON script タグから読み込む
    const configEl = document.getElementById('app-config');
    const config = configEl ? JSON.parse(configEl.textContent) : { devices: [], currentUser: { isAuthenticated: false, role: 'guest', fullName: '', fullKana: '', phone: '', email: '' } };

    // AppState の初期化
    AppState.init(config);

    // UI Controller の初期化
    if (typeof UIController !== 'undefined' && UIController.init) {
        UIController.init();
    }

    // フォーム状態の復元と監視 (リフレッシュ対策)
    if (typeof restoreFormState === 'function') {
        await restoreFormState();
        initChangeWatchers();
    }

    // 初回のバリデーションハイライト
    if (typeof checkAllRequiredFields === 'function') {
        checkAllRequiredFields();
    }
});

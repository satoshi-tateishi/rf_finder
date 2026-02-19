document.addEventListener('DOMContentLoaded', function() {
    const resultList = document.querySelector('#result_list');
    if (!resultList) return;

    const rows = resultList.querySelectorAll('tbody tr');
    rows.forEach(row => {
        // マウスオーバーで行全体がクリック可能であることを示す
        row.style.cursor = 'pointer';
        
        row.addEventListener('click', function(e) {
            // チェックボックスや既存のリンクをクリックした場合は何もしない
            if (e.target.tagName === 'A' || e.target.tagName === 'INPUT' || e.target.closest('a') || e.target.closest('input')) {
                return;
            }

            // チェックボックスからIDを取得して遷移先URLを決定
            const checkbox = row.querySelector('input.action-select');
            if (checkbox && checkbox.value) {
                // 現在のURLパスを利用して詳細画面(change/)へ遷移
                const currentPath = window.location.pathname;
                const targetUrl = `${currentPath}${checkbox.value}/change/`;
                window.location.href = targetUrl;
            }
        });

        // ホバーエフェクト
        row.addEventListener('mouseenter', () => {
            row.style.backgroundColor = 'rgba(0,0,0,0.02)';
        });
        row.addEventListener('mouseleave', () => {
            row.style.backgroundColor = '';
        });
    });
});

// data-href 属性を持つ要素をクリック可能な行として扱う
// Admin カスタムテンプレートの onclick="location.href=..." を CSP 準拠に置き換える
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-href]').forEach(function (el) {
        el.style.cursor = 'pointer';
        el.addEventListener('click', function (e) {
            // リンクや入力要素のクリックは通常通り動作させる
            if (e.target.tagName === 'A' || e.target.tagName === 'INPUT' || e.target.closest('a') || e.target.closest('input')) {
                return;
            }
            window.location.href = el.dataset.href;
        });
    });
});

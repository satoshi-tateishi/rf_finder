// Django Admin のテーマ切り替えよりも前にライトモードを強制する
// このスクリプトは <head> 内で早期に読み込まれることを想定している
document.documentElement.setAttribute('data-theme', 'light');

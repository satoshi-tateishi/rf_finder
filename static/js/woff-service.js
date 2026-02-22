/**
 * LINE WORKS WOFF Service
 */
const WoffService = (function() {
    let _woffId = '';
    let _isInitialized = false;

    function _updateDebugStatus(msg) {
        console.log(`[WOFF Debug] ${msg}`);
        const debugEl = document.getElementById('woff-debug-text');
        if (debugEl) debugEl.innerText = `WOFF: ${msg}`;
    }

    async function init(woffId) {
        _updateDebugStatus('Initializing...');
        if (!woffId) {
            _updateDebugStatus('No Woff ID');
            return;
        }
        
        _woffId = woffId;
        
        try {
            _updateDebugStatus(`Calling woff.init(${_woffId})...`);
            await woff.init({ woffId: _woffId });
            _isInitialized = true;
            _updateDebugStatus('Init Success');
            
            if (woff.isInClient()) {
                _updateDebugStatus('In Client');
                _showWoffBadge();
            } else {
                _updateDebugStatus('External Browser');
            }
        } catch (error) {
            _updateDebugStatus(`Error: ${error.code || 'unknown'}`);
            console.error('[WOFF] Initialization failed:', error);
        }
    }

    function _showWoffBadge() {
        const title = document.querySelector('nav h1');
        if (title && !document.getElementById('woff-badge')) {
            const badge = document.createElement('span');
            badge.id = 'woff-badge';
            badge.className = 'text-[10px] bg-white text-[#00c300] px-1.5 py-0.5 rounded-full font-bold ml-2';
            badge.innerText = 'WOFF';
            title.appendChild(badge);
        }
    }

    function isInClient() {
        return _isInitialized && woff.isInClient();
    }

    async function getProfile() {
        if (!_isInitialized) return null;
        try {
            return await woff.getProfile();
        } catch (error) {
            console.error('[WOFF] Failed to get profile:', error);
            return null;
        }
    }

    /**
     * 現在のトークルームのチャンネルIDを取得する
     */
    async function getChannelId() {
        if (!isInClient()) return null;
        try {
            const result = await woff.getChannelId();
            // デバッグログをバックエンドに送信
            Api.logWoffChannelIdResult(result).catch(e => console.error('[WOFF] Failed to log channel ID result to backend:', e));
            // resultが文字列ならそのまま、オブジェクトならresult.channelIdを返す
            if (typeof result === 'string') {
                return result;
            } else if (result && typeof result.channelId === 'string') {
                return result.channelId;
            }
            return null;
        } catch (error) {
            Api.logWoffChannelIdResult({ error: error.code || 'unknown', message: error.message }).catch(e => console.error('[WOFF] Failed to log channel ID error to backend:', e));
            console.error('[WOFF] Failed to get channel ID:', error);
            return null;
        }
    }

    /**
     * アクセストークンを取得する
     */
    async function getAccessToken() {
        if (!_isInitialized) return null;
        try {
            return await woff.getAccessToken();
        } catch (error) {
            console.error('[WOFF] Failed to get access token:', error);
            return null;
        }
    }

    /**
     * サーバーサイド経由で詳細なプロフィールを取得する
     */
    async function getDetailedProfile() {
        if (!_isInitialized) return null;
        try {
            const profile = await woff.getProfile();
            const accessToken = await woff.getAccessToken();
            if (profile && accessToken) {
                return await Api.getWoffDetailedProfile(profile.userId, accessToken);
            }
            return null;
        } catch (error) {
            console.error('[WOFF] Failed to get detailed profile:', error);
            return null;
        }
    }

    async function sendMessage(text) {
        if (!isInClient()) return { success: false, error: 'Not in client' };
        try {
            await woff.sendMessage({ content: text });
            return { success: true };
        } catch (error) {
            console.error('[WOFF] Failed to send message:', error);
            return { success: false, error: error };
        }
    }

    async function sendFlexMessage(flexData) {
        if (!isInClient()) return { success: false, error: 'Not in client' };
        try {
            // flexData が type: "flex" を持っていない場合はラップする
            const payload = flexData.type === 'flex' ? flexData : {
                type: 'flex',
                altText: 'RF Finder Notification',
                contents: flexData
            };
            await woff.sendFlexMessage({ flex: payload });
            return { success: true };
        } catch (error) {
            console.error('[WOFF] Failed to send flex message:', error);
            return { success: false, error: error };
        }
    }

    async function _sendTestMessageToBackend(messageType) {
        if (!isInClient()) {
            alert('WOFFアプリ内でのみ送信可能です');
            return;
        }

        const confirmed = confirm(`テスト${messageType}メッセージを送信しますか？`);
        if (!confirmed) return;

        const channelId = await getChannelId();
        if (!channelId) {
            alert('チャネルIDが取得できませんでした。トークルーム内で開いていますか？');
            return;
        }

        try {
            let result;
            if (messageType === 'text') {
                result = await Api.sendTestTextMessage(channelId, "これはテストメッセージです。");
            } else if (messageType === 'file') {
                // PDF 生成はサーバーサイドで行う
                result = await Api.sendTestPdfMessage(channelId);
            } else {
                alert('不明なメッセージタイプです。');
                return;
            }
            
            if (result && result.message) { // result.successではなくresult.messageの存在で成功を判断
                alert(`テスト${messageType}メッセージの送信に成功しました！`);
                console.log(`[WOFF] Test ${messageType} Message sent:`, result);
            } else {
                const error = result.error || {};
                const errorMsg = `送信に失敗しました。\nCode: ${error.code || 'unknown'}\nMessage: ${error.message || 'No details'}`;
                alert(errorMsg);
                console.error(`[WOFF] Test ${messageType} Message send error details:`, error);
            }
        } catch (e) {
            alert(`テスト${messageType}メッセージの送信中にエラーが発生しました。\n${e.message}`);
            console.error(`[WOFF] Error sending test ${messageType} message:`, e);
        }
    }

    // グローバルスコープに公開するための関数
    window.testSendMessage = async () => _sendTestMessageToBackend('text');
    window.testSendFile = async () => _sendTestMessageToBackend('file');

    return {
        init,
        isInClient,
        getProfile,
        getChannelId,
        getAccessToken,
        getDetailedProfile,
        sendMessage,
        sendFlexMessage,
    };
})();

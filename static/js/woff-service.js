/**
 * LINE WORKS WOFF Service
 */
const WoffService = (function() {
    let _woffId = '';
    let _isInitialized = false;

    function _updateDebugStatus(msg) {
        console.log(`[WOFF Debug] ${msg}`);
        const debugEl = document.getElementById('woff-debug-status');
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

    async function sendMessage(text) {
        if (!isInClient()) return false;
        try {
            await woff.sendMessage({ content: text });
            return true;
        } catch (error) {
            console.error('[WOFF] Failed to send message:', error);
            return false;
        }
    }

    return {
        init,
        isInClient,
        getProfile,
        sendMessage
    };
})();

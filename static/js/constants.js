/**
 * Application Constants
 */

const RADIO_SPEC = {
    // チャンネル計算のベース周波数 (kHz)
    BASE_FREQUENCY: 470000,
    // 開始チャンネル
    CHANNEL_START: 13,
    // 終了チャンネル
    CHANNEL_END: 53,
    // 標準チャンネル幅 (kHz)
    DEFAULT_WIDTH: 6000,
    // 特殊なチャンネル幅 (kHz)
    SPECIAL_WIDTHS: {
        53: 4000
    },
    // ガードバンド幅 (kHz)
    GUARD_BAND_WIDTH: 1000,

    /**
     * 指定されたチャンネルの開始周波数を逐次加算で計算する (制度変更耐性)
     * @param {number} ch 
     * @returns {number} frequency (kHz)
     */
    calculateChannelBase: function(ch) {
        let freq = this.BASE_FREQUENCY;
        for (let c = this.CHANNEL_START; c < ch; c++) {
            freq += this.SPECIAL_WIDTHS[c] ?? this.DEFAULT_WIDTH;
        }
        return freq;
    }
};

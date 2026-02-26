/**
 * Validation Service module
 * Responsible for business logic validation of collected data.
 */

const ValidationService = (function() {
    
    /**
     * 送信データを検証する
     * @param {Object} data 
     * @returns {Array} errors [{ field, message }]
     */
    function validate(data) {
        const errors = [];

        // 現地使用者
        if (!data.user.name?.trim()) errors.push({ field: 'user_name', message: '氏名は必須です' });
        if (!data.user.kana?.trim()) errors.push({ field: 'user_kana', message: 'ふりがなは必須です' });
        if (!data.user.tel?.trim()) errors.push({ field: 'user_tel', message: '電話番号は必須です' });
        
        const email = data.user.email?.trim();
        if (!email) {
            errors.push({ field: 'user_email', message: 'メールアドレスは必須です' });
        } else {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                errors.push({ field: 'user_email', message: 'メールアドレスの形式が正しくありません' });
            }
        }
        
        // 催事
        if (!data.event.name?.trim()) errors.push({ field: 'event_name', message: '催事名は必須です' });

        // 施設
        if (!data.facilities || data.facilities.length === 0) {
            errors.push({ field: 'facilities', message: '施設が選択されていません' });
        } else {
            data.facilities.forEach((f, i) => {
                if (!f.start_date || !f.end_date) {
                    errors.push({ 
                        field: `facility_${i}`, 
                        message: `施設「${f.name}」の使用日程を正しく入力してください` 
                    });
                } else if (new Date(f.start_date) > new Date(f.end_date)) {
                    errors.push({
                        field: `facility_${i}`,
                        message: `施設「${f.name}」の使用開始日は終了日以前に設定してください`
                    });
                } else if (f.start_date === f.end_date && f.start_time >= f.end_time) {
                    errors.push({
                        field: `facility_${i}`,
                        message: `施設「${f.name}」の使用開始時間は終了時間より前に設定してください`
                    });
                }
            });
        }

        // 使用マイク数 (少なくとも1つ入力されているか)
        if (!hasAtLeastOneMicCount(data.mic_counts)) {
            errors.push({ field: 'mic_counts', message: '使用マイク数を少なくとも1つ入力してください' });
        }

        return errors;
    }

    /**
     * マイク数が1つ以上入力されているかチェック
     */
    function hasAtLeastOneMicCount(mc) {
        for (const category in mc) {
            const val = mc[category];
            if (typeof val === 'string') {
                const n = parseInt(val, 10);
                if (/^\d+$/.test(val.trim()) && n > 0) return true;
            } else if (typeof val === 'object') {
                for (const sub in val) {
                    const subVal = val[sub];
                    const n = parseInt(subVal, 10);
                    if (/^\d+$/.test(subVal.trim()) && n > 0) return true;
                }
            }
        }
        return false;
    }

    /**
     * 運用調整フォームへ進める状態か確認する
     * (全ての施設でチャンネルが選択されている必要がある)
     */
    function canProceedToAdjustment(keepList) {
        if (!keepList || keepList.length === 0) return false;
        return keepList.every(f => f.selectedChannels && f.selectedChannels.length > 0);
    }

    return {
        validate,
        canProceedToAdjustment
    };
})();

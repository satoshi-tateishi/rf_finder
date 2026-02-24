/**
 * API communication module
 */
const Api = {
    async _handleResponse(res) {
        const json = await res.json();
        if (json.status === 'success') {
            return json.data;
        } else {
            // Handle structured validation errors if present
            if (json.errors) {
                const errorDetails = Object.entries(json.errors)
                    .map(([field, msgs]) => `${field}: ${msgs.join(', ')}`)
                    .join('\n');
                throw new Error(`${json.message}\n${errorDetails}`);
            }
            throw new Error(json.message || 'API Error');
        }
    },

    async _handleBlobOrError(res) {
        if (res.ok) {
            return await res.blob();
        } else {
            // Even if it's a blob-returning endpoint, errors are JSON
            const json = await res.json();
            if (json.errors) {
                const errorDetails = Object.entries(json.errors)
                    .map(([field, msgs]) => `${field}: ${msgs.join(', ')}`)
                    .join('\n');
                throw new Error(`${json.message}\n${errorDetails}`);
            }
            throw new Error(json.message || 'API Error');
        }
    },

    async searchFacilities(q) {
        const res = await fetch(`/api/facilities/search/?q=${encodeURIComponent(q)}`);
        return await this._handleResponse(res);
    },

    async getFacilityDetail(id) {
        const res = await fetch(`/api/facilities/${id}/`);
        return await this._handleResponse(res);
    },

    async downloadExcel(data) {
        const res = await fetch('/api/adjustments/preview-excel/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await this._handleBlobOrError(res);
    },

    async previewPDF(data) {
        const res = await fetch('/api/adjustments/preview-pdf/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await this._handleBlobOrError(res);
    },

    async sendEmail(data) {
        const res = await fetch('/api/adjustments/send-email/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await this._handleResponse(res);
    },

    async exportWSM(facilityId, selectedChannels) {
        const res = await fetch('/api/adjustments/export-wsm/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                facility_id: facilityId,
                selected_channels: selectedChannels
            })
        });
        return await this._handleBlobOrError(res);
    },

    async saveAdjustment(data) {
        console.log('[Api] saveAdjustment calling POST /api/adjustments/save/');
        const res = await fetch('/api/adjustments/save/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await this._handleResponse(res);
    },

    async listAdjustments(params = {}) {
        const query = new URLSearchParams(params).toString();
        const res = await fetch(`/api/adjustments/list/?${query}`);
        return await this._handleResponse(res);
    },

    async getAdjustment(id) {
        const res = await fetch(`/api/adjustments/${id}/`);
        return await this._handleResponse(res);
    },

    async listAuditLogs(params = {}) {
        const query = new URLSearchParams(params).toString();
        const res = await fetch(`/auth/audit-logs/?${query}`);
        return await this._handleResponse(res);
    },

    async getMyProfile() {
        const res = await fetch('/auth/me/');
        return await this._handleResponse(res);
    },

    /**
     * Utility: Format channel numbers (e.g. [13, 14, 15, 20] -> "13-15, 20")
     */
    formatChannels(channels) {
        if (!channels || channels.length === 0) return "";
        const sorted = [...new Set(channels)].map(Number).sort((a, b) => a - b);
        const result = [];
        
        let i = 0;
        while (i < sorted.length) {
            let start = sorted[i];
            let end = start;
            
            while (i + 1 < sorted.length && sorted[i + 1] === end + 1) {
                end = sorted[i + 1];
                i++;
            }
            
            if (end - start >= 2) {
                result.push(`${start}-${end}`);
            } else if (end - start === 1) {
                result.push(start.toString());
                result.push(end.toString());
            } else {
                result.push(start.toString());
            }
            i++;
        }
        return result.join(", ");
    }
};

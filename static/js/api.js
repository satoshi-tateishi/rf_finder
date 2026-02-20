/**
 * API communication module
 */
const Api = {
    async _handleResponse(res) {
        const json = await res.json();
        if (json.status === 'success') {
            return json.data;
        } else {
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
        // Returns raw response for blob handling
        return await fetch('/api/adjustments/preview-excel/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    },

    async previewPDF(data) {
        // Returns raw response for blob handling
        return await fetch('/api/adjustments/preview-pdf/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    },

    async sendEmail(data) {
        const res = await fetch('/api/adjustments/send-email/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await this._handleResponse(res);
    }
};

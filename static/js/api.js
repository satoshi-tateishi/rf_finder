/**
 * API communication module
 */
const Api = {
    async searchFacilities(q) {
        const res = await fetch(`/api/facilities/search/?q=${encodeURIComponent(q)}`);
        return await res.json();
    },

    async getFacilityDetail(id) {
        const res = await fetch(`/api/facilities/${id}/`);
        return await res.json();
    },

    async downloadExcel(data) {
        return await fetch('/api/adjustments/preview-excel/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    },

    async previewPDF(data) {
        return await fetch('/api/adjustments/preview-pdf/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    },

    async sendEmail(data) {
        const response = await fetch('/api/adjustments/send-email/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await response.json();
    }
};

import apiClient from './client';
export const mailApi = {
    getMailboxes: () => apiClient.get('/mailboxes'),
    getFolders: (address) => apiClient.get(`/mailboxes/${address}/folders`),
    createFolder: (address, name, color) => apiClient.post(`/mailboxes/${address}/folders`, { name, color }),
    deleteFolder: (address, id) => apiClient.delete(`/mailboxes/${address}/folders/${id}`),
    emptyFolder: (address, id) => apiClient.delete(`/mailboxes/${address}/folders/${id}/empty`),
    renameFolder: (address, id, name, color) => apiClient.patch(`/mailboxes/${address}/folders/${id}`, { name, color }),
    getMessages: (address, params) => apiClient.get(`/mailboxes/${address}/messages`, { params }),
    getMessage: (address, id) => apiClient.get(`/mailboxes/${address}/messages/${id}`),
    updateMessage: (address, id, data) => apiClient.patch(`/mailboxes/${address}/messages/${id}`, data),
    deleteMessage: (address, id) => apiClient.delete(`/mailboxes/${address}/messages/${id}`),
    moveMessages: (address, data) => apiClient.post(`/mailboxes/${address}/messages/move`, data),
    markMessages: (address, data) => apiClient.post(`/mailboxes/${address}/messages/mark`, data),
    sendMessage: (address, data) => apiClient.post(`/mailboxes/${address}/send`, data),
    searchMessages: (address, params) => apiClient.get(`/mailboxes/${address}/search`, { params }),
    getMailboxStatus: () => apiClient.get('/mailboxes/status'),
    getAttachmentUrl: (id) => `/api/v1/attachments/${id}/download`,
    downloadAttachment: (id) => apiClient.get(`/attachments/${id}/download`, { responseType: 'blob' }).then(r => r.data),
    createDraft: (address, data) => apiClient.post(`/mailboxes/${address}/drafts`, data),
    updateDraft: (address, id, data) => apiClient.put(`/mailboxes/${address}/drafts/${id}`, data),
};
//# sourceMappingURL=mail.js.map
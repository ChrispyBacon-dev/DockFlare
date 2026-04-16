import apiClient from './client'

export const mailApi = {
  getMailboxes: () => apiClient.get('/mailboxes'),
  getFolders: (address: string) => apiClient.get(`/mailboxes/${address}/folders`),
  createFolder: (address: string, name: string, color?: string) =>
    apiClient.post(`/mailboxes/${address}/folders`, { name, color }),
  deleteFolder: (address: string, id: number) =>
    apiClient.delete(`/mailboxes/${address}/folders/${id}`),
  emptyFolder: (address: string, id: number) =>
    apiClient.delete(`/mailboxes/${address}/folders/${id}/empty`),
  renameFolder: (address: string, id: number, name: string, color?: string) =>
    apiClient.patch(`/mailboxes/${address}/folders/${id}`, { name, color }),
  getMessages: (address: string, params: any) => apiClient.get(`/mailboxes/${address}/messages`, { params }),
  getMessage: (address: string, id: string) => apiClient.get(`/mailboxes/${address}/messages/${id}`),
  updateMessage: (address: string, id: string, data: any) => apiClient.patch(`/mailboxes/${address}/messages/${id}`, data),
  deleteMessage: (address: string, id: string) => apiClient.delete(`/mailboxes/${address}/messages/${id}`),
  moveMessages: (address: string, data: any) => apiClient.post(`/mailboxes/${address}/messages/move`, data),
  markMessages: (address: string, data: any) => apiClient.post(`/mailboxes/${address}/messages/mark`, data),
  sendMessage: (address: string, data: FormData | Record<string, any>) =>
    apiClient.post(`/mailboxes/${address}/send`, data),
  searchMessages: (address: string, params: any) => apiClient.get(`/mailboxes/${address}/search`, { params }),
  getMailboxStatus: () => apiClient.get('/mailboxes/status'),
  getMailboxPreferences: (address: string) => apiClient.get(`/mailboxes/${address}/preferences`),
  updateMailboxPreferences: (address: string, data: Record<string, any>) =>
    apiClient.patch(`/mailboxes/${address}/preferences`, data),
  getAttachmentUrl: (id: string) => `/api/v1/attachments/${id}/download`,
  downloadAttachment: (id: number | string) =>
    apiClient.get(`/attachments/${id}/download`, { responseType: 'blob' }).then(r => r.data as Blob),
  createDraft: (address: string, data: Record<string, any>) =>
    apiClient.post(`/mailboxes/${address}/drafts`, data),
  updateDraft: (address: string, id: number, data: Record<string, any>) =>
    apiClient.put(`/mailboxes/${address}/drafts/${id}`, data),
  getAutoResponder: (address: string) =>
    apiClient.get(`/mailboxes/${address}/auto-responder`),
  setAutoResponder: (address: string, data: Record<string, any>) =>
    apiClient.post(`/mailboxes/${address}/auto-responder`, data),
  deleteAutoResponder: (address: string) =>
    apiClient.delete(`/mailboxes/${address}/auto-responder`),
}

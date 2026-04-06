import apiClient from './client'

export const mailApi = {
  getMailboxes: () => apiClient.get('/mailboxes'),
  getFolders: (address: string) => apiClient.get(`/mailboxes/${address}/folders`),
  getMessages: (address: string, params: any) => apiClient.get(`/mailboxes/${address}/messages`, { params }),
  getMessage: (address: string, id: string) => apiClient.get(`/mailboxes/${address}/messages/${id}`),
  updateMessage: (address: string, id: string, data: any) => apiClient.patch(`/mailboxes/${address}/messages/${id}`, data),
  deleteMessage: (address: string, id: string) => apiClient.delete(`/mailboxes/${address}/messages/${id}`),
  moveMessages: (address: string, data: any) => apiClient.post(`/mailboxes/${address}/messages/move`, data),
  markMessages: (address: string, data: any) => apiClient.post(`/mailboxes/${address}/messages/mark`, data),
  sendMessage: (address: string, data: any) => apiClient.post(`/mailboxes/${address}/send`, data),
  searchMessages: (address: string, params: any) => apiClient.get(`/mailboxes/${address}/search`, { params }),
  getAttachmentUrl: (id: string) => `/api/v1/attachments/${id}/download`,
  downloadAttachment: (id: number | string) =>
    apiClient.get(`/attachments/${id}/download`, { responseType: 'blob' }).then(r => r.data as Blob),
}

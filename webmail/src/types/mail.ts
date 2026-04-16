export interface Mailbox {
  address: string
  display_name: string
}

export interface Folder {
  id: number
  name: string
  system_folder: boolean
  color: string | null
  unread_count: number
  total_count: number
}

export interface Attachment {
  id: string
  filename: string
  content_type: string
  size: number
}

export interface Message {
  id: string
  mailbox_address: string
  folder_id: number
  message_id: string | null
  from_name: string | null
  from_address: string
  to_addresses: string
  cc_addresses: string
  subject: string | null
  text_body: string | null
  html_body: string | null
  received_at: string | null
  sent_at: string | null
  is_read: 0 | 1
  is_starred: 0 | 1
  is_draft: boolean
  attachments?: Attachment[]
}

export interface Toast {
  message: string
  type: 'error' | 'success' | 'info'
}

export interface ComposeDefaults {
  to?: string
  subject?: string
  body?: string
  quotedHtml?: string
  draftId?: number
}

export interface PrintTemplatePage {
  size?: 'A4' | 'A3'
  orientation?: 'portrait' | 'landscape'
  marginMm?: number
}

export interface PrintTemplateAsset {
  url?: string
  widthMm?: number
  align?: 'left' | 'right' | 'center'
  opacity?: number
}

export interface PrintFieldItem {
  label?: string
  fieldKey?: string
  subFieldKey?: string
  format?: string
  value?: string
}

export interface PrintDetailColumn {
  key: string
  header: string
  width?: string
  align?: 'left' | 'right' | 'center'
  format?: string
}

export interface PrintTemplateBlock {
  type: string
  content?: string
  align?: string
  items?: PrintFieldItem[]
  fieldKey?: string
  title?: string
  currencyLabel?: string
  currencyFieldKey?: string
  columns?: PrintDetailColumn[]
  showTotal?: boolean
  totalLabel?: string
  totalFieldKey?: string
  showSeal?: boolean
  lines?: string[]
  showDivider?: boolean
  left?: PrintFieldItem[]
  right?: PrintFieldItem[]
}

export interface PrintTemplateSchema {
  version?: number
  page?: PrintTemplatePage
  layout?: string
  assets?: {
    logo?: PrintTemplateAsset
    seal?: PrintTemplateAsset
  }
  regions?: Record<string, { blocks?: string[] }>
  blocks?: Record<string, PrintTemplateBlock>
  styles?: {
    fontFamily?: string
    baseFontSizePt?: number
    tableBorderColor?: string
  }
  emailTemplates?: Record<
    string,
    {
      subject?: string
      greeting?: string
      body?: string
    }
  >
}

export interface PrintTemplateRow {
  id: number
  code: string
  name: string
  description?: string
  category?: string
  is_builtin?: boolean
  is_active?: boolean
  schema?: PrintTemplateSchema
  created_at?: string | null
  updated_at?: string | null
}

export const DEFAULT_PRINT_TEMPLATE_SCHEMA = (): PrintTemplateSchema => ({
  version: 1,
  page: { size: 'A4', orientation: 'portrait', marginMm: 10 },
  layout: 'debit_note_v1',
  assets: {
    logo: { url: '', widthMm: 42, align: 'left' },
    seal: { url: '', widthMm: 36, opacity: 0.95 },
  },
  regions: {},
  blocks: {},
  styles: {
    fontFamily: 'Arial, Helvetica, "Liberation Sans", sans-serif',
    baseFontSizePt: 10,
    tableBorderColor: '#333333',
  },
  emailTemplates: {
    en: {
      subject: 'Debit Note {{debit_note_no}}',
      greeting: 'Dear {{recipient_name}},',
      body: 'Please find the Debit Note {{debit_note_no}}.',
    },
  },
})

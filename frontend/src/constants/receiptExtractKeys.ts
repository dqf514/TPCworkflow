/** 智能票据标准提取字段（与后端 receipt_extract_keys 对齐） */
export const RECEIPT_EXTRACT_KEYS = [
  { key: 'total_amount', label: '总金额', desc: '应付/报销总金额' },
  { key: 'amount_before_tax', label: '不含税金额', desc: '税前金额' },
  { key: 'tax_amount', label: '税额', desc: '增值税或其他税额' },
  { key: 'currency', label: '币种', desc: 'ISO 4217 货币代码' },
  { key: 'transaction_date', label: '交易日期', desc: '开票或消费日期' },
  { key: 'transaction_time', label: '交易时间', desc: 'HH:MM 格式' },
  { key: 'expense_category', label: '费用类别', desc: '匹配下拉选项' },
  { key: 'merchant_name', label: '商户名称', desc: '销售方/商户/店铺' },
  { key: 'document_number', label: '票号/订单号', desc: '发票号码或订单编号' },
  { key: 'document_type', label: '票种', desc: '如餐饮小票、Receipt' },
  { key: 'summary', label: '摘要', desc: '消费摘要或事由' },
  { key: 'payment_method', label: '支付方式', desc: '微信、支付宝、信用卡等' },
  { key: 'buyer_name', label: '购买方', desc: '购买方名称' },
  { key: 'merchant_tax_id', label: '税号', desc: '销售方纳税人识别号' },
  { key: 'country_region', label: '国家/地区', desc: '如 CN、US' },
] as const

export type ReceiptExtractKey = (typeof RECEIPT_EXTRACT_KEYS)[number]['key']

export interface SmartReceiptMapping {
  extractKey: string
  targetKey: string
  targetScope: 'main' | 'detail'
}

/** 传给后端的表单字段提示，供 LLM 按 label 智能对号入座 */
export interface FormFieldHint {
  key: string
  label: string
  type: string
  scope: 'main' | 'detail'
  options?: { label: string; value: string; name?: string; code?: string }[]
}

export interface SmartReceiptRecognitionConfig {
  enabled?: boolean
  scene?: 'expense' | 'payment' | 'general'
  providerId?: number | null
  fillMode?: 'main_fields' | 'detail_row' | 'both'
  targetDetailKey?: string
  mappings?: SmartReceiptMapping[]
  categoryFieldKey?: string
  autoFill?: boolean
  attachToFieldKey?: string
  attachToScope?: 'main' | 'detail'
}

export interface ReceiptExtracted {
  document_type?: string
  document_number?: string
  transaction_date?: string
  merchant_name?: string
  currency?: string
  total_amount?: number
  expense_category?: string
  summary?: string
  confidence?: number
  warnings?: string[]
  [key: string]: unknown
}

export interface ReceiptFillSuggestions {
  main?: Record<string, unknown>
  detail_row?: Record<string, unknown>
}

export interface ReceiptDuplicateInfo {
  used: boolean
  reason?: 'document_number' | 'file_path'
  document_number?: string
  file_path?: string
  instance_id?: number
  display_no?: string
  source_field?: string
  merchant_name?: string
  transaction_date?: string
  total_amount?: number
}

export interface ReceiptRecognitionResult {
  extracted: ReceiptExtracted
  fill_suggestions: ReceiptFillSuggestions
  warnings?: string[]
  provider_used?: string
  recognition_mode?: string
  duplicate?: ReceiptDuplicateInfo
}

export function labelForExtractKey(key: string): string {
  return RECEIPT_EXTRACT_KEYS.find((k) => k.key === key)?.label || key
}

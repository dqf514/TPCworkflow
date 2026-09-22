# -*- coding: utf-8 -*-
"""智能票据识别 — 标准提取字段定义。"""

RECEIPT_EXTRACT_KEYS = [
    {'key': 'total_amount', 'label': '总金额', 'desc': '应付/报销总金额'},
    {'key': 'amount_before_tax', 'label': '不含税金额', 'desc': '税前金额'},
    {'key': 'tax_amount', 'label': '税额', 'desc': '增值税或其他税额'},
    {'key': 'currency', 'label': '币种', 'desc': 'ISO 4217 货币代码，如 CNY、USD'},
    {'key': 'transaction_date', 'label': '交易日期', 'desc': '开票或消费日期'},
    {'key': 'transaction_time', 'label': '交易时间', 'desc': 'HH:MM 格式'},
    {'key': 'expense_category', 'label': '费用类别', 'desc': '匹配下拉选项的消费类别'},
    {'key': 'merchant_name', 'label': '商户名称', 'desc': '销售方/商户/店铺'},
    {'key': 'document_number', 'label': '票号/订单号', 'desc': '发票号码或订单编号'},
    {'key': 'document_type', 'label': '票种', 'desc': '如餐饮小票、增值税发票、Receipt'},
    {'key': 'summary', 'label': '摘要', 'desc': '消费摘要或事由说明'},
    {'key': 'payment_method', 'label': '支付方式', 'desc': '如微信、支付宝、现金、信用卡'},
    {'key': 'buyer_name', 'label': '购买方', 'desc': '购买方名称'},
    {'key': 'merchant_tax_id', 'label': '税号', 'desc': '销售方纳税人识别号'},
    {'key': 'country_region', 'label': '国家/地区', 'desc': 'ISO 3166-1 alpha-2，如 CN、US'},
]

RECEIPT_JSON_SCHEMA_HINT = """
{
  "document_type": "票种中文描述",
  "document_type_en": "English type if applicable",
  "document_number": "票号或订单号或 null",
  "transaction_date": "YYYY-MM-DD 或 null",
  "transaction_time": "HH:MM 或 null",
  "merchant_name": "商户名称或 null",
  "merchant_address": "地址或 null",
  "merchant_tax_id": "税号或 null",
  "buyer_name": "购买方或 null",
  "currency": "CNY",
  "amount_before_tax": 0.00,
  "tax_amount": 0.00,
  "total_amount": 0.00,
  "payment_method": "支付方式或 null",
  "expense_category": "费用类别建议或 null",
  "line_items": [{"name": "项目", "quantity": 1, "unit_price": 0, "amount": 0}],
  "summary": "摘要或 null",
  "language": "zh",
  "country_region": "CN",
  "confidence": 0.0,
  "field_confidence": {"total_amount": 0.0, "expense_category": 0.0},
  "warnings": [],
  "smart_fill": {"表单字段key": "按字段 label 语义填入的值，无法确认则省略"}
}
"""

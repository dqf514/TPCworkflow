# -*- coding: utf-8 -*-
"""已通过申请中的票据/发票使用登记，用于防重复报销。"""
from datetime import datetime

from app.extensions import db


class ReceiptUsageRecord(db.Model):
    """同一公司内票号或附件文件不可在已通过申请中重复使用。"""

    __tablename__ = 'receipt_usage_records'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    instance_id = db.Column(
        db.Integer,
        db.ForeignKey('workflow_instances.id'),
        nullable=False,
        index=True,
    )
    display_no = db.Column(db.String(32))
    document_number = db.Column(db.String(128), index=True)
    file_path = db.Column(db.String(512), index=True)
    merchant_name = db.Column(db.String(256))
    transaction_date = db.Column(db.String(32))
    total_amount = db.Column(db.Numeric(18, 2))
    source_field = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())

    __table_args__ = (
        db.Index('ix_receipt_usage_company_doc', 'company_id', 'document_number'),
        db.Index('ix_receipt_usage_company_file', 'company_id', 'file_path'),
    )

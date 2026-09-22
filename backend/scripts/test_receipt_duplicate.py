# -*- coding: utf-8 -*-
"""票据防重复校验单元测试。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import Company, ReceiptUsageRecord, User, WorkflowDefinition, WorkflowInstance
from app.services.receipt_duplicate_service import (
    extract_receipt_entries,
    find_duplicate_usage,
    normalize_document_number,
    sync_receipt_usage_for_instance,
    validate_form_receipt_duplicates,
)


def test_normalize_and_extract():
    assert normalize_document_number('  Ab-12.34 ') == 'AB1234'
    schema = {
        'sections': [{
            'fields': [{
                'key': 'expense_items',
                'type': 'detail',
                'props': {
                    'columns': [
                        {'key': 'voucher_no', 'type': 'input', 'label': '票号'},
                        {'key': 'invoice_file', 'type': 'attachment', 'label': '附件'},
                    ],
                },
            }],
        }],
    }
    form = {
        'expense_items': [
            {'voucher_no': 'INV-2024-001', 'invoice_file': [{'path': 'uploads/a.pdf', 'name': 'a.pdf'}]},
        ],
    }
    entries = extract_receipt_entries(schema, form)
    assert any(e.get('document_number') == 'INV2024001' for e in entries)
    assert any(e.get('file_path') == 'uploads/a.pdf' for e in entries)


def test_duplicate_detection():
    app = create_app()
    with app.app_context():
        db.create_all()
        company = Company.query.first()
        user = User.query.first()
        if not company or not user:
            print('skip: no seed company/user')
            return
        wf = WorkflowDefinition.query.first()
        if not wf:
            print('skip: no workflow definition')
            return

        inst = WorkflowInstance(
            definition_id=wf.id,
            initiator_id=user.id,
            company_id=company.id,
            status='approved',
            variables='{"form":{"expense_items":[{"voucher_no":"DUP123456"}]}}',
            display_no='TEST-DUP-001',
        )
        db.session.add(inst)
        db.session.flush()
        sync_receipt_usage_for_instance(inst)
        db.session.commit()

        hit = find_duplicate_usage(company.id, document_number='DUP123456')
        assert hit and hit.get('used'), hit

        errs = validate_form_receipt_duplicates(
            {
                'sections': [{
                    'fields': [{
                        'key': 'expense_items',
                        'type': 'detail',
                        'props': {'columns': [{'key': 'voucher_no', 'type': 'input', 'label': '票号'}]},
                    }],
                }],
            },
            {'expense_items': [{'voucher_no': 'DUP123456'}]},
            company.id,
        )
        assert errs, errs

        ReceiptUsageRecord.query.filter_by(instance_id=inst.id).delete()
        db.session.delete(inst)
        db.session.commit()
        print('receipt duplicate tests passed')


if __name__ == '__main__':
    test_normalize_and_extract()
    test_duplicate_detection()

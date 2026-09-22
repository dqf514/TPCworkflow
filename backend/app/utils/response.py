# -*- coding: utf-8 -*-
from flask import jsonify


def ok(data=None, message='操作成功', status=200):
    body = {'ok': True, 'data': data, 'message': message}
    return jsonify(body), status


def fail(message='操作失败', code='error', status=400, data=None):
    body = {'ok': False, 'message': message, 'code': code, 'data': data}
    return jsonify(body), status

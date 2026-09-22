# -*- coding: utf-8 -*-
import os

from app import create_app
from app.startup import run_startup_maintenance

app = create_app()
run_startup_maintenance(app)


if __name__ == '__main__':
    app.run(
        host=os.environ.get('HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', 5320)),
        debug=os.environ.get('FLASK_DEBUG', '1') == '1',
    )

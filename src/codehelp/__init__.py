# SPDX-FileCopyrightText: 2023 Mark Liffiton <liffiton@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-only

from pathlib import Path
from typing import Any

from flask.app import Flask

from gened import base

from . import admin, context_config, helper, tutor

import os
from dotenv import find_dotenv, load_dotenv
from . import api
from .commands import register_commands

def create_app(test_config: dict[str, Any] | None = None, instance_path: Path | None = None) -> Flask:
    app_config = dict(
        APPLICATION_TITLE='CodeHelp',
        DARTMOUTH_API_KEY=os.environ.get('DARTMOUTH_API_KEY'),
        MISTRAL_API_KEY=os.environ.get('MISTRAL_API_KEY'),
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        APPLICATION_AUTHOR='Mark Liffiton, Modified by Rana Moeez Hassan',
        SYSTEM_MODEL=os.environ.get('SYSTEM_MODEL'),
        DEFAULT_CLASS_MODEL_SHORTNAME=os.environ.get('DEFAULT_CLASS_MODEL_SHORTNAME'),
        DATABASE_NAME='codehelp.db',
        HELP_LINK_TEXT='Get Help',
        SUPPORT_EMAIL='rana.moeez.hassan.ug@dartmouth.edu',
        FAVICON='icon.png',
        DOCS_DIR=Path(__file__).resolve().parent / 'docs',
        DEFAULT_LANGUAGES=[
            "Conceptual Question",
            "C",
            "Java",
            "Python",
            "C++",
        ]
    )
    if test_config:
        app_config.update(test_config)

    app = base.create_app_base(__name__, app_config, instance_path)
    
    app.register_blueprint(context_config.bp)
    app.register_blueprint(helper.bp)
    app.register_blueprint(tutor.bp)
    app.register_blueprint(api.bp)

    context_config.register(app)
    admin.register_with_gened()

    app.config['NAVBAR_ITEM_TEMPLATES'].append("tutor_nav_item.html")
    register_commands(app)
    
    return app
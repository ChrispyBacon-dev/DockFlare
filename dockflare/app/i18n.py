import os

from flask import request, session
from flask_babel import Babel, get_locale

from . import config

babel = Babel()


def _resolve_locale():
    requested_locale = request.args.get('lang', '').strip().lower()
    if requested_locale in config.SUPPORTED_LOCALES:
        session['lang'] = requested_locale

    selected_locale = session.get('lang')
    if selected_locale in config.SUPPORTED_LOCALES:
        return selected_locale

    best_match = request.accept_languages.best_match(config.SUPPORTED_LOCALES)
    if best_match:
        return best_match

    return config.DEFAULT_LOCALE


def init_i18n(app_instance):
    app_instance.config['BABEL_DEFAULT_LOCALE'] = config.DEFAULT_LOCALE
    app_instance.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.join(app_instance.root_path, 'translations')
    babel.init_app(app_instance, locale_selector=_resolve_locale)


def get_current_locale():
    locale = get_locale()
    return str(locale) if locale else config.DEFAULT_LOCALE

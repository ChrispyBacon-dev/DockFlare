import json
import os
import logging

from flask import session
from markupsafe import Markup

_translations = {}
_fallback_lang = 'en'

def load_translations(i18n_dir):
    for filename in os.listdir(i18n_dir):
        if filename.endswith('.json'):
            lang = filename[:-5]
            filepath = os.path.join(i18n_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                _translations[lang] = json.load(f)
            logging.info(f"i18n: Loaded {len(_translations[lang])} keys for '{lang}'")

def t(key, **kwargs):
    lang = session.get('lang', _fallback_lang)
    value = _translations.get(lang, {}).get(key)
    if value is None:
        value = _translations.get(_fallback_lang, {}).get(key, key)
    if kwargs:
        for k, v in kwargs.items():
            value = value.replace('{' + k + '}', str(v))
    return Markup(value)

def get_js_translations():
    lang = session.get('lang', _fallback_lang)
    all_keys = _translations.get(lang, {})
    fallback = _translations.get(_fallback_lang, {})
    js_keys = {}
    for k, v in fallback.items():
        if k.startswith('js.'):
            js_keys[k] = all_keys.get(k, v)
    return js_keys

def init_app(app):
    i18n_dir = os.path.dirname(__file__)
    load_translations(i18n_dir)
    app.jinja_env.globals['t'] = t

    @app.context_processor
    def inject_i18n():
        return {
            'current_lang': session.get('lang', 'en'),
            'js_translations': get_js_translations()
        }

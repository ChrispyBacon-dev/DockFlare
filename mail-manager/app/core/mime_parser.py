import email
import email.policy
import email.utils
from datetime import datetime, timezone
import nh3

_ALLOWED_TAGS = {
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'div', 'em',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'i', 'img', 'li', 'ol', 'p',
    'pre', 'span', 'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'th',
    'thead', 'tr', 'u', 'ul',
}

_ALLOWED_ATTRIBUTES = {
    '*': {'class', 'style', 'id'},
    'a': {'href', 'title', 'target'},
    'img': {'src', 'alt', 'width', 'height'},
}


def parse_eml(eml_bytes):
    msg = email.message_from_bytes(eml_bytes, policy=email.policy.default)
    parsed = {
        'message_id': msg.get('Message-ID', '').strip('<>'),
        'from_address': '',
        'from_name': '',
        'to_addresses': [],
        'cc_addresses': [],
        'bcc_addresses': [],
        'subject': msg.get('Subject', ''),
        'date': msg.get('Date'),
        'in_reply_to': msg.get('In-Reply-To', '').strip('<>'),
        'references': msg.get('References', ''),
        'text_body': '',
        'html_body': '',
        'attachments': [],
        'headers_json': [],
    }

    for k, v in msg.items():
        parsed['headers_json'].append({k: v})

    from_header = msg.get('From', '')
    if from_header:
        from_name, from_addr = email.utils.parseaddr(str(from_header))
        parsed['from_address'] = from_addr or str(from_header)
        parsed['from_name'] = from_name

    for addr_header in ['To', 'Cc', 'Bcc']:
        val = msg.get(addr_header, '')
        if val:
            pairs = email.utils.getaddresses([str(val)])
            parsed[f'{addr_header.lower()}_addresses'] = [
                addr for _, addr in pairs if addr
            ]

    try:
        if parsed['date']:
            dt = email.utils.parsedate_to_datetime(parsed['date'])
        else:
            dt = datetime.now(timezone.utc)
        parsed['received_at'] = dt.isoformat()
    except Exception:
        parsed['received_at'] = datetime.now(timezone.utc).isoformat()

    for part in msg.walk():
        if part.is_multipart():
            continue

        content_type = part.get_content_type()
        content_disposition = str(part.get('Content-Disposition', ''))

        if content_type == 'text/plain' and 'attachment' not in content_disposition:
            try:
                parsed['text_body'] += part.get_content()
            except Exception:
                pass
        elif content_type == 'text/html' and 'attachment' not in content_disposition:
            try:
                raw_html = part.get_content()
                parsed['html_body'] += nh3.clean(
                    raw_html,
                    tags=_ALLOWED_TAGS,
                    attributes=_ALLOWED_ATTRIBUTES,
                )
            except Exception:
                pass
        else:
            filename = part.get_filename() or 'unnamed_attachment'
            data = part.get_payload(decode=True)
            if data:
                parsed['attachments'].append({
                    'filename': filename,
                    'content_type': content_type,
                    'data': data,
                    'content_id': part.get('Content-ID', '').strip('<>'),
                    'is_inline': 1 if 'inline' in content_disposition else 0,
                    'size_bytes': len(data),
                })

    return parsed

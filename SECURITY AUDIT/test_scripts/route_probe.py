#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar
from html.parser import HTMLParser

class CSRFTokenParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None
    def handle_starttag(self, tag, attrs):
        if tag.lower() != 'input':
            return
        attr_map = {k.lower(): v for k, v in attrs}
        name = attr_map.get('name')
        if name == 'csrf_token':
            self.token = attr_map.get('value')

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

DEFAULT_ROUTES = [
    ("GET", "/"),
    ("GET", "/agents"),
    ("GET", "/access-policies"),
    ("GET", "/settings"),
    ("GET", "/tunnel-dns-records/test"),
    ("GET", "/ping"),
    ("GET", "/version/check"),
    ("GET", "/debug"),
    ("GET", "/reconciliation-status"),
    ("GET", "/stream-logs"),
    ("GET", "/stream-state-updates"),
    ("GET", "/backup/download"),
    ("GET", "/help"),
    ("GET", "/login"),
    ("POST", "/login"),
    ("GET", "/logout"),
    ("GET", "/api/v2/overview"),
    ("GET", "/api/v2/ping"),
    ("GET", "/api/v2/debug-info"),
    ("GET", "/api/v2/services"),
    ("GET", "/api/v2/zones"),
    ("GET", "/api/v2/zone-policies"),
    ("GET", "/api/v2/agents"),
]

def build_opener():
    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies), NoRedirectHandler())
    opener.addheaders = [("User-Agent", "DockFlareRouteProbe/1.0")]
    return opener, cookies

def fetch(opener, method, url, data=None, headers=None, timeout=10):
    req_headers = headers.copy() if headers else {}
    data_bytes = data
    if isinstance(data, dict):
        data_bytes = urllib.parse.urlencode(data).encode()
        if "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=data_bytes, headers=req_headers, method=method)
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read()
            return {
                "status": response.getcode(),
                "reason": response.reason,
                "headers": {k: v for k, v in response.headers.items()},
                "body": body,
                "url": response.geturl(),
                "error": None,
            }
    except urllib.error.HTTPError as error:
        body = error.read()
        return {
            "status": error.code,
            "reason": error.reason,
            "headers": {k: v for k, v in error.headers.items()},
            "body": body,
            "url": error.geturl(),
            "error": str(error),
        }
    except urllib.error.URLError as error:
        return {
            "status": None,
            "reason": getattr(error, 'reason', str(error)),
            "headers": {},
            "body": b"",
            "url": url,
            "error": str(error),
        }

def parse_csrf_token(html_bytes):
    parser = CSRFTokenParser()
    try:
        parser.feed(html_bytes.decode("utf-8", errors="ignore"))
    except Exception:
        return None
    return parser.token

def attempt_login(opener, base_url, username, password):
    login_url = urllib.parse.urljoin(base_url, "/login")
    login_page = fetch(opener, "GET", login_url)
    if login_page["status"] != 200:
        return {"success": False, "detail": f"login_page_status_{login_page['status']}", "response": login_page}
    csrf_token = parse_csrf_token(login_page["body"])
    if not csrf_token:
        return {"success": False, "detail": "csrf_token_missing", "response": login_page}
    payload = {
        "username": username,
        "password": password,
        "csrf_token": csrf_token,
    }
    submit = fetch(opener, "POST", login_url, data=payload)
    if submit["status"] in (301, 302, 303, 307, 308):
        location = submit["headers"].get("Location", "")
        if location:
            next_url = urllib.parse.urljoin(login_url, location)
            fetch(opener, "GET", next_url)
        return {"success": True, "detail": "redirect", "response": submit}
    if submit["status"] == 200:
        return {"success": False, "detail": "login_failed", "response": submit}
    return {"success": False, "detail": f"unexpected_status_{submit['status']}", "response": submit}

def evaluate_access(result):
    headers = result["headers"]
    location = headers.get("Location", "")
    status = result["status"]
    if status is None:
        return "error", location
    if status in (301, 302, 303, 307, 308):
        if "/login" in location:
            return "auth_required", location
        return "redirect", location
    if status in (401, 403):
        return "auth_required", location
    if status == 200:
        return "ok", location
    if status == 503:
        return "service_unavailable", location
    return f"status_{status}", location

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:5001", help="Target base URL")
    parser.add_argument("--username", help="Login username")
    parser.add_argument("--password", help="Login password")
    parser.add_argument("--master-api-key", help="Master API key for protected API routes")
    parser.add_argument("--routes", help="JSON file with additional route definitions")
    parser.add_argument("--output", choices=["table", "json"], default="table")
    args = parser.parse_args()
    opener, cookies = build_opener()
    routes = list(DEFAULT_ROUTES)
    if args.routes:
        try:
            with open(args.routes, "r", encoding="utf-8") as handle:
                extra = json.load(handle)
                for entry in extra:
                    method = entry.get("method", "GET").upper()
                    path = entry.get("path")
                    if not path:
                        continue
                    routes.append((method, path))
        except Exception as error:
            print(f"Failed to load routes file: {error}", file=sys.stderr)
    login_status = None
    if args.username and args.password:
        login_status = attempt_login(opener, args.base_url.rstrip('/'), args.username, args.password)
    auth_header = {}
    if args.master_api_key:
        auth_header = {"Authorization": f"Bearer {args.master_api_key}"}
    report = []
    for method, path in routes:
        url = urllib.parse.urljoin(args.base_url.rstrip('/'), path)
        headers = {}
        if path.startswith("/api/") and auth_header:
            headers.update(auth_header)
        result = fetch(opener, method, url, headers=headers)
        access, location = evaluate_access(result)
        record = {
            "method": method,
            "path": path,
            "status": result["status"],
            "reason": result["reason"],
            "location": location,
            "access": access,
        }
        report.append(record)
    if args.output == "json":
        output = {
            "login": login_status,
            "routes": report,
        }
        print(json.dumps(output, indent=2))
        return
    if login_status:
        if login_status["success"]:
            print("Login: success")
        else:
            print(f"Login: failed ({login_status['detail']})")
    header = f"{'METHOD':<6} {'PATH':<35} {'STATUS':<6} {'ACCESS':<18} LOCATION"
    print(header)
    print("-" * len(header))
    for entry in report:
        status = entry["status"] if entry["status"] is not None else "ERR"
        location = entry["location"] or ""
        line = f"{entry['method']:<6} {entry['path']:<35} {status!s:<6} {entry['access']:<18} {location}"
        print(line)

if __name__ == "__main__":
    main()

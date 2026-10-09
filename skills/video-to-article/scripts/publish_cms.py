#!/usr/bin/env python3
"""Upload the finished article to a CMS as a DRAFT (never published automatically).

Usage:
    publish_cms.py wordpress <article.md> --site https://example.com --user NAME --password-file FILE [--css blocks.css]
    publish_cms.py ghost     <article.md> --site https://example.com --key-file FILE [--css blocks.css]
    publish_cms.py bundle    <article.md> [--css blocks.css] [-o bundle.zip]

  wordpress  REST API with an Application Password (Users → Profile → Application Passwords).
  ghost      Admin API key "id:secret" (Settings → Integrations → Add custom integration).
  bundle     no API: a zip with article.html, the images and the stylesheet for manual upload.

Credentials are read from files only, never from the command line or the chat. Images referenced by the article
(frames/…, cards/…) are uploaded and their links rewritten. The markdown is converted with the `markdown`
package (pip install markdown). Prints the draft's edit URL.
"""
import argparse
import base64
import hashlib
import hmac
import json
import mimetypes
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path


def md_to_html(md):
    try:
        import markdown
    except ImportError:
        sys.exit("pip install markdown")
    md = re.sub(r"(?s)\A---\n.*?\n---\n", "", md)
    md = re.sub(r"(?s)<!--.*?-->", "", md)
    return markdown.markdown(md, extensions=["extra", "sane_lists"])


def front(md):
    m = re.match(r"(?s)\A---\n(.*?)\n---\n", md)
    return dict(re.findall(r'^(\w+):[ \t]*"?(.*?)"?[ \t]*$', m.group(1), re.M)) if m else {}


def local_images(html, base):
    return [(src, base / src) for src in dict.fromkeys(re.findall(r'<img[^>]+src="([^"]+)"', html))
            if not re.match(r"^https?://", src) and (base / src).exists()]


def request(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"{method or 'GET'} {url} → {e.code}: {e.read().decode()[:400]}")


def secret(path):
    return Path(path).expanduser().read_text(encoding="utf-8").strip()


def wordpress(a, md, html, base):
    auth = "Basic " + base64.b64encode(f"{a.user}:{secret(a.password_file)}".encode()).decode()
    api = a.site.rstrip("/") + "/wp-json/wp/v2"
    for src, path in local_images(html, base):
        media = request(f"{api}/media", data=path.read_bytes(), method="POST", headers={
            "Authorization": auth, "Content-Type": mimetypes.guess_type(path.name)[0] or "image/jpeg",
            "Content-Disposition": f'attachment; filename="{path.name}"'})
        html = html.replace(f'src="{src}"', f'src="{media["source_url"]}"')
    if a.css:
        html = f"<style>{Path(a.css).read_text(encoding='utf-8')}</style>\n" + html
    fm = front(md)
    post = request(f"{api}/posts", method="POST", headers={"Authorization": auth, "Content-Type": "application/json"},
                   data=json.dumps({"title": fm.get("title", ""), "content": html, "status": "draft",
                                    "excerpt": fm.get("description", ""), "slug": fm.get("slug", "")}).encode())
    print(f"draft created: {a.site.rstrip('/')}/wp-admin/post.php?post={post['id']}&action=edit")


def ghost_token(key):
    kid, sec = key.split(":")
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=")
    header = b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": kid}).encode())
    now = int(time.time())
    payload = b64(json.dumps({"iat": now, "exp": now + 300, "aud": "/admin/"}).encode())
    sig = b64(hmac.new(bytes.fromhex(sec), header + b"." + payload, hashlib.sha256).digest())
    return (header + b"." + payload + b"." + sig).decode()


def ghost(a, md, html, base):
    api = a.site.rstrip("/") + "/ghost/api/admin"
    auth = {"Authorization": "Ghost " + ghost_token(secret(a.key_file)), "Accept-Version": "v5.0"}
    for src, path in local_images(html, base):
        boundary = "----va" + hashlib.md5(path.name.encode()).hexdigest()
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
                f"Content-Type: {mimetypes.guess_type(path.name)[0] or 'image/jpeg'}\r\n\r\n").encode() \
            + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        img = request(f"{api}/images/upload/", data=body, method="POST",
                      headers=dict(auth, **{"Content-Type": f"multipart/form-data; boundary={boundary}"}))
        html = html.replace(f'src="{src}"', f'src="{img["images"][0]["url"]}"')
    if a.css:
        html = f"<style>{Path(a.css).read_text(encoding='utf-8')}</style>\n" + html
    fm = front(md)
    post = request(f"{api}/posts/?source=html", method="POST", headers=dict(auth, **{"Content-Type": "application/json"}),
                   data=json.dumps({"posts": [{"title": fm.get("title", ""), "html": html, "status": "draft",
                                               "custom_excerpt": fm.get("description", "")[:300]}]}).encode())
    print(f"draft created: {a.site.rstrip('/')}/ghost/#/editor/post/{post['posts'][0]['id']}")


def bundle(a, md, html, base):
    out = Path(a.output or base / "bundle.zip")
    fm = front(md)
    page = (f"<!doctype html><html lang=\"{fm.get('lang', 'ru')}\"><head><meta charset=\"utf-8\">"
            f"<title>{fm.get('title', '')}</title>" + ('<link rel="stylesheet" href="blocks.css">' if a.css else "")
            + f"</head><body><article><h1>{fm.get('title', '')}</h1>\n{html}\n</article></body></html>")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("article.html", page)
        for src, path in local_images(html, base):
            z.write(path, src)
        if a.css:
            z.write(a.css, "blocks.css")
    print(f"bundle: {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", choices=["wordpress", "ghost", "bundle"])
    ap.add_argument("article")
    ap.add_argument("--site")
    ap.add_argument("--user")
    ap.add_argument("--password-file")
    ap.add_argument("--key-file")
    ap.add_argument("--css")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()
    path = Path(a.article)
    md = path.read_text(encoding="utf-8")
    html = md_to_html(md)
    if a.target == "wordpress" and not (a.site and a.user and a.password_file):
        sys.exit("wordpress needs --site, --user and --password-file")
    if a.target == "ghost" and not (a.site and a.key_file):
        sys.exit("ghost needs --site and --key-file")
    {"wordpress": wordpress, "ghost": ghost, "bundle": bundle}[a.target](a, md, html, path.parent)


if __name__ == "__main__":
    main()

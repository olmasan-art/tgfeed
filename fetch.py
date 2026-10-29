import re, json, hashlib, pathlib, requests
from bs4 import BeautifulSoup

D = pathlib.Path("data"); M = D / "media"; M.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0"}
KEEP = 100
ALLOW = {"b", "strong", "i", "em", "u", "s", "code", "pre", "a", "br", "blockquote"}

def media(url):
    if not url: return None
    n = hashlib.md5(url.encode()).hexdigest()[:16] + ".jpg"
    p = M / n
    if not p.exists():
        try:
            r = requests.get(url, headers=H, timeout=30); r.raise_for_status()
            p.write_bytes(r.content)
        except Exception as e:
            print("img fail", url, e); return None
    return "data/media/" + n

def bg(el):
    m = re.search(r"url\(['\"]?(.*?)['\"]?\)", el.get("style", "")) if el else None
    return m.group(1) if m else None

def clean(el):
    for t in el.find_all(True):
        if t.name not in ALLOW: t.unwrap(); continue
        href = t.get("href") if t.name == "a" else None
        t.attrs = {"href": href, "target": "_blank", "rel": "noopener"} if href else {}
    return el.decode_contents()

def txt(s, sel):
    e = s.select_one(sel); return e.get_text(" ", strip=True) if e else ""

def grab(ch):
    r = requests.get(f"https://t.me/s/{ch}", headers=H, timeout=30); r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")
    img = s.select_one(".tgme_header_link img, .tgme_channel_info_header img")
    info = {"id": ch, "title": txt(s, ".tgme_channel_info_header_title") or ch,
            "desc": txt(s, ".tgme_channel_info_description"),
            "subs": " · ".join(c.get_text(" ", strip=True) for c in s.select(".tgme_channel_info_counter")[:2]),
            "avatar": media(img["src"]) if img and img.get("src") else None}
    f = D / f"{ch}.json"
    old = {p["id"]: p for p in json.loads(f.read_text())["posts"]} if f.exists() else {}
    for m in s.select(".tgme_widget_message[data-post]"):
        pid = int(m["data-post"].split("/")[1])
        t = m.select_one(".tgme_widget_message_text")
        d = m.select_one(".tgme_widget_message_date time")
        v = m.select_one(".tgme_widget_message_views")
        fw = m.select_one(".tgme_widget_message_forwarded_from_name")
        lp = m.select_one(".tgme_widget_message_link_preview")
        vt = m.select_one(".tgme_widget_message_video_thumb, .tgme_widget_message_roundvideo_thumb")
        old[pid] = {"id": pid, "date": d["datetime"] if d else "",
            "html": clean(t) if t else "", "views": v.get_text(strip=True) if v else "",
            "fwd": fw.get_text(strip=True) if fw else "",
            "photos": [x for x in (media(bg(p)) for p in m.select(".tgme_widget_message_photo_wrap")) if x],
            "video": media(bg(vt)) if vt else None, "hasvideo": bool(vt),
            "link": {"url": lp.get("href", ""), "title": txt(lp, ".link_preview_title") or txt(lp, ".link_preview_site_name"),
                     "desc": txt(lp, ".link_preview_description")} if lp else None}
    posts = sorted(old.values(), key=lambda p: p["id"])[-KEEP:]
    f.write_text(json.dumps({"posts": posts}, ensure_ascii=False))
    if posts:
        l = posts[-1]; info["last"] = re.sub(r"<[^>]+>", " ", l["html"]).strip()[:80] or "📷"; info["time"] = l["date"]
    return info

chs = [l.strip().lstrip("@").rstrip("/").split("/")[-1] for l in open("channels.txt") if l.strip() and not l.startswith("#")]
idx = []
for c in chs:
    try: idx.append(grab(c)); print("ok", c)
    except Exception as e: print("FAIL", c, e)
if idx: (D / "channels.json").write_text(json.dumps(idx, ensure_ascii=False))
used = set(re.findall(r"data/media/\w+\.jpg", "".join(p.read_text() for p in D.glob("*.json"))))
for p in M.glob("*.jpg"):
    if "data/media/" + p.name not in used: p.unlink()

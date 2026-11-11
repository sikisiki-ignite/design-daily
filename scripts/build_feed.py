#!/usr/bin/env python3
"""items/*.json -> docs/feed.xml (RSS 2.0, Slack RSS 앱 구독용) + docs/index.html (미리보기).

items/YYYY-MM-DD.json 형식:
[
  {
    "id": "x 게시물 status id",
    "url": "https://x.com/<handle>/status/<id>",
    "author": "@handle",
    "title": "한 줄 제목",
    "summary": ["요약 1", "요약 2", "요약 3"],
    "apply": "적용 아이디어 (외부 공개용 일반 표현)",
    "tags": ["motion", "feedback"],
    "category": "UI" | "Motion",
    "image": "썸네일 URL (선택)"
  }
]
"""
import json
import html
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items"
DOCS = ROOT / "docs"
KST = timezone(timedelta(hours=9))
FEED_TITLE = "Design Daily"
FEED_DESC = "UI·모션 디자인 일일 리서치 (현재 출처: X)"
MAX_ITEMS = 60


def load_items():
    out = []
    for f in sorted(ITEMS.glob("*.json")):
        day = datetime.strptime(f.stem, "%Y-%m-%d").replace(hour=10, tzinfo=KST)
        for i, it in enumerate(json.loads(f.read_text(encoding="utf-8"))):
            # 같은 날 항목 순서 유지를 위해 1분씩 차이를 둠 (Top 1이 가장 먼저 게시)
            it["_date"] = day + timedelta(minutes=i)
            it["_day"] = f.stem
            out.append(it)
    out.sort(key=lambda x: x["_date"], reverse=True)
    return out[:MAX_ITEMS]


def description(it):
    lines = [f"- {s}" for s in it["summary"]]
    if it.get("apply"):
        lines.append(f"- 적용 아이디어: {it['apply']}")
    return "\n".join(lines)


def page_url(it, base_url):
    return f"{base_url}p/{it['id']}.html"


def item_title(it):
    return f"[{it.get('category', 'UI')}] {it['title']} — {it['author']}"


def build_item_page(it, base_url):
    """슬랙 unfurl용 항목 페이지: og/twitter 메타 + 썸네일 + X 원문 버튼."""
    x = html.escape
    title = item_title(it)
    desc = " ".join(it["summary"])[:280]
    img = it.get("image", "")
    lis = "".join(f"<li>{x(s)}</li>" for s in it["summary"])
    if it.get("apply"):
        lis += f'<li class="apply">적용 아이디어: {x(it["apply"])}</li>'
    tags = " ".join(f"<span>#{x(t)}</span>" for t in it.get("tags", []))
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{x(title)}</title>
<meta name="description" content="{x(desc)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{x(FEED_TITLE)}">
<meta property="og:title" content="{x(title)}">
<meta property="og:description" content="{x(desc)}">
<meta property="og:url" content="{x(page_url(it, base_url))}">
{f'<meta property="og:image" content="{x(img)}">' if img else ''}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{x(title)}">
<meta name="twitter:description" content="{x(desc)}">
{f'<meta name="twitter:image" content="{x(img)}">' if img else ''}
<style>
:root{{--bg:#fff;--fg:#1d1c1d;--muted:#616061;--link:#1264a3;--line:#e8e8e8;--btn:#1d1c1d;--btnfg:#fff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1a1d21;--fg:#d1d2d3;--muted:#9a9b9e;--link:#1d9bd1;--line:#35373b;--btn:#d1d2d3;--btnfg:#1a1d21}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,"Apple SD Gothic Neo",sans-serif}}
main{{max-width:720px;margin:0 auto;padding:24px 16px 48px}}
.top{{font-size:13px;color:var(--muted)}} .top a{{color:var(--muted)}}
h1{{font-size:22px;line-height:1.4;margin:8px 0 16px}}
img{{width:100%;border-radius:12px;border:1px solid var(--line)}}
ul{{padding-left:20px}} li{{margin:6px 0}} li.apply{{color:var(--muted)}}
a.btn{{display:inline-block;background:var(--btn);color:var(--btnfg);text-decoration:none;padding:12px 20px;border-radius:999px;font-weight:600;margin-top:8px}}
.tags span{{font-size:13px;color:var(--muted);margin-right:8px}}
</style></head><body><main>
<div class="top"><a href="../">{x(FEED_TITLE)}</a> · {it['_day']}</div>
<h1>{x(title)}</h1>
{f'<a href="{x(it["url"])}"><img src="{x(img)}" alt=""></a>' if img else ''}
<ul>{lis}</ul>
<a class="btn" href="{x(it['url'])}">X에서 원문 보기 →</a>
<p class="tags">{tags}</p>
</main></body></html>
"""


def build_rss(items, base_url):
    x = html.escape
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "<channel>",
        f"<title>{x(FEED_TITLE)}</title>",
        f"<link>{x(base_url)}</link>",
        f"<description>{x(FEED_DESC)}</description>",
        "<language>ko</language>",
        f'<atom:link href="{x(base_url)}feed.xml" rel="self" type="application/rss+xml"/>',
        f"<lastBuildDate>{format_datetime(datetime.now(KST))}</lastBuildDate>",
    ]
    for it in items:
        title = item_title(it)
        parts += [
            "<item>",
            f"<title>{x(title)}</title>",
            # 링크는 항목별 페이지 — og:image로 슬랙 썸네일 미리보기를 띄우고, 페이지에서 X 원문으로 이동
            f"<link>{x(page_url(it, base_url))}</link>",
            f'<guid isPermaLink="false">xdd-{x(str(it["id"]))}</guid>',
            f"<pubDate>{format_datetime(it['_date'])}</pubDate>",
            f"<description>{x(description(it))}</description>",
        ]
        for t in it.get("tags", []):
            parts.append(f"<category>{x(t)}</category>")
        if it.get("image"):
            parts.append(f'<enclosure url="{x(it["image"])}" type="image/jpeg" length="0"/>')
        parts.append("</item>")
    parts += ["</channel>", "</rss>"]
    return "\n".join(parts) + "\n"


def build_html(items):
    x = html.escape
    cards = []
    for it in items:
        img = f'<img src="{x(it["image"])}" alt="" loading="lazy">' if it.get("image") else ""
        lis = "".join(f"<li>{x(s)}</li>" for s in it["summary"])
        if it.get("apply"):
            lis += f'<li class="apply">적용 아이디어: {x(it["apply"])}</li>'
        tags = " ".join(f"<span>#{x(t)}</span>" for t in it.get("tags", []))
        cards.append(f"""
<article>
  <div class="meta"><b>{x(FEED_TITLE)}</b> <em>앱</em> <time>{it['_day']}</time></div>
  <a class="title" href="{x(it['url'])}" target="_blank" rel="noopener">[{x(it.get('category','UI'))}] {x(it['title'])} — {x(it['author'])}</a>
  <ul>{lis}</ul>
  {img}
  <div class="tags">{tags}</div>
</article>""")
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{x(FEED_TITLE)}</title>
<link rel="alternate" type="application/rss+xml" title="{x(FEED_TITLE)}" href="feed.xml">
<style>
:root{{--bg:#fff;--fg:#1d1c1d;--muted:#616061;--link:#1264a3;--line:#e8e8e8}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1a1d21;--fg:#d1d2d3;--muted:#9a9b9e;--link:#1d9bd1;--line:#35373b}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,"Apple SD Gothic Neo",sans-serif}}
main{{max-width:760px;margin:0 auto;padding:24px 16px}}
h1{{font-size:20px;margin:0 0 4px}} p.sub{{color:var(--muted);margin:0 0 24px}}
article{{padding:16px 0;border-top:1px solid var(--line)}}
.meta{{font-size:13px;color:var(--muted)}} .meta b{{color:var(--fg);font-size:15px}} .meta em{{font-style:normal;font-size:11px;border:1px solid var(--line);padding:0 4px;border-radius:3px;margin:0 6px}}
a.title{{display:block;color:var(--link);text-decoration:none;font-weight:600;margin:4px 0}}
ul{{margin:4px 0;padding-left:18px}} li.apply{{color:var(--muted)}}
img{{max-width:100%;max-height:360px;border-radius:8px;margin-top:8px}}
.tags span{{font-size:12px;color:var(--muted);margin-right:6px}}
</style></head><body><main>
<h1>{x(FEED_TITLE)}</h1><p class="sub">{x(FEED_DESC)} · <a href="feed.xml">RSS</a></p>
{''.join(cards)}
</main></body></html>
"""


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://sikisiki-ignite.github.io/design-daily/"
    items = load_items()
    DOCS.mkdir(exist_ok=True)
    (DOCS / "feed.xml").write_text(build_rss(items, base_url), encoding="utf-8")
    (DOCS / "index.html").write_text(build_html(items), encoding="utf-8")
    (DOCS / "p").mkdir(exist_ok=True)
    for it in items:
        (DOCS / "p" / f"{it['id']}.html").write_text(build_item_page(it, base_url), encoding="utf-8")
    print(f"built {len(items)} items -> docs/feed.xml, docs/index.html")


if __name__ == "__main__":
    main()

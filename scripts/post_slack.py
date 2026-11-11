#!/usr/bin/env python3
"""items/*.json 항목을 Design Daily 봇으로 슬랙 채널에 게시한다.

사용:
  python3 scripts/post_slack.py items/2026-11-11-1430.json            # 아직 안 올린 항목 전부 게시
  python3 scripts/post_slack.py items/2026-11-11-1430.json --id <id>  # 한 항목만
  python3 scripts/post_slack.py items/... --dry-run                   # 보낼 내용만 출력
  python3 scripts/post_slack.py items/... --id <id> --delete          # 올린 메시지 삭제

- 토큰·채널은 .env (SLACK_BOT_TOKEN, SLACK_CHANNEL_ID). git에 올라가지 않음.
- 메시지마다 X 작성자 이름·프로필 사진으로 표시(chat:write.customize) → 연속 게시돼도 글마다 구분됨.
- 게시 후 slack_ts를 항목 JSON에 기록 → 중복 게시 방지, 수정·삭제 가능.
- unfurl을 끄고 썸네일은 image 블록으로 직접 넣는다 (링크 카드가 여러 개 붙어 흘러내리는 문제 방지).
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def api(method, token, payload):
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_message(it, channel):
    title = f"[{it.get('category', 'UI')}] {it['title']}"
    body = f"*<{it['url']}|{esc(title)}>*"
    if it.get("summary"):
        body += "\n" + "\n".join(f"• {esc(s)}" for s in it["summary"])
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": body}}]
    if it.get("apply"):
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"💡 {esc(it['apply'])}"}})
    if it.get("links"):
        lines = []
        for l in it["links"]:
            note = f" — {esc(l['note'])}" if l.get("note") else ""
            lines.append(f"🔗 <{l['url']}|{esc(l['title'])}>{note}")
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}})
    if it.get("image"):
        blocks.append({"type": "image", "image_url": it["image"], "alt_text": it["title"][:200]})
    tags = " ".join(f"#{t}" for t in it.get("tags", []))
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f"<{it['url']}|X 원문 보기> · {esc(tags)}"}]})
    msg = {
        "channel": channel,
        "text": title,
        "blocks": blocks,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    name = it.get("name")
    msg["username"] = f"{name} ({it['author']})" if name else it["author"]
    if it.get("avatar"):
        msg["icon_url"] = it["avatar"]
    return msg


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    path = Path(args[0])
    only = args[args.index("--id") + 1] if "--id" in args else None
    dry = "--dry-run" in args
    delete = "--delete" in args
    env = load_env()
    token, channel = env.get("SLACK_BOT_TOKEN"), env.get("SLACK_CHANNEL_ID")
    if not dry and not (token and channel):
        sys.exit(".env에 SLACK_BOT_TOKEN / SLACK_CHANNEL_ID가 필요합니다")

    items = json.loads(path.read_text(encoding="utf-8"))
    for it in items:
        if only and it["id"] != only:
            continue
        if delete:
            if it.get("slack_ts"):
                r = api("chat.delete", token, {"channel": channel, "ts": it["slack_ts"]})
                print("삭제" if r.get("ok") else f"실패: {r.get('error')}", it["id"])
                if r.get("ok"):
                    it.pop("slack_ts")
            continue
        if it.get("slack_ts"):
            print("이미 게시됨, 건너뜀:", it["id"])
            continue
        msg = build_message(it, channel)
        if dry:
            print(json.dumps(msg, ensure_ascii=False, indent=2))
            continue
        r = api("chat.postMessage", token, msg)
        if not r.get("ok") and r.get("error") == "invalid_blocks" and it.get("image"):
            # 슬랙이 썸네일 URL을 못 가져오면(예: 429) invalid_blocks → 이미지 없이 재시도
            msg["blocks"] = [b for b in msg["blocks"] if b["type"] != "image"]
            r = api("chat.postMessage", token, msg)
            if r.get("ok"):
                print("  (썸네일을 가져오지 못해 이미지 없이 게시)")
        if not r.get("ok"):
            print("실패:", it["id"], r.get("error"))
            continue
        it["slack_ts"] = r["ts"]
        print("게시:", it["id"], it["title"][:40])
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        time.sleep(1.5)
    if delete:
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

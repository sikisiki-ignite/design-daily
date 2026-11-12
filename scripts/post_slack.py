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

items/YYYY-MM-DD-HHMM.json 항목 형식:
  id        X: status id / Threads: "th_<post code>"
  source    "X"(기본) | "Threads"
  url       원문 URL (x.com/<handle>/status/<id> · threads.com/@<handle>/post/<code>)
  author    "@handle"
  name      표시 이름 (메시지 발신자 이름)
  avatar    프로필 이미지 URL (메시지 아이콘). Threads CDN 이미지는 약 4~5일 뒤 만료됨
  category  "UI" | "AI"
  title     한 줄 제목
  summary   ["요약", ...] 1~3줄 — 원문 재진술 금지
  apply     적용 아이디어 한 줄
  tags      ["tag", ...]
  image     썸네일 URL (선택)
  links     [{"title", "url", "note"(선택)}] (선택)
  slack_ts  게시 후 자동 기록 (수정·삭제용)
"""
import json
import re
import subprocess
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


AVATAR_DIR = ROOT / "assets" / "avatars"
RAW_BASE = "https://raw.githubusercontent.com/sikisiki-ignite/design-daily/main/assets/avatars/"


def host_avatars(items):
    """슬랙은 Threads(Instagram CDN) 프로필 사진 URL을 icon_url로 받지 않음(invalid_arguments).
    → pbs.twimg.com이 아닌 아바타는 저장소 assets/avatars/에 복사하고 raw.githubusercontent 주소로 바꾼다.
    (CDN 서명 URL 만료 문제도 함께 피함)"""
    changed = []
    for it in items:
        av = it.get("avatar")
        if not av or "pbs.twimg.com" in av or av.startswith(RAW_BASE) or it.get("slack_ts"):
            continue
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", it["author"].lstrip("@")) + ".jpg"
        AVATAR_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(av, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            (AVATAR_DIR / name).write_bytes(r.read())
        it["avatar"] = RAW_BASE + name
        changed.append(name)
    if changed:
        subprocess.run(["git", "add", str(AVATAR_DIR)], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-qm", "avatars: " + ", ".join(changed)], cwd=ROOT, check=True)
        subprocess.run(["git", "push", "-q"], cwd=ROOT, check=True)
        for _ in range(12):  # raw 주소가 열릴 때까지 대기
            try:
                urllib.request.urlopen(RAW_BASE + changed[-1], timeout=10)
                break
            except Exception:
                time.sleep(5)
        print("아바타 호스팅:", ", ".join(changed))
    return bool(changed)


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
    source = it.get("source", "X")
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f"<{it['url']}|{source} 원문 보기> · {esc(tags)}"}]})
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
    if not dry and not delete and host_avatars(items):
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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

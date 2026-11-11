#!/bin/zsh
# 이번 회차 항목을 pub 시각에 맞춰 하나씩 공개한다 (슬랙에서 글마다 아이콘이 따로 붙게).
# 사용: zsh scripts/release.sh   — 미래 pub 항목이 모두 공개되면 종료.
cd "$(dirname "$0")/.." || exit 1
BASE=https://sikisiki-ignite.github.io/design-daily/
while true; do
  python3 scripts/build_feed.py "$BASE" >/dev/null
  if ! git diff --quiet -- docs || [ -n "$(git ls-files --others --exclude-standard docs)" ]; then
    git add docs && git commit -qm "release $(date '+%F %H:%M')" && git push -q && echo "$(date '+%H:%M') 공개 1건 push"
  fi
  read n wait <<< "$(python3 scripts/build_feed.py --pending)"
  [ "$n" -eq 0 ] && echo "$(date '+%H:%M') 모두 공개 완료" && break
  echo "$(date '+%H:%M') 남은 ${n}건, ${wait}초 후 다음 공개"
  sleep "$wait"
done

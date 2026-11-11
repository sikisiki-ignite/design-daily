# Design Daily

X(구 트위터)에서 UI·모션 디자인 게시물을 매일 수집·분석해 RSS로 발행하고, 슬랙 RSS 앱으로 채널에 구독시키는 프로젝트.

## 구조
- `items/YYYY-MM-DD.json` — 그날 분석 결과 (형식은 `scripts/build_feed.py` 상단 주석)
- `scripts/build_feed.py <base_url>` — items → `docs/feed.xml`(RSS) + `docs/index.html`(미리보기)
- `docs/` — GitHub Pages로 공개되는 폴더
- `.work/` — 수집 원본·스크린샷 (git 제외)

## 일일 절차
1. ego-browser(로그인된 X 계정)로 최근 7일 검색. 쿼리는 UI / 모션(filter:videos) / 제품 디자인 3종, Top 정렬, min_faves 100~300.
2. 이미 발행한 id(기존 items/*.json)는 제외.
3. 제외 기준: "bookmark this" 링크 모음, AI 도구 과장 홍보, 강의·구인 홍보, 미디어 없는 글.
4. 남은 후보를 직접 열어 스크린샷으로 화면·모션 확인 후 상위 5~6개 선정 (UI/Motion 균형).
5. 항목마다 요약 3줄 + 적용 아이디어 1줄. 측정하지 않은 수치(ms 등)는 쓰지 않는다.
6. **공개 피드이므로 적용 아이디어에 회사·내부 제품 이름을 쓰지 않는다.**
7. `python3 scripts/build_feed.py https://sikisiki-ignite.github.io/design-daily/` 후 커밋·푸시.

## 결정 기록
- 2026-11-11: 슬랙 게시는 웹훅 대신 RSS 피드 + 슬랙 RSS 앱 구독 방식 (워크스페이스 기존 방식과 동일, 관리자 승인 불필요). 대가: 피드 공개, 굵게 등 서식 없음.

- 2026-11-11: 저장소 이름은 design-daily (X 외 출처 확장 대비). 피드 주소 feed.xml은 출처가 늘어도 유지 — 바꾸면 슬랙 구독이 끊김.
- 2026-11-11: 운영 방식은 반자동. 사용자가 매일 10시경 "오늘 Design Daily 돌려줘"라고 요청하면 위 '일일 절차'를 실행한다. 무인 자동 실행(launchd + claude -p)은 X 게시물을 통한 프롬프트 인젝션 → 공개 저장소 게시 위험 때문에 보류. 1~2주 운영으로 필터·문구 기준이 안정되면 권한을 좁힌(ego-browser, build_feed.py, git만 허용) 자동 실행으로 전환을 검토.

## 실행 트리거
"오늘 Design Daily 돌려줘" → 오늘 날짜로 일일 절차 1~7 실행. 푸시 전에 선정 항목 목록을 사용자에게 보여주고 확인받는다.

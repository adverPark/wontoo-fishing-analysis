# 원투낚시 유튜브 알고리즘 분석기

## 프로젝트 개요
낚시 유튜브 채널들을 순회하여 원투낚시 영상 중 알고리즘을 탄 영상을 찾고, 자막을 받아 분석하여 시각적 HTML 리포트로 정리하는 도구.

## 기술 스택
- **패키지 관리:** uv
- **채널/영상 검색:** yt-dlp (ytsearch + 채널 scraping)
- **구독자수:** YouTube Data API v3 channels.list 배치 조회
- **자막 추출:** youtube-transcript-api → yt-dlp fallback
- **AI 분석:** Claude Code 서브에이전트 (video-analyzer, strategy-advisor)
- **리포트:** 단일 HTML (인라인 CSS + Chart.js CDN)

## 실행 방법
`/run` 커맨드 또는:
```bash
uv run python scripts/run_all.py collect   # 데이터 수집 (01~03)
# → 서브에이전트로 AI 분석 (04)
uv run python scripts/run_all.py report    # 리포트 생성 (05)
```

## 파이프라인
1. `01_discover_channels.py` — 채널 발굴 (yt-dlp ytsearch)
2. `02_collect_videos.py` — 영상 수집 + 알고리즘 히트 판별
3. `03_extract_subtitles.py` — 자막 + 썸네일 추출
4. **서브에이전트** — AI 분석 (video-analyzer → strategy-advisor)
5. `05_generate_report.py` — HTML 리포트 생성

## 서브에이전트
- `channel-finder` — 채널 발굴 실행 + 검증
- `video-analyzer` — 히트 영상 자막+썸네일+제목 심층 분석 → data/analysis/{video_id}.json
- `strategy-advisor` — 히트vs비히트 비교 + 성공요인 그룹핑 + 소재추천 → summary.json + 리포트

## 데이터 흐름
- `data/channels.json` — 발굴된 채널 목록
- `data/videos.json` — 수집된 영상 + 알고리즘 히트 정보
- `data/subtitles/{video_id}.txt` — 자막 텍스트
- `data/thumbnails/{video_id}.jpg` — 썸네일 이미지
- `data/analysis/{video_id}.json` — 개별 영상 AI 분석 (점수+상세)
- `data/analysis/summary.json` — 종합 전략 분석
- `output/원투낚시_알고리즘_분석.html` — 최종 리포트

## API 키 설정
`.env` 파일에 YOUTUBE_API_KEY 설정 필요

## 주의사항
- youtube-transcript-api v1.2.4: `seg.text` 속성 접근 (dict 아님)
- yt-dlp 채널 scraping: view_count, duration 포함
- YouTube API quota: 구독자 조회만 사용 (총 2 quota 이하)

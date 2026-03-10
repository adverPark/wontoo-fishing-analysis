---
name: run
description: 원투낚시 알고리즘 분석 전체 파이프라인을 실행합니다.
user-invocable: true
---

전체 파이프라인을 실행합니다.

## 실행 순서

### 1단계: 데이터 수집 (Python 스크립트)
```bash
uv run python scripts/01_discover_channels.py
uv run python scripts/02_collect_videos.py
uv run python scripts/03_extract_subtitles.py
```
각 단계 완료 시 결과를 간략히 보고하세요.

### 2단계: 분석 현황 확인
```bash
uv run python scripts/04_analyze_content.py
```
분석 대기 영상 수와 상태를 확인합니다.

### 3단계: AI 분석 (서브에이전트)
- **video-analyzer** 에이전트를 호출하여 개별 히트 영상을 분석합니다.
  - data/subtitles/{video_id}.txt를 읽고 분석 → data/analysis/{video_id}.json 저장
- **strategy-advisor** 에이전트를 호출하여 종합 전략을 분석합니다.
  - 개별 분석 결과 종합 → data/analysis/summary.json 저장

### 4단계: 컨펌 후 리포트 생성
- 분석 결과(summary.json)를 사용자에게 요약 보고
- **사용자 확인을 받은 후** `uv run python scripts/05_generate_report.py` 실행

### 5단계: 결과 보고
- 발견 채널 수
- 수집 영상 수, 알고리즘 히트 수
- 자막 추출 성공 수
- AI 분석 완료 수
- HTML 리포트 경로: output/원투낚시_알고리즘_분석.html

오류 발생 시 해당 스크립트의 에러를 분석하고 수정한 뒤 재실행하세요.

## 전제 조건
- .env에 YOUTUBE_API_KEY 설정
- `uv sync` 완료 (패키지 설치)

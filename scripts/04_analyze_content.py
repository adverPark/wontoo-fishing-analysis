"""04. 분석 데이터 준비 — 서브에이전트가 분석할 데이터를 정리하여 출력

이 스크립트는 직접 AI 분석을 하지 않습니다.
Claude Code 서브에이전트(video-analyzer, strategy-advisor)가 읽고 분석할
데이터를 준비하고 상태를 확인합니다.
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
VIDEOS_FILE = DATA_DIR / "videos.json"
SUBTITLES_DIR = DATA_DIR / "subtitles"
ANALYSIS_DIR = DATA_DIR / "analysis"


def main():
    if not VIDEOS_FILE.exists():
        print("❌ data/videos.json 없음 — 이전 단계를 먼저 실행하세요")
        sys.exit(1)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    videos = json.loads(VIDEOS_FILE.read_text())
    hit_videos = [v for v in videos if v.get("is_algorithm_hit")]

    # 자막 있는 히트 영상 확인
    ready = []
    no_subtitle = []
    already_analyzed = []

    for v in hit_videos:
        vid = v["video_id"]
        analysis_file = ANALYSIS_DIR / f"{vid}.json"
        subtitle_file = SUBTITLES_DIR / f"{vid}.txt"

        if analysis_file.exists():
            already_analyzed.append(v)
        elif subtitle_file.exists():
            ready.append(v)
        else:
            no_subtitle.append(v)

    summary_exists = (ANALYSIS_DIR / "summary.json").exists()

    print(f"{'='*50}")
    print(f"📊 분석 데이터 현황")
    print(f"{'='*50}")
    print(f"  알고리즘 히트 영상: {len(hit_videos)}개")
    print(f"  분석 대기 (자막 있음): {len(ready)}개")
    print(f"  분석 완료: {len(already_analyzed)}개")
    print(f"  자막 없음 (스킵): {len(no_subtitle)}개")
    print(f"  종합 전략 분석: {'완료' if summary_exists else '미완료'}")
    print(f"{'='*50}")

    if not ready and not already_analyzed:
        print("\n⚠️ 분석할 영상이 없습니다.")
        return

    if ready:
        print(f"\n🔍 분석 대기 영상 {len(ready)}개:")
        for v in ready:
            vid = v["video_id"]
            subtitle_file = SUBTITLES_DIR / f"{vid}.txt"
            sub_len = len(subtitle_file.read_text(encoding="utf-8"))
            print(f"  - [{v['hit_tier']}] {v['title'][:50]}")
            print(f"    조회수: {v['view_count']:,} | 자막: {sub_len:,}자")
            print(f"    video_id: {vid}")

    if ready or not summary_exists:
        print(f"\n💡 서브에이전트로 분석을 실행하세요:")
        if ready:
            print(f"  → video-analyzer 에이전트: 개별 영상 {len(ready)}개 분석")
        if not summary_exists:
            print(f"  → strategy-advisor 에이전트: 종합 전략 분석")
    else:
        print("\n✅ 모든 분석이 완료되었습니다.")


if __name__ == "__main__":
    main()

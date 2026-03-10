"""데이터 수집 파이프라인 실행 (01~03 + 05)

AI 분석(04단계)은 Claude Code 서브에이전트가 수행합니다.
이 스크립트는 데이터 수집과 리포트 생성만 담당합니다.

사용법:
  uv run python scripts/run_all.py collect   # 01~03 데이터 수집
  uv run python scripts/run_all.py report    # 05 리포트 생성
  uv run python scripts/run_all.py           # 전체 (수집 + 분석현황 + 리포트)
"""

import subprocess
import sys
import os

scripts_dir = os.path.dirname(os.path.abspath(__file__))

COLLECT_STEPS = [
    ("01_discover_channels.py", "채널 발굴"),
    ("02_collect_videos.py",    "영상 수집 + 알고리즘 판별"),
    ("03_extract_subtitles.py", "자막 추출"),
]

ANALYZE_STEP = ("04_analyze_content.py", "분석 데이터 현황 확인")
REPORT_STEP = ("05_generate_report.py", "HTML 리포트 생성")


def run_step(script: str, desc: str, step_num: int, total: int) -> bool:
    print(f"\n{'='*50}")
    print(f"[{step_num}/{total}] {desc}")
    print(f"{'='*50}")
    script_path = os.path.join(scripts_dir, script)
    result = subprocess.run([sys.executable, script_path])
    if result.returncode != 0:
        print(f"\n❌ 오류 발생: {script}")
        print("수정 후 다시 실행하면 완료된 단계는 스킵됩니다.")
        return False
    print(f"✅ {desc} 완료!")
    return True


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    print("🎣 원투낚시 알고리즘 분석기")
    print(f"{'='*50}\n")

    if mode in ("all", "collect"):
        for i, (script, desc) in enumerate(COLLECT_STEPS, 1):
            if not run_step(script, desc, i, len(COLLECT_STEPS)):
                sys.exit(1)

    if mode == "all":
        # 분석 현황 표시
        run_step(*ANALYZE_STEP, 4, 5)
        print("\n💡 AI 분석은 서브에이전트가 수행합니다.")
        print("   /run 커맨드 또는 video-analyzer → strategy-advisor 순서로 실행하세요.")

    if mode == "report":
        if not run_step(*REPORT_STEP, 1, 1):
            sys.exit(1)
        print(f"\n→ output/원투낚시_알고리즘_분석.html")
    elif mode == "all":
        print(f"\n{'='*50}")
        print("🎣 데이터 수집 완료!")
        print("→ 다음: 서브에이전트로 AI 분석 실행")
        print("→ 분석 완료 후 컨펌받고 리포트 생성:")
        print("  uv run python scripts/run_all.py report")
        print(f"{'='*50}")


if __name__ == "__main__":
    main()

"""02. 영상 수집 — yt-dlp 채널 scraping + 알고리즘 히트 판별"""

import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"
VIDEOS_FILE = DATA_DIR / "videos.json"

import re

# 원투낚시 키워드 (일본어 + 한국어 + 영어)
WONTOO_KEYWORDS = [
    "投げ釣り", "ぶっこみ釣り", "遠投カゴ", "遠投釣り",
    "サーフフィッシング", "ちょい投げ",
    "원투", "서프캐스팅", "원캐",
]
WONTOO_PATTERNS = [
    re.compile(r"surf\s*cast", re.IGNORECASE),
    re.compile(r"surf\s*fish", re.IGNORECASE),
    re.compile(r"beach\s*cast", re.IGNORECASE),
    re.compile(r"投げ\s*釣", re.IGNORECASE),
]


def is_wontoo_video(title: str) -> bool:
    """원투낚시 관련 키워드 포함 여부"""
    title_lower = title.lower()
    if any(kw in title for kw in WONTOO_KEYWORDS):
        return True
    return any(pat.search(title) for pat in WONTOO_PATTERNS)


def is_algorithm_hit(views: int, channel_avg_views: float, subscribers: int) -> tuple[bool, str | None, float]:
    """알고리즘 히트 판별 — 조회수 10만+ AND 채널 평균의 2배+"""
    if views >= 100_000 and channel_avg_views > 0 and views >= channel_avg_views * 2:
        ratio = views / max(channel_avg_views, 1)
        return True, "HIT", ratio

    return False, None, 0.0


def scrape_channel_videos(channel_id: str) -> list[dict]:
    """yt-dlp로 채널의 전체 영상 목록 수집"""
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    cmd = [
        "yt-dlp", "--flat-playlist", "--dump-json",
        "--no-warnings", "--quiet",
        "--playlist-end", "300",
        url,
    ]
    videos = []
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        for line in proc.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                entry = json.loads(line)
                video_id = entry.get("id")
                title = entry.get("title", "")
                view_count = entry.get("view_count")
                duration = entry.get("duration")

                if video_id and view_count is not None:
                    videos.append({
                        "video_id": video_id,
                        "title": title,
                        "view_count": int(view_count),
                        "duration": duration,
                        "upload_date": entry.get("upload_date"),
                        "description": entry.get("description", ""),
                    })
            except (json.JSONDecodeError, ValueError):
                continue
    except subprocess.TimeoutExpired:
        print(f"    ⚠️ 타임아웃")
    except Exception as e:
        print(f"    ⚠️ 오류: {e}")
    return videos


def main():
    if not CHANNELS_FILE.exists():
        print("❌ data/channels.json 없음 — 01_discover_channels.py 먼저 실행하세요")
        sys.exit(1)

    channels = json.loads(CHANNELS_FILE.read_text())

    # 재개 지원 — 이미 수집된 채널은 스킵
    all_videos = []
    scraped_channel_ids: set[str] = set()
    if VIDEOS_FILE.exists():
        all_videos = json.loads(VIDEOS_FILE.read_text())
        scraped_channel_ids = set(v["channel_id"] for v in all_videos)

    pending_channels = [ch for ch in channels if ch["channel_id"] not in scraped_channel_ids]
    if not pending_channels:
        hit_count = sum(1 for v in all_videos if v.get("is_algorithm_hit"))
        print(f"✅ 이미 완료됨: {len(all_videos)}개 영상 (히트 {hit_count}개)")
        return

    print(f"총 {len(channels)}개 채널 중 {len(pending_channels)}개 수집 대기\n")

    for i, ch in enumerate(pending_channels, 1):
        cid = ch["channel_id"]
        cname = ch["channel_name"]
        subscribers = ch.get("subscriber_count", 0)

        print(f"  [{i}/{len(pending_channels)}] {cname} (구독자 {subscribers:,})")

        # 채널 영상 수집
        videos = scrape_channel_videos(cid)
        if not videos:
            print(f"    → 영상 없음, 스킵")
            continue

        # 채널 평균 조회수 계산
        total_views = sum(v["view_count"] for v in videos)
        channel_avg_views = total_views / len(videos) if videos else 0

        # 원투 키워드 필터 + 알고리즘 히트 판별
        wontoo_count = 0
        hit_count = 0

        for v in videos:
            is_wontoo = is_wontoo_video(v["title"])
            hit, tier, ratio = is_algorithm_hit(v["view_count"], channel_avg_views, subscribers)

            if is_wontoo or hit:
                category = "원투낚시" if is_wontoo else "기타 낚시"
                video_data = {
                    "video_id": v["video_id"],
                    "channel_id": cid,
                    "channel_name": cname,
                    "title": v["title"],
                    "view_count": v["view_count"],
                    "subscriber_count": subscribers,
                    "channel_avg_views": round(channel_avg_views),
                    "duration": v["duration"],
                    "upload_date": v.get("upload_date"),
                    "is_algorithm_hit": hit,
                    "hit_tier": tier,
                    "hit_ratio": round(ratio, 2),
                    "category": category,
                    "subtitle_status": "pending",
                    "analysis_status": "pending",
                }
                all_videos.append(video_data)
                if is_wontoo:
                    wontoo_count += 1
                if hit:
                    hit_count += 1

        print(f"    → {len(videos)}개 영상, 원투 {wontoo_count}개, 히트 {hit_count}개")

        # 10채널마다 중간 저장 (재개 안전성)
        if i % 10 == 0:
            VIDEOS_FILE.write_text(json.dumps(all_videos, ensure_ascii=False, indent=2))
            print(f"    💾 중간 저장 ({len(all_videos)}개 영상)")

    # 히트 영상 정렬 (조회수 내림차순)
    all_videos.sort(key=lambda x: x["view_count"], reverse=True)

    # 저장
    VIDEOS_FILE.write_text(json.dumps(all_videos, ensure_ascii=False, indent=2))

    total_hits = sum(1 for v in all_videos if v["is_algorithm_hit"])
    wontoo_hits = sum(1 for v in all_videos if v["is_algorithm_hit"] and v["category"] == "원투낚시")

    print(f"\n{'='*40}")
    print(f"총 수집: {len(all_videos)}개 영상")
    print(f"알고리즘 히트: {total_hits}개")
    print(f"  └ 원투낚시 히트: {wontoo_hits}개")
    print(f"  └ 기타 낚시 히트: {total_hits - wontoo_hits}개")
    print(f"✅ 저장: {VIDEOS_FILE}")


if __name__ == "__main__":
    main()

"""01. 채널 발굴 — yt-dlp ytsearch + YouTube API 구독자수 조회"""

import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"

KEYWORDS = [
    # 일본 원투낚시 특화
    "投げ釣り", "投げ釣り 大物", "投げ釣り 仕掛け",
    "サーフフィッシング",
    "ぶっこみ釣り", "ぶっこみ釣り 大物",
    "遠投カゴ釣り", "遠投 釣り",
    "投げ釣り マダイ", "投げ釣り カレイ", "投げ釣り キス",
    # 일본 바다낚시 전반
    "海釣り 大物", "堤防釣り", "磯釣り",
]

MAX_CHANNELS = 80
MIN_SUBSCRIBERS = 1000

# 시드 채널 — 반드시 포함 (필터 무관)
SEED_CHANNELS = []


def search_channels_by_keyword(keyword: str, max_results: int = 50) -> list[dict]:
    """yt-dlp ytsearch로 키워드 검색 → 채널 정보 추출"""
    cmd = [
        "yt-dlp", "--flat-playlist", "--dump-json",
        "--no-warnings", "--quiet",
        f"ytsearch{max_results}:{keyword}",
    ]
    results = []
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        for line in proc.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                entry = json.loads(line)
                channel_id = entry.get("channel_id")
                channel_name = entry.get("channel") or entry.get("uploader")
                if channel_id and channel_name:
                    results.append({
                        "channel_id": channel_id,
                        "channel_name": channel_name,
                    })
            except json.JSONDecodeError:
                continue
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ 타임아웃: {keyword}")
    except Exception as e:
        print(f"  ⚠️ 오류: {keyword} — {e}")
    return results


def batch_get_subscribers(channel_ids: list[str]) -> dict[str, int]:
    """YouTube API channels.list 배치 조회 (50개씩)"""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key or api_key == "your_youtube_api_key_here":
        print("⚠️ YOUTUBE_API_KEY 미설정 — 구독자수 조회 생략 (전체 채널 포함)")
        return {}

    youtube = build("youtube", "v3", developerKey=api_key)
    subscribers = {}

    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i + 50]
        try:
            response = youtube.channels().list(
                part="statistics",
                id=",".join(batch),
            ).execute()
            for item in response.get("items", []):
                cid = item["id"]
                stats = item.get("statistics", {})
                sub_count = int(stats.get("subscriberCount", 0))
                subscribers[cid] = sub_count
        except Exception as e:
            print(f"  ⚠️ YouTube API 오류: {e}")

    return subscribers


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 재개 지원: 이미 완료된 경우 스킵
    if CHANNELS_FILE.exists():
        existing = json.loads(CHANNELS_FILE.read_text())
        if existing:
            print(f"✅ 이미 완료됨: {len(existing)}개 채널 (data/channels.json)")
            return

    # Step 0: 시드 채널 등록
    channel_map: dict[str, dict] = {}  # channel_id → info
    for seed in SEED_CHANNELS:
        channel_map[seed["channel_id"]] = {
            "channel_id": seed["channel_id"],
            "channel_name": seed["channel_name"],
            "discovered_via": {"시드 채널"},
            "is_seed": True,
        }
    print(f"시드 채널: {len(SEED_CHANNELS)}개 등록\n")

    # Step 1: 키워드별 검색
    for i, keyword in enumerate(KEYWORDS, 1):
        print(f"  [{i}/{len(KEYWORDS)}] 검색: {keyword}")
        results = search_channels_by_keyword(keyword)
        for ch in results:
            cid = ch["channel_id"]
            if cid in channel_map:
                channel_map[cid]["discovered_via"].add(keyword)
            else:
                channel_map[cid] = {
                    "channel_id": cid,
                    "channel_name": ch["channel_name"],
                    "discovered_via": {keyword},
                }
        print(f"    → {len(results)}개 영상에서 채널 추출 (누적 {len(channel_map)}개)")

    print(f"\n총 고유 채널: {len(channel_map)}개")

    # Step 2: 구독자수 배치 조회
    channel_ids = list(channel_map.keys())
    print(f"구독자수 조회 중... ({len(channel_ids)}개)")
    subscribers = batch_get_subscribers(channel_ids)

    # Step 3: 필터링 + 정렬
    channels = []
    for cid, info in channel_map.items():
        sub_count = subscribers.get(cid, 0)
        info["subscriber_count"] = sub_count
        info["discovered_via"] = sorted(info["discovered_via"])
        info["status"] = "pending"

        # 시드 채널은 무조건 포함
        if info.get("is_seed"):
            channels.append(info)
        # 구독자수 API 미사용 시 전체 포함, 사용 시 1000+ 필터
        elif not subscribers or sub_count >= MIN_SUBSCRIBERS:
            channels.append(info)

    # 시드 채널 분리 → 나머지 구독자 순 정렬 → 상위 80개
    seed_channels = [ch for ch in channels if ch.get("is_seed")]
    other_channels = [ch for ch in channels if not ch.get("is_seed")]
    other_channels.sort(key=lambda x: x["subscriber_count"], reverse=True)
    remaining = MAX_CHANNELS - len(seed_channels)
    channels = seed_channels + other_channels[:remaining]

    print(f"필터 후 채널: {len(channels)}개 (구독자 {MIN_SUBSCRIBERS}+, 상한 {MAX_CHANNELS})")

    # 저장
    CHANNELS_FILE.write_text(json.dumps(channels, ensure_ascii=False, indent=2))
    print(f"✅ 저장: {CHANNELS_FILE} ({len(channels)}개 채널)")


if __name__ == "__main__":
    main()

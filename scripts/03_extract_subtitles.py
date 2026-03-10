"""03. 자막 + 썸네일 추출 — transcript-api (쿠키 인증)"""

import json
import os
import random
import sys
import time
import urllib.request
from pathlib import Path

import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
VIDEOS_FILE = DATA_DIR / "videos.json"
SUBTITLES_DIR = DATA_DIR / "subtitles"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"

REQUEST_DELAY = (4, 6)  # 요청 간 랜덤 딜레이 범위(초)
BATCH_PAUSE_EVERY = 50  # N개마다 추가 대기
BATCH_PAUSE_SEC = 10  # 배치 대기 시간(초)
IP_BLOCK_THRESHOLD = 5  # 연속 실패 N회 시 IP차단 간주하고 중단

YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES", "")


def _build_ytt() -> YouTubeTranscriptApi:
    """쿠키 인증된 YouTubeTranscriptApi 인스턴스 생성"""
    if YOUTUBE_COOKIES:
        session = requests.Session()
        for pair in YOUTUBE_COOKIES.split("; "):
            if "=" in pair:
                k, v = pair.split("=", 1)
                session.cookies.set(k, v, domain=".youtube.com")
        return YouTubeTranscriptApi(http_client=session)
    return YouTubeTranscriptApi()


_ytt_instance = _build_ytt()


class IpBlockedError(Exception):
    pass


def extract_with_transcript_api(video_id: str) -> str | None:
    """youtube-transcript-api v1.x (쿠키 인증). IP차단 시 IpBlockedError 발생."""
    try:
        ytt = _ytt_instance
        transcript_list = ytt.list(video_id)

        transcript = None
        for lang_codes in [["ja"], ["ko"], ["en"], None]:
            try:
                if lang_codes:
                    transcript = transcript_list.find_transcript(lang_codes)
                else:
                    for t in transcript_list:
                        transcript = t
                        break
                if transcript:
                    break
            except Exception:
                continue

        if transcript is None:
            return None

        data = transcript.fetch()
        full_text = " ".join([seg.text for seg in data.snippets])
        return full_text if full_text.strip() else None

    except Exception as e:
        err_name = type(e).__name__
        if "IpBlocked" in err_name or "IpBlocked" in str(e):
            raise IpBlockedError(f"IP 차단 감지: {e}")
        return None


def download_thumbnail(video_id: str) -> bool:
    """YouTube 썸네일 다운로드 (maxres > hq > mq)"""
    thumb_file = THUMBNAILS_DIR / f"{video_id}.jpg"
    if thumb_file.exists() and thumb_file.stat().st_size > 1000:
        return True

    for quality in ["maxresdefault", "hqdefault", "mqdefault"]:
        url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
        try:
            urllib.request.urlretrieve(url, thumb_file)
            if thumb_file.stat().st_size > 1000:
                return True
        except Exception:
            continue

    return False


def main():
    if not VIDEOS_FILE.exists():
        print("❌ data/videos.json 없음 — 02_collect_videos.py 먼저 실행하세요")
        sys.exit(1)

    SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

    videos = json.loads(VIDEOS_FILE.read_text())

    HIT_QUEUE = DATA_DIR / "hit_analysis_queue.json"
    if HIT_QUEUE.exists():
        hit_videos = json.loads(HIT_QUEUE.read_text())
    else:
        hit_videos = [v for v in videos if v.get("is_algorithm_hit")]
    print(f"자막+썸네일 추출 대상: {len(hit_videos)}개 히트 영상\n")

    sub_success = 0
    sub_fail = 0
    sub_skip = 0
    consecutive_fail = 0
    thumb_success = 0
    thumb_fail = 0
    last_batch_milestone = 0

    for i, video in enumerate(hit_videos, 1):
        vid = video["video_id"]
        title = video["title"]

        subtitle_file = SUBTITLES_DIR / f"{vid}.txt"
        if subtitle_file.exists() and subtitle_file.stat().st_size > 0:
            sub_skip += 1
        else:
            print(f"  [{i}/{len(hit_videos)}] {title[:50]}...")

            try:
                text = extract_with_transcript_api(vid)
            except IpBlockedError as e:
                print(f"    🚫 {e}")
                print(f"    ⛔ IP 차단! 지금까지 성공: {sub_success}, 실패: {sub_fail}, 스킵: {sub_skip}")
                print(f"    → 아이피 변경 후 다시 실행하세요.")
                break

            if text:
                subtitle_file.write_text(text, encoding="utf-8")
                video["subtitle_status"] = "ok (transcript-api)"
                sub_success += 1
                consecutive_fail = 0
                print(f"    ✅ 자막: transcript-api ({len(text)}자)")
            else:
                # 마커 파일 생성 → 다음 실행 시 스킵
                subtitle_file.write_text("NO_SUBTITLE", encoding="utf-8")
                video["subtitle_status"] = "no_subtitle"
                sub_fail += 1
                consecutive_fail += 1
                print(f"    ❌ 자막 없음 (스킵 마킹)")

                if consecutive_fail >= IP_BLOCK_THRESHOLD:
                    print(f"    ⛔ 연속 {consecutive_fail}회 실패 — IP 차단 의심!")
                    print(f"    → 아이피 변경 후 다시 실행하세요.")
                    break

            # 요청 간 랜덤 딜레이
            time.sleep(random.uniform(*REQUEST_DELAY))

            # N개마다 추가 대기 (마일스톤 방식으로 중복 방지)
            milestone = sub_success // BATCH_PAUSE_EVERY
            if milestone > last_batch_milestone:
                last_batch_milestone = milestone
                print(f"    ⏸️  {BATCH_PAUSE_SEC}초 배치 대기...")
                time.sleep(BATCH_PAUSE_SEC)

        # 썸네일 다운로드
        thumb_file = THUMBNAILS_DIR / f"{vid}.jpg"
        if not thumb_file.exists() or thumb_file.stat().st_size < 1000:
            if download_thumbnail(vid):
                thumb_success += 1
            else:
                thumb_fail += 1

        # 50개마다 중간 저장
        if i % 50 == 0:
            VIDEOS_FILE.write_text(json.dumps(videos, ensure_ascii=False, indent=2))
            print(f"    💾 중간 저장 ({sub_success}개 자막 성공)")

    # 최종 저장
    VIDEOS_FILE.write_text(json.dumps(videos, ensure_ascii=False, indent=2))

    print(f"\n{'='*40}")
    print(f"자막 추출: 성공 {sub_success} / 실패 {sub_fail} / 스킵 {sub_skip}")
    print(f"썸네일: 새로 {thumb_success} / 실패 {thumb_fail}")
    print(f"✅ 저장: {SUBTITLES_DIR}/ + {THUMBNAILS_DIR}/")


if __name__ == "__main__":
    main()

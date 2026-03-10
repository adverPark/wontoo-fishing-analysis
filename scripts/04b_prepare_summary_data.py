"""04b. 사전 집계 스크립트 — 72개 분석 JSON + videos.json → pre_aggregated.json

일본어를 한국어로 번역하고, 정량 집계를 수행하여
strategy-advisor 에이전트가 바로 소비할 수 있는 데이터를 만든다.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
VIDEOS_FILE = DATA_DIR / "videos.json"
ANALYSIS_DIR = DATA_DIR / "analysis"
OUTPUT_FILE = ANALYSIS_DIR / "pre_aggregated.json"

# ── 일한 번역 사전 ──────────────────────────────────────────────

FISH_JA_TO_KO = {
    # 도미류
    "真鯛": "참돔", "マダイ": "참돔", "まだい": "참돔",
    "チヌ": "감성돔", "クロダイ": "감성돔", "黒鯛": "감성돔",
    "ヘダイ": "황돔", "石鯛": "돌돔", "イシダイ": "돌돔",
    "メジナ": "벵에돔", "グレ": "벵에돔",
    # 광어/넙치류
    "ヒラメ": "넙치", "平目": "넙치",
    "カレイ": "가자미", "鰈": "가자미",
    "マコガレイ": "참가자미",
    # 농어/방어류
    "シーバス": "농어", "スズキ": "농어", "鱸": "농어",
    "ブリ": "방어", "鰤": "방어",
    "ワラサ": "부시리", "カンパチ": "잿방어", "間八": "잿방어",
    "ヒラマサ": "부시리",
    # 참치/가다랑어류
    "キハダ": "황다랑어", "キハダマグロ": "황다랑어",
    "カツオ": "가다랑어", "鰹": "가다랑어",
    "メジ": "눈다랑어",
    # 보리멸/모래무지류
    "キス": "보리멸", "シロギス": "보리멸", "鱚": "보리멸",
    # 전갱이류
    "アジ": "전갱이", "鯵": "전갱이", "マアジ": "참전갱이",
    # 고등어류
    "サバ": "고등어", "鯖": "고등어",
    # 쥐치류
    "カワハギ": "쥐치", "ウマヅラハギ": "말쥐치",
    # 볼락류
    "メバル": "볼락", "カサゴ": "쏨뱅이", "ガシラ": "쏨뱅이",
    "ソイ": "조피볼락",
    # 연어/송어류
    "サケ": "연어", "鮭": "연어", "サーモン": "연어",
    "イワナ": "산천어", "岩魚": "산천어",
    "ヤマメ": "산천어", "アマゴ": "은어",
    "ニジマス": "무지개송어",
    # 다금바리/대형어
    "クエ": "다금바리", "九絵": "다금바리",
    "ハタ": "다금바리류",
    "アカハタ": "붉바리", "オオモンハタ": "대문바리",
    "キジハタ": "능성어",
    # 문어/오징어
    "タコ": "문어", "蛸": "문어",
    "イカ": "오징어", "アオリイカ": "무늬오징어", "ヤリイカ": "살오징어",
    "コウイカ": "갑오징어",
    # 기타 인기어종
    "タチウオ": "갈치", "太刀魚": "갈치",
    "アイナメ": "노래미", "쥐노래미": "쥐노래미",
    "ハゼ": "망둑어",
    "ウナギ": "뱀장어", "鰻": "뱀장어",
    "アナゴ": "붕장어",
    "フグ": "복어", "河豚": "복어",
    "コチ": "양태",
    "マゴチ": "양태",
    "ベラ": "놀래미",
    "スズメダイ": "자리돔",
    "サヨリ": "학꽁치",
    "ナマズ": "메기",
    "コイ": "잉어", "鯉": "잉어",
    "ヘラブナ": "떡붕어",
    "ライギョ": "가물치",
    "ブラックバス": "배스",
    "鱒レンジャー": "마스 렌저(저가 낚싯대)",
}

FISHING_TERMS_JA_TO_KO = {
    # 낚시법
    "ぶっこみ釣り": "던질낚시",
    "ぶっこみ": "던질낚시",
    "投げ釣り": "원투낚시",
    "遠投カゴ": "원투카고",
    "カゴ釣り": "카고낚시",
    "サビキ釣り": "사비키낚시",
    "サビキ": "사비키",
    "フカセ釣り": "흘림낚시",
    "フカセ": "흘림낚시",
    "泳がせ釣り": "활미끼낚시",
    "泳がせ": "활미끼낚시",
    "ショアジギング": "쇼어지깅",
    "ショアジギ": "쇼어지깅",
    "ライトショアジギング": "라이트쇼어지깅",
    "エギング": "에깅",
    "メバリング": "볼락루어",
    "アジング": "아징",
    "ルアー釣り": "루어낚시",
    "ルアー": "루어",
    "ジグ": "지그",
    "ワーム": "웜",
    "穴釣り": "구멍낚시",
    "釣り": "낚시",
    "オカマ釣り": "오카마낚시",
    # 장소
    "堤防釣り": "방파제낚시",
    "堤防": "방파제",
    "サーフ": "서프",
    "磯釣り": "갯바위낚시",
    "磯": "갯바위",
    "渓流釣り": "계류낚시",
    "渓流": "계류",
    "船釣り": "선상낚시",
    "オフショア": "오프쇼어",
    "港": "항구",
    "漁港": "어항",
    "防波堤": "방파제",
    "源流": "원류",
    "離島": "이도(외딴섬)",
    "無人島": "무인도",
    "秘境": "비경",
    "渡船": "도선(건넘배)",
    "筏": "이카다(뗏목)",
    "桟橋": "잔교",
    "露天風呂": "노천온천",
    "旅館": "료칸(여관)",
    "部屋": "방",
    "家": "집",
    # 장비/용품
    "ダイソー": "다이소",
    "100均": "100엔숍",
    "仕掛け": "채비",
    "リール": "릴",
    "ロッド": "낚싯대",
    "竿": "낚싯대",
    "餌": "미끼",
    "エサ": "미끼",
    "ケミホタル": "케미라이트",
    "電気ウキ": "전기찌",
    "ウキ": "찌",
    "テンヤ": "텐야",
    "タイラバ": "타이라바",
    "ミサイル": "미사일(카고)",
    "カゴ": "카고",
    "釣り具": "낚시용품",
    "釣り具屋": "낚시점",
    # 미끼
    "業務スーパー": "업무용 슈퍼(대형마트)",
    "スーパー": "슈퍼(마트)",
    "生エビ": "생새우",
    "白エビ": "흰새우",
    "活き": "살아있는",
    "アサリ": "아사리(바지락)",
    "イワシ": "정어리",
    "生蝉": "살아있는 매미",
    # 낚시 용어
    "アタリ": "어신(입질)",
    "入れ食い": "입질 폭발",
    "連発": "연발",
    "釣果": "조과",
    "大物": "대물",
    "巨大": "거대",
    "怪物": "괴물",
    "化物": "괴물",
    "化け物": "괴물",
    "青物": "부시리류",
    "高級魚": "고급어종",
    "デカバス": "대형배스",
    "ビッグフィッシュ": "빅피쉬",
    "バトル": "배틀",
    "モンスター": "몬스터",
    # 감정/표현
    "衝撃": "충격",
    "前代未聞": "전대미문",
    "大騒動": "대소동",
    "騒然": "소동",
    "ビビった": "깜짝 놀랐다",
    "楽しすぎた": "너무 재미있었다",
    "ボコボコ": "마구잡이",
    "マジで": "진짜",
    "とんでもない": "엄청난",
    "珍事": "진기한 일",
    "奇跡": "기적",
    "歴史的瞬間": "역사적 순간",
    "本当は教えたくない": "사실 알려주고 싶지 않은",
    "確実に": "확실하게",
    "助けて": "도와줘",
    "怖い": "무서운",
    "理不尽": "이불합리한",
    # 교육
    "初心者": "초보자",
    "入門": "입문",
    "超入門": "초입문",
    "極意": "극의(비법)",
    "徹底解説": "철저 해설",
    "最強": "최강",
    "テクニック": "테크닉",
    "ギミック": "기믹",
    "公式": "공식",
    "チャンネル": "채널",
    "直伝": "직전",
    "地元漁師": "현지 어부",
    "親分": "보스",
    # 시즌/자연
    "真冬": "한겨울",
    "夏": "여름",
    "春": "봄",
    "秋": "가을",
    "冬": "겨울",
    "滝": "폭포",
    "大直瀑": "대직폭",
    "ダム": "댐",
    "川": "강",
    "湖": "호수",
    "海": "바다",
    "島": "섬",
    "谷": "골짜기",
    "山": "산",
    # 일반
    "日本": "일본",
    "日本最大級": "일본 최대급",
    "国内最大級": "일본 국내 최대급",
    "店員": "점원",
    "毎週配信": "매주 송출",
    "挑戦": "도전",
    "何匹": "몇 마리",
    "釣れる": "잡히는",
    "釣れます": "잡힙니다",
    "連発させる": "연발시키는",
    "技": "기술",
    "教えます": "가르쳐 드립니다",
    "尾": "마리",
    "瞬間": "순간",
    "対面": "대면",
    "王様": "왕",
    "度": "번",
    "水系": "수계",
    "素人": "초보",
    "始める": "시작하다",
    "長くなる": "길어지는",
    "目指す": "목표하는",
    "落としたら": "떨어뜨리면",
    "遭いました": "당했습니다",
    "追いかけられ": "쫓기고",
    "遭遇": "조우",
    "熊撃退スプレー": "곰퇴치 스프레이",
    "手にしたが": "손에 쥐었지만",
    "集まる": "모이는",
    "魚": "물고기",
    "全部": "전부",
    "市役所": "시청",
    "ブランド": "브랜드",
    "潮": "조류",
    "大量発生中": "대량 발생 중",
    "状態": "상태",
    "仕留める": "잡아내다",
    "誰でも": "누구나",
    "淡水用": "민물용",
    "漁師達": "어부들",
    "漁師": "어부",
    "閉ざされた": "닫힌",
    "居ない": "없는",
    "前": "앞",
    "食らいつく": "물어뜯는",
    "思わず": "자기도 모르게",
    "超えた": "넘어선",
    "起きない": "일어나지 않는",
    "釣り上げた": "낚아올린",
    "プライベート": "프라이빗",
    "付き": "포함",
    "釣り放題": "낚시 무제한",
    "してきた": "하고 왔다",
    "ルーキ": "루키",
    "実釣": "실제 낚시",
    "両ダンゴ": "양단고",
    "チョーチン": "초우칭",
    "フィッシングライフ": "피싱 라이프",
    "釣りキャンプ": "낚시 캠핑",
    "凸": "돌격",
    "センター": "센터",
    "県": "현",
    "郡": "군",
    "区": "구",
    "町": "정(마을)",
    "公園": "공원",
    "たち": "들",
}

# 한자(CJK Unified Ideographs) + 히라가나 + 가타카나 감지 패턴
_JA_PATTERN = re.compile(
    r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uF900-\uFAFF]+"
)

# ── 소재 카테고리 분류 키워드 ──────────────────────────────────
IDEA_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "가성비_도전": ["가성비", "다이소", "100엔", "마트", "저렴", "편의점", "균일가",
                    "도전", "vs", "대결", "비교", "검증", "실험", "테스트", "몇 마리"],
    "장비_기어": ["장비", "채비", "릴", "낚싯대", "로드", "세팅", "추천", "리뷰",
                  "빌딩", "커스텀", "튜닝", "봉돌", "텐야", "타이라바", "지그",
                  "웜", "카고", "찌", "미사일"],
    "장소_탐험": ["무인도", "비경", "원류", "탐험", "섬", "펜션", "숙소", "항구",
                  "방파제", "포인트", "여행", "캠핑", "캠프", "서프", "계류"],
    "교육": ["입문", "가이드", "레슨", "비법", "해설", "강의", "교육", "튜토리얼",
             "기초", "마스터", "완전정복", "총정리"],
    "어종특화": ["참돔", "감성돔", "농어", "광어", "보리멸", "전갱이", "볼락",
                "쏨뱅이", "다금바리", "갈치", "연어", "부시리", "가자미", "문어",
                "오징어", "놀래미", "떡붕어", "붕장어", "넙치"],
    "초보자": ["초보", "입문", "처음", "시작", "쉬운", "간단", "아이", "가족",
              "어린이", "뉴비"],
    "시즌": ["봄", "여름", "가을", "겨울", "시즌", "개막", "한겨울", "초봄",
            "초여름"],
}

# ── 바이럴 메커니즘 키워드 매핑 ──────────────────────────────────
VIRAL_MECHANISM_KEYWORDS: dict[str, list[str]] = {
    "의외성 — 기대를 뒤집는 반전": [
        "의외", "반전", "예상", "역발상", "놀라", "뜻밖", "예상치",
        "평범", "일상", "흔한", "저렴", "대물", "뒤집"],
    "교육가치 — 검색되는 에버그린": [
        "교육", "해설", "가이드", "입문", "비법", "레슨", "강의",
        "정보", "검색", "완전", "총정리", "에버그린", "교재", "교과서"],
    "감정연결 — 공감과 감동": [
        "감동", "공감", "재미", "즐거", "행복", "교감", "웃음",
        "힐링", "따뜻", "눈물", "기뻐", "즐겁"],
    "서스펜스 — 결과가 궁금한 구조": [
        "서스펜스", "클리프", "궁금", "결말", "미공개", "긴장",
        "기대", "스릴", "결과", "어떻게", "무엇이"],
    "접근성 — 누구나 할 수 있는": [
        "가성비", "다이소", "마트", "저렴", "누구나", "쉬운",
        "간단", "초보", "입문자", "접근"],
    "전문성 — 프로의 권위": [
        "프로", "전문", "최강", "공식", "브랜드", "검증",
        "프리미엄", "메이커", "고급", "권위"],
    "시각충격 — 압도적 비주얼": [
        "드론", "항공", "수중", "대물", "거대", "괴물", "몬스터",
        "충격", "임팩트", "압도", "스케일", "비주얼"],
    "크로스오버 — 다른 장르와 결합": [
        "캠핑", "여행", "요리", "숙소", "펜션", "동물", "고양이",
        "숙박", "캠프", "가족", "크로스"],
    "기록도전 — 한계에 도전": [
        "도전", "대결", "배틀", "기록", "최초", "역사", "극한",
        "한계", "신기록", "챌린지"],
}

# ── 한국 원투낚시 시즌 어종 매핑 (월별) ──────────────────────────
FISH_SEASON_MONTHS: dict[str, list[int]] = {
    "도다리": [3, 4, 5],
    "보리멸": [5, 6, 7, 8, 9],
    "감성돔": [9, 10, 11, 12, 1],
    "가자미": [11, 12, 1, 2],
    "볼락": [12, 1, 2, 3],
    "농어": [6, 7, 8, 9, 10],
    "참돔": [4, 5, 6, 7, 8, 9],
    "광어": [3, 4, 5, 10, 11, 12],
    "넙치": [3, 4, 5, 10, 11, 12],
    "전갱이": [5, 6, 7, 8, 9, 10],
    "고등어": [9, 10, 11],
    "쥐치": [10, 11],
    "쏨뱅이": [11, 12, 1, 2, 3],
    "붕장어": [6, 7, 8, 9],
    "놀래미": [3, 4, 5, 10, 11],
    "연어": [9, 10, 11],
    "부시리": [6, 7, 8, 9, 10],
    "다금바리": [6, 7, 8, 9, 10],
    "갈치": [8, 9, 10, 11],
    "오징어": [8, 9, 10, 11],
    "문어": [6, 7, 8, 9],
    "잉어": [4, 5, 6],
    "떡붕어": [3, 4, 5, 6, 7, 8, 9],
    "산천어": [3, 4, 5, 6, 7, 8, 9],
    "무지개송어": [3, 4, 5, 10, 11],
    "숭어": [1, 2, 11, 12],
    "학꽁치": [3, 4, 10, 11],
    "돌돔": [6, 7, 8, 9],
    "벵에돔": [5, 6, 7, 8, 9],
    "뱀장어": [5, 6, 7, 8],
    "복어": [10, 11, 12, 1, 2],
    "양태": [6, 7, 8, 9],
}

MONTH_NAMES = ["1월", "2월", "3월", "4월", "5월", "6월",
               "7월", "8월", "9월", "10월", "11월", "12월"]
SEASON_NAMES = {
    1: "한겨울", 2: "늦겨울", 3: "초봄", 4: "봄", 5: "늦봄",
    6: "초여름", 7: "여름", 8: "한여름", 9: "초가을", 10: "가을",
    11: "늦가을", 12: "초겨울",
}


def translate_ja_to_ko(text: str) -> str:
    """일본어 어종명/낚시 용어를 한국어로 치환한다."""
    if not text:
        return text

    # 긴 키부터 치환 (부분 매칭 방지)
    all_dict = {**FISH_JA_TO_KO, **FISHING_TERMS_JA_TO_KO}
    for ja, ko in sorted(all_dict.items(), key=lambda x: len(x[0]), reverse=True):
        text = text.replace(ja, ko)

    return text


def strip_remaining_japanese(text: str) -> str:
    """번역 후에도 남은 일본어 문자를 제거한다.

    괄호 안의 일본어도 함께 제거하고, 불필요한 공백을 정리한다.
    """
    if not text:
        return text
    # 괄호 안 일본어 제거: (日本語), （日本語）
    text = re.sub(r"[（(][^)）]*[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uF900-\uFAFF]+[^)）]*[)）]", "", text)
    # 남은 일본어 문자 제거
    text = _JA_PATTERN.sub("", text)
    # 정리: 연속 공백, 앞뒤 공백, 빈 괄호 등
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"（\s*）", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s*[,、]\s*[,、]\s*", ", ", text)
    text = text.strip(" ,、・")
    return text


def clean_deep(obj):
    """재귀적으로 모든 문자열에서 잔여 일본어를 제거."""
    if isinstance(obj, str):
        return strip_remaining_japanese(obj)
    elif isinstance(obj, list):
        return [clean_deep(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: clean_deep(v) for k, v in obj.items()}
    return obj


def has_japanese(text: str) -> bool:
    """히라가나/가타카나/한자가 남아있는지 확인."""
    if not text:
        return False
    return bool(_JA_PATTERN.search(text))


def translate_deep(obj):
    """재귀적으로 모든 문자열에 일한 번역 적용."""
    if isinstance(obj, str):
        return translate_ja_to_ko(obj)
    elif isinstance(obj, list):
        return [translate_deep(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: translate_deep(v) for k, v in obj.items()}
    return obj


def categorize_idea(idea_text: str) -> str:
    """소재 아이디어를 카테고리로 분류."""
    if not idea_text:
        return "기타"
    scores: dict[str, int] = {}
    for category, keywords in IDEA_CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in idea_text)
        if score > 0:
            scores[category] = score
    if not scores:
        return "기타"
    return max(scores, key=scores.get)


def classify_viral_mechanism(why_viral: str) -> str:
    """바이럴 이유를 메커니즘으로 분류."""
    if not why_viral:
        return "기타"
    scores: dict[str, int] = {}
    for mechanism, keywords in VIRAL_MECHANISM_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in why_viral)
        if score > 0:
            scores[mechanism] = score
    if not scores:
        return "기타"
    return max(scores, key=scores.get)


def build_season_calendar() -> list[dict]:
    """월별 시즌 캘린더 생성 (어종+시즌 정보)."""
    calendar = []
    for month in range(1, 13):
        fish_list = [
            fish for fish, months in FISH_SEASON_MONTHS.items()
            if month in months
        ]
        calendar.append({
            "month": MONTH_NAMES[month - 1],
            "season": SEASON_NAMES[month],
            "target_fish": fish_list,
        })
    return calendar


def load_videos() -> list[dict]:
    return json.loads(VIDEOS_FILE.read_text()) if VIDEOS_FILE.exists() else []


def load_analyses() -> dict[str, dict]:
    """analysis/{video_id}.json 파일 전부 로드 (summary.json 제외)."""
    result = {}
    for f in ANALYSIS_DIR.glob("*.json"):
        if f.name == "summary.json" or f.name == "pre_aggregated.json":
            continue
        vid = f.stem
        try:
            result[vid] = json.loads(f.read_text())
        except json.JSONDecodeError:
            print(f"⚠️ JSON 파싱 실패: {f}")
    return result


def extract_fish_species(text: str) -> list[str]:
    """fish_species 문자열에서 개별 어종 추출."""
    if not text:
        return []
    species = []
    for part in re.split(r"[,/、・\s]+", text):
        part = part.strip()
        if part and len(part) > 1:
            species.append(part)
    return species


def build_compact_video(vid: str, analysis: dict, videos_map: dict) -> dict:
    """영상별 compact 데이터 생성."""
    v = videos_map.get(vid, {})
    ss = analysis.get("success_score", {})
    af = analysis.get("algorithm_factors", {})
    fi = analysis.get("fishing_info", {})
    ta = analysis.get("title_analysis", {})
    seeds = analysis.get("content_idea_seeds", [])

    # 어종 한국어 변환
    fish_raw = fi.get("fish_species", "")
    fish_ko = translate_ja_to_ko(fish_raw)
    fish_list = extract_fish_species(fish_ko)

    # 최고 소재 아이디어 (첫 번째)
    best_idea = ""
    if seeds:
        first = seeds[0]
        if isinstance(first, dict):
            best_idea = translate_ja_to_ko(first.get("idea", ""))
        else:
            best_idea = translate_ja_to_ko(str(first))

    return {
        "video_id": vid,
        "title_ko": translate_ja_to_ko(v.get("title", "")),
        "channel": translate_ja_to_ko(v.get("channel_name", "")),
        "views": v.get("view_count", 0),
        "hit_ratio": v.get("hit_ratio", 0),
        "subscriber_count": v.get("subscriber_count", 0),
        "duration": v.get("duration", 0),
        "category": v.get("category", ""),
        "primary_factor": ss.get("primary_factor", ""),
        "overall_score": ss.get("overall", 0),
        "title_score": ss.get("title_score", 0),
        "thumbnail_score": ss.get("thumbnail_score", 0),
        "content_score": ss.get("content_score", 0),
        "timing_score": ss.get("timing_score", 0),
        "one_line_hit_reason": translate_ja_to_ko(af.get("why_viral", "")),
        "fish_species": fish_list,
        "location_type": translate_ja_to_ko(fi.get("location", "")),
        "bait": translate_ja_to_ko(fi.get("bait", "")),
        "rig": translate_ja_to_ko(fi.get("rig", "")),
        "content_style": translate_ja_to_ko(
            analysis.get("content_structure", {}).get("storytelling", "")
        ),
        "best_idea_seed": best_idea,
        "hook_type": translate_ja_to_ko(ta.get("hook_type", "")),
        "formula": translate_ja_to_ko(ta.get("formula", "")),
        "verdict": translate_ja_to_ko(ss.get("verdict", "")),
    }


def aggregate(analyses: dict[str, dict], videos: list[dict]) -> dict:
    """정량 집계 + 정성 텍스트 모음."""
    videos_map = {v["video_id"]: v for v in videos}

    # ── compact 영상 데이터 ──
    compacts = []
    for vid, analysis in sorted(analyses.items()):
        compacts.append(build_compact_video(vid, analysis, videos_map))

    # ── 정량 집계 ──
    factor_counter = Counter()
    fish_counter = Counter()
    location_counter = Counter()
    score_sums = {"title": 0, "thumbnail": 0, "content": 0, "timing": 0, "overall": 0}
    total = len(compacts)

    for c in compacts:
        if c["primary_factor"]:
            factor_counter[c["primary_factor"]] += 1
        for fish in c["fish_species"]:
            fish_counter[fish] += 1
        if c["location_type"]:
            location_counter[c["location_type"]] += 1
        score_sums["title"] += c["title_score"]
        score_sums["thumbnail"] += c["thumbnail_score"]
        score_sums["content"] += c["content_score"]
        score_sums["timing"] += c["timing_score"]
        score_sums["overall"] += c["overall_score"]

    score_avgs = {k: round(v / max(total, 1), 1) for k, v in score_sums.items()}

    # ── 정성 텍스트 모음 (번역 완료) ──
    why_viral_list = []
    idea_seeds_list = []
    formula_list = []

    for vid, analysis in sorted(analyses.items()):
        af = analysis.get("algorithm_factors", {})
        why = translate_ja_to_ko(af.get("why_viral", ""))
        if why:
            why_viral_list.append({"video_id": vid, "why_viral": why})

        ta = analysis.get("title_analysis", {})
        formula = translate_ja_to_ko(ta.get("formula", ""))
        if formula:
            formula_list.append({"video_id": vid, "formula": formula})

        seeds = analysis.get("content_idea_seeds", [])
        for seed in seeds:
            if isinstance(seed, dict):
                idea_seeds_list.append({
                    "video_id": vid,
                    "idea": translate_ja_to_ko(seed.get("idea", "")),
                    "why": translate_ja_to_ko(seed.get("why", "")),
                })
            else:
                idea_seeds_list.append({
                    "video_id": vid,
                    "idea": translate_ja_to_ko(str(seed)),
                    "why": "",
                })

    # ── 소재 카테고리 분류 ──
    idea_categories: dict[str, list[dict]] = {}
    for seed_item in idea_seeds_list:
        cat = categorize_idea(seed_item.get("idea", ""))
        idea_categories.setdefault(cat, []).append(seed_item)

    # ── 바이럴 메커니즘 클러스터링 ──
    viral_clusters: dict[str, list[dict]] = {}
    for viral_item in why_viral_list:
        mechanism = classify_viral_mechanism(viral_item.get("why_viral", ""))
        viral_clusters.setdefault(mechanism, []).append(viral_item)

    # ── 시즌 캘린더 (고정 매핑 기반) ──
    season_calendar = build_season_calendar()

    # ── 히트 vs 비히트 비교 데이터 ──
    hit_videos = [v for v in videos if v.get("is_algorithm_hit")]
    nothit_wontoo = [v for v in videos if not v.get("is_algorithm_hit") and v.get("category") == "원투낚시"]

    hit_durations = [v["duration"] for v in hit_videos if v.get("duration")]
    nothit_durations = [v["duration"] for v in nothit_wontoo if v.get("duration")]

    hit_avg_dur = round(sum(hit_durations) / max(len(hit_durations), 1) / 60, 1)
    nothit_avg_dur = round(sum(nothit_durations) / max(len(nothit_durations), 1) / 60, 1)

    hit_views = [v["view_count"] for v in hit_videos if v.get("view_count")]
    min_views = min(hit_views) if hit_views else 0
    max_views = max(hit_views) if hit_views else 0

    # ── 최종 출력 ──
    result = {
        "meta": {
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "total_analyzed": total,
            "total_videos": len(videos),
            "total_hit_videos": len(hit_videos),
            "total_nothit_wontoo": len(nothit_wontoo),
            "view_range": {"min": min_views, "max": max_views},
        },
        "quantitative": {
            "primary_factor_distribution": dict(factor_counter.most_common()),
            "fish_species_ranking": [
                {"species": species, "count": count}
                for species, count in fish_counter.most_common(20)
            ],
            "location_type_ranking": [
                {"location": loc, "count": count}
                for loc, count in location_counter.most_common(10)
            ],
            "score_averages": score_avgs,
            "hit_avg_duration_min": hit_avg_dur,
            "nothit_avg_duration_min": nothit_avg_dur,
        },
        "video_compacts": compacts,
        "qualitative": {
            "why_viral_reasons": why_viral_list,
            "content_idea_seeds": idea_seeds_list,
            "title_formulas": formula_list,
        },
        "pre_clustered": {
            "idea_categories": {
                cat: {"count": len(items), "items": items}
                for cat, items in sorted(idea_categories.items(),
                                         key=lambda x: len(x[1]), reverse=True)
            },
            "viral_mechanism_clusters": {
                mech: {"count": len(items), "items": items}
                for mech, items in sorted(viral_clusters.items(),
                                          key=lambda x: len(x[1]), reverse=True)
            },
            "season_calendar": season_calendar,
        },
    }

    return result


def check_remaining_japanese(data: dict) -> list[str]:
    """JSON 전체에서 남아있는 일본어 문자열을 찾는다."""
    warnings = []

    def _scan(obj, path=""):
        if isinstance(obj, str):
            matches = _JA_PATTERN.findall(obj)
            if matches:
                warnings.append(f"  {path}: {', '.join(matches[:3])} (in: ...{obj[:80]}...)")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _scan(item, f"{path}[{i}]")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _scan(v, f"{path}.{k}")

    _scan(data)
    return warnings


def main():
    if not VIDEOS_FILE.exists():
        print("❌ data/videos.json 없음")
        sys.exit(1)

    videos = load_videos()
    analyses = load_analyses()
    print(f"📊 로드: videos={len(videos)}, analyses={len(analyses)}")

    result = aggregate(analyses, videos)

    # 잔여 일본어 제거 (번역 사전에 없는 것들)
    result = clean_deep(result)

    # 일본어 잔여 체크
    warnings = check_remaining_japanese(result)
    if warnings:
        print(f"\n⚠️ 일본어 잔여 {len(warnings)}건 (번역 사전 추가 필요):")
        for w in warnings[:20]:
            print(w)
        print()

    OUTPUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"✅ pre_aggregated.json 생성: {OUTPUT_FILE} ({size_kb:.1f}KB)")
    print(f"   영상 {result['meta']['total_analyzed']}개 집계 완료")
    print(f"   소재 아이디어 {len(result['qualitative']['content_idea_seeds'])}개 수집")
    pre = result.get("pre_clustered", {})
    print(f"   소재 카테고리 {len(pre.get('idea_categories', {}))}개 분류")
    print(f"   바이럴 메커니즘 {len(pre.get('viral_mechanism_clusters', {}))}개 클러스터")
    print(f"   시즌 캘린더 {len(pre.get('season_calendar', []))}개월 생성")


if __name__ == "__main__":
    main()

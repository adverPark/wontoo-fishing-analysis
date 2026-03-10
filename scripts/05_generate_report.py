"""05. HTML 리포트 생성 — 단일 HTML (인라인 CSS + Chart.js CDN)

영상별 상세 분석, 성공 요인 그룹핑, 소재 추천을 포함한 유튜버용 리포트.
"""

import html as html_mod
import json
import re
import sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
VIDEOS_FILE = DATA_DIR / "videos.json"
ANALYSIS_DIR = DATA_DIR / "analysis"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "원투낚시_알고리즘_분석.html"


def load_data() -> tuple[list[dict], dict | None]:
    videos = json.loads(VIDEOS_FILE.read_text()) if VIDEOS_FILE.exists() else []
    summary = None
    summary_file = ANALYSIS_DIR / "summary.json"
    if summary_file.exists():
        summary = json.loads(summary_file.read_text())
    return videos, summary


def load_analysis(video_id: str) -> dict | None:
    f = ANALYSIS_DIR / f"{video_id}.json"
    if f.exists():
        return json.loads(f.read_text())
    return None


def fmt(n: int) -> str:
    if n >= 10000:
        return f"{n/10000:.1f}만"
    elif n >= 1000:
        return f"{n/1000:.1f}천"
    return str(n)


# Japanese character ranges: Hiragana U+3040-U+309F, Katakana U+30A0-U+30FF
_JP_PATTERN = re.compile(r'[぀-ゟ゠-ヿ]')

def strip_jp(text: str) -> str:
    """Remove Japanese hiragana/katakana characters from text."""
    return _JP_PATTERN.sub('', text) if text else ""

def esc(text: str) -> str:
    return html_mod.escape(strip_jp(str(text))) if text else ""


def tier_badge(tier: str | None) -> str:
    if not tier:
        return ""
    colors = {
        "TIER1_ABSOLUTE": ("#ff4444", "TIER1 절대 바이럴"),
        "TIER2_RELATIVE": ("#ff8800", "TIER2 상대 바이럴"),
        "TIER3_SUB_RATIO": ("#44bb44", "TIER3 구독자비율"),
    }
    color, label = colors.get(tier, ("#888", tier))
    return f'<span class="badge" style="background:{color}">{label}</span>'


def factor_badge(factor: str | None) -> str:
    if not factor:
        return ""
    colors = {
        "title": ("#e94560", "제목"),
        "thumbnail": ("#0f3460", "썸네일"),
        "content": ("#533483", "콘텐츠"),
        "timing": ("#00b4d8", "타이밍"),
        "topic": ("#90be6d", "소재"),
    }
    color, label = colors.get(factor, ("#888", factor))
    return f'<span class="badge" style="background:{color}">핵심: {label}</span>'


def score_bar(score: int, label: str) -> str:
    color = "#ff4444" if score >= 9 else "#ff8800" if score >= 7 else "#44bb44" if score >= 5 else "#888"
    width = score * 10
    return f'''<div class="score-row">
        <span class="score-label">{label}</span>
        <div class="score-track"><div class="score-fill" style="width:{width}%;background:{color}"></div></div>
        <span class="score-num">{score}</span>
    </div>'''


def build_video_card(v: dict, analysis: dict | None, idx: int) -> str:
    safe_title = esc(v['title'])
    vid = v['video_id']
    thumb = f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"
    link = f"https://www.youtube.com/watch?v={vid}"
    duration_str = ""
    if v.get("duration"):
        m, s = divmod(int(v["duration"]), 60)
        duration_str = f"{m}:{s:02d}"
    sub_ratio = v["view_count"] / max(v["subscriber_count"], 1)

    # 기본 카드
    detail_html = ""
    scores_html = ""
    factor_html = ""

    if analysis:
        ss = analysis.get("success_score", {})
        factor_html = factor_badge(ss.get("primary_factor"))
        verdict = esc(ss.get("verdict", ""))

        scores_html = f'''<div class="scores-section">
            {score_bar(ss.get("title_score", 0), "제목")}
            {score_bar(ss.get("thumbnail_score", 0), "썸네일")}
            {score_bar(ss.get("content_score", 0), "콘텐츠")}
            {score_bar(ss.get("timing_score", 0), "타이밍")}
        </div>
        <p class="verdict">{verdict}</p>'''

        # 상세 분석 (토글)
        ta = analysis.get("title_analysis", {})
        tha = analysis.get("thumbnail_analysis", {})
        cs = analysis.get("content_structure", {})
        af = analysis.get("algorithm_factors", {})
        fi = analysis.get("fishing_info", {})
        seeds = analysis.get("content_idea_seeds", [])

        # 제목 분석
        title_detail = ""
        if ta:
            kw = ", ".join(ta.get("keyword_power", []))
            strengths = "".join(f"<li>{esc(s)}</li>" for s in ta.get("strengths", []))
            improvements = "".join(f"<li>{esc(s)}</li>" for s in ta.get("improvements", []))
            title_detail = f'''<div class="detail-block">
                <h4>제목 분석</h4>
                <p><b>훅 유형:</b> {esc(ta.get("hook_type", ""))}</p>
                <p><b>감정 트리거:</b> {esc(ta.get("emotional_trigger", ""))}</p>
                <p><b>파워 키워드:</b> {esc(kw)}</p>
                <p><b>제목 공식:</b> {esc(ta.get("formula", ""))}</p>
                {"<p><b>잘한 점:</b></p><ul>" + strengths + "</ul>" if strengths else ""}
                {"<p><b>개선점:</b></p><ul>" + improvements + "</ul>" if improvements else ""}
            </div>'''

        # 썸네일 분석
        thumb_detail = ""
        if tha:
            t_strengths = "".join(f"<li>{esc(s)}</li>" for s in tha.get("strengths", []))
            t_improvements = "".join(f"<li>{esc(s)}</li>" for s in tha.get("improvements", []))
            thumb_detail = f'''<div class="detail-block">
                <h4>썸네일 분석</h4>
                <p><b>주요 피사체:</b> {esc(tha.get("main_subject", ""))}</p>
                <p><b>텍스트:</b> {esc(tha.get("text_overlay", ""))}</p>
                <p><b>클릭 유발:</b> {esc(tha.get("click_trigger", ""))}</p>
                <p><b>구도:</b> {esc(tha.get("composition", ""))}</p>
                {"<p><b>잘한 점:</b></p><ul>" + t_strengths + "</ul>" if t_strengths else ""}
                {"<p><b>개선점:</b></p><ul>" + t_improvements + "</ul>" if t_improvements else ""}
            </div>'''

        # 콘텐츠 구조
        content_detail = ""
        if cs:
            retention = "".join(f"<li>{esc(r)}</li>" for r in cs.get("retention_techniques", []))
            content_detail = f'''<div class="detail-block">
                <h4>콘텐츠 구조</h4>
                <p><b>오프닝 훅:</b> {esc(cs.get("opening_hook", ""))}</p>
                <p><b>전개:</b> {esc(cs.get("buildup", ""))}</p>
                <p><b>클라이맥스:</b> {esc(cs.get("climax", ""))}</p>
                <p><b>스토리텔링:</b> {esc(cs.get("storytelling", ""))}</p>
                {"<p><b>시청 유지 기법:</b></p><ul>" + retention + "</ul>" if retention else ""}
            </div>'''

        # 알고리즘 분석
        algo_detail = f'''<div class="detail-block highlight-block">
            <h4>왜 알고리즘에 선택되었나?</h4>
            <p>{esc(af.get("why_viral", ""))}</p>
            <p><b>채널 평균 대비:</b> {esc(af.get("vs_channel_average", ""))}</p>
            <p><b>타겟 시청자:</b> {esc(af.get("audience_appeal", ""))}</p>
            <p><b>공유 요인:</b> {esc(af.get("shareability", ""))}</p>
        </div>''' if af else ""

        # 낚시 정보
        fish_detail = ""
        if fi and any(fi.values()):
            fish_detail = f'''<div class="detail-block">
                <h4>낚시 정보</h4>
                {"<p><b>장소:</b> " + esc(fi.get("location", "")) + "</p>" if fi.get("location") else ""}
                {"<p><b>어종:</b> " + esc(fi.get("fish_species", "")) + "</p>" if fi.get("fish_species") else ""}
                {"<p><b>채비:</b> " + esc(fi.get("rig", "")) + "</p>" if fi.get("rig") else ""}
                {"<p><b>미끼:</b> " + esc(fi.get("bait", "")) + "</p>" if fi.get("bait") else ""}
                {"<p><b>조과:</b> " + esc(fi.get("catch_result", "")) + "</p>" if fi.get("catch_result") else ""}
            </div>'''

        # 소재 아이디어
        seeds_detail = ""
        if seeds:
            seed_items = ""
            for seed in seeds:
                if isinstance(seed, dict):
                    seed_items += f'''<li>
                        <b>{esc(seed.get("idea", ""))}</b>
                        <br><span class="muted">{esc(seed.get("why", ""))}</span>
                    </li>'''
                else:
                    seed_items += f"<li>{esc(seed)}</li>"
            seeds_detail = f'''<div class="detail-block idea-block">
                <h4>파생 소재 아이디어</h4>
                <ul>{seed_items}</ul>
            </div>'''

        detail_html = f'''<div class="video-detail" id="detail-{idx}" style="display:none">
            {algo_detail}
            {title_detail}
            {thumb_detail}
            {content_detail}
            {fish_detail}
            {seeds_detail}
        </div>'''

    summary_text = esc(analysis.get("summary", "")) if analysis else ""

    return f'''
    <div class="video-card-wrap" onclick="toggleDetail({idx})">
      <div class="video-card">
        <a href="{link}" target="_blank" onclick="event.stopPropagation()">
          <img src="{thumb}" alt="{safe_title}" class="thumb">
        </a>
        <div class="video-info">
          <a href="{link}" target="_blank" class="video-title" onclick="event.stopPropagation()">{safe_title}</a>
          <div class="video-meta">
            <span>{esc(v['channel_name'])}</span>
            <span>조회수 {fmt(v['view_count'])}</span>
            <span>구독자 {fmt(v['subscriber_count'])}</span>
            <span>구독자 대비 {sub_ratio:.1f}x</span>
            {"<span>" + duration_str + "</span>" if duration_str else ""}
          </div>
          <div class="badges">
            {tier_badge(v.get('hit_tier'))}
            {factor_html}
          </div>
          {scores_html}
          {"<p class='video-summary'>" + summary_text + "</p>" if summary_text else ""}
          {"<span class='expand-hint'>클릭하여 상세 분석 보기 ▼</span>" if analysis else ""}
        </div>
      </div>
      {detail_html}
    </div>'''


def build_video_catalog_section(summary: dict) -> str:
    """video_catalog 섹션: 72개 영상 한눈에 보기 테이블."""
    if not summary:
        return ""
    catalog = summary.get("video_catalog", [])
    if not catalog:
        return ""

    FACTOR_LABELS = {"title": "제목", "thumbnail": "썸네일", "content": "콘텐츠",
                     "timing": "타이밍", "topic": "소재"}
    FACTOR_COLORS = {"title": "#e94560", "thumbnail": "#0f3460", "content": "#533483",
                     "timing": "#00b4d8", "topic": "#90be6d"}

    rows = ""
    for v in catalog:
        vid = v.get("video_id", "")
        link = f"https://www.youtube.com/watch?v={vid}"
        pf = v.get("primary_factor", "")
        pf_label = FACTOR_LABELS.get(pf, pf)
        pf_color = FACTOR_COLORS.get(pf, "#888")
        fish = ", ".join(v.get("fish_species", [])) if isinstance(v.get("fish_species"), list) else esc(v.get("fish_species", ""))

        rows += f'''<tr>
            <td><a href="{link}" target="_blank" class="catalog-link">{esc(v.get("title_ko", vid))}</a></td>
            <td>{esc(v.get("channel", ""))}</td>
            <td class="num">{fmt(v.get("views", 0))}</td>
            <td class="num">{v.get("hit_ratio", 0):.1f}x</td>
            <td><span class="badge" style="background:{pf_color};font-size:0.7em">{pf_label}</span></td>
            <td class="num">{v.get("overall_score", 0)}</td>
            <td>{esc(fish)}</td>
            <td class="reason">{esc(v.get("one_line_hit_reason", ""))}</td>
        </tr>'''

    return f'''
    <section class="section">
      <h2>전체 분석 영상 카탈로그 ({len(catalog)}개)</h2>
      <p class="muted">모든 분석 영상의 핵심 정보를 한눈에 비교합니다.</p>
      <div class="catalog-wrap">
        <table class="catalog-table">
          <thead>
            <tr>
              <th>제목</th><th>채널</th><th>조회수</th><th>히트비</th>
              <th>핵심요인</th><th>점수</th><th>어종</th><th>히트 이유</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>'''


def build_viral_mechanisms_section(summary: dict) -> str:
    """터지는 메커니즘 TOP 섹션."""
    if not summary:
        return ""
    mechanisms = summary.get("viral_mechanisms", [])
    if not mechanisms:
        return ""

    MECH_COLORS = ["#e94560", "#0f3460", "#533483", "#00b4d8", "#90be6d",
                   "#f77f00", "#d62828", "#4361ee", "#7209b7"]
    cards = ""
    for i, m in enumerate(mechanisms):
        color = MECH_COLORS[i % len(MECH_COLORS)]
        # Representative videos
        vids_html = ""
        for rv in m.get("representative_videos", [])[:3]:
            vid = rv.get("video_id", "")
            link = f"https://www.youtube.com/watch?v={vid}" if vid else "#"
            thumb = f"https://img.youtube.com/vi/{vid}/default.jpg" if vid else ""
            vids_html += f'''<div class="mech-video">
                <img src="{thumb}" class="sfg-thumb" alt="">
                <div>
                    <a href="{link}" target="_blank" class="sfg-detail-title">{esc(rv.get("title_ko", vid))}</a>
                    <span class="sfg-views">{fmt(rv.get("views", 0))} 조회</span>
                    <p class="muted" style="margin:2px 0;font-size:0.82em">{esc(rv.get("example", ""))}</p>
                </div>
            </div>'''

        cards += f'''<div class="mech-card" style="border-left:4px solid {color}">
            <div class="mech-header">
                <span class="mech-count" style="background:{color}">{m.get("count", 0)}</span>
                <h4 class="mech-title">{esc(m.get("mechanism", ""))}</h4>
            </div>
            <p class="mech-desc">{esc(m.get("description", ""))}</p>
            <div class="mech-videos">{vids_html}</div>
            <div class="mech-apply">
                <b>원투낚시 적용법</b>
                <p>{esc(m.get("wontoo_application", ""))}</p>
            </div>
        </div>'''

    return f'''
    <section class="section">
      <h2>터지는 메커니즘 TOP</h2>
      <p class="muted">72개 히트 영상의 바이럴 이유를 메커니즘별로 분류한 결과입니다.</p>
      <div class="mech-grid">{cards}</div>
    </section>'''


def build_idea_pool_section(summary: dict) -> str:
    """소재 아이디어 풀 섹션 (접이식)."""
    if not summary:
        return ""
    pool = summary.get("idea_pool", {})
    if not pool:
        return ""

    CAT_LABELS = {
        "가성비_도전": ("가성비/도전", "#e94560"),
        "장비_기어": ("장비/기어", "#0f3460"),
        "장소_탐험": ("장소/탐험", "#533483"),
        "교육": ("교육", "#00b4d8"),
        "어종특화": ("어종특화", "#90be6d"),
        "초보자": ("초보자", "#f77f00"),
        "시즌": ("시즌", "#d62828"),
        "기타": ("기타", "#888"),
    }

    total_ideas = sum(len(items) for items in pool.values())
    categories_html = ""
    pool_idx = 0
    for cat, items in pool.items():
        if not items:
            continue
        label, color = CAT_LABELS.get(cat, (cat, "#888"))
        ideas_list = ""
        for item in items:
            if isinstance(item, dict):
                vid = item.get("source_video", "")
                link = f"https://www.youtube.com/watch?v={vid}" if vid else ""
                link_html = f' <a href="{link}" target="_blank" class="catalog-link" style="font-size:0.75em">[참고]</a>' if link else ""
                ideas_list += f'''<li>
                    <b>{esc(item.get("idea", ""))}</b>{link_html}
                    {"<br><span class='muted'>" + esc(item.get("why", "")) + "</span>" if item.get("why") else ""}
                </li>'''
            else:
                ideas_list += f"<li>{esc(item)}</li>"

        categories_html += f'''<div class="pool-category">
            <button class="pool-toggle" onclick="var el=document.getElementById('pool-{pool_idx}');var btn=this;if(el.style.display==='none'){{el.style.display='block';btn.querySelector('.pool-arrow').textContent='▼'}}else{{el.style.display='none';btn.querySelector('.pool-arrow').textContent='▶'}}" style="border-left:3px solid {color}">
                <span class="pool-arrow">▶</span>
                <span class="pool-label">{label}</span>
                <span class="pool-count">{len(items)}개</span>
            </button>
            <ul class="pool-list" id="pool-{pool_idx}" style="display:none">{ideas_list}</ul>
        </div>'''
        pool_idx += 1

    return f'''
    <section class="section">
      <h2>소재 아이디어 풀 ({total_ideas}개)</h2>
      <p class="muted">72개 히트 영상에서 추출한 모든 소재 아이디어를 카테고리별로 정리했습니다. 소재를 고를 때 레퍼런스로 활용하세요.</p>
      <div class="pool-wrap">{categories_html}</div>
    </section>'''


def build_season_calendar_section(summary: dict) -> str:
    """시즌 캘린더 섹션."""
    if not summary:
        return ""
    calendar = summary.get("season_calendar", [])
    if not calendar:
        return ""

    SEASON_COLORS = {
        "한겨울": "#4361ee", "늦겨울": "#4895ef", "초봄": "#90be6d",
        "봄": "#43aa8b", "늦봄": "#577590", "초여름": "#f77f00",
        "여름": "#e94560", "한여름": "#d62828", "초가을": "#f4a261",
        "가을": "#e76f51", "늦가을": "#6d6875", "초겨울": "#457b9d",
    }

    months_html = ""
    for m in calendar:
        season = m.get("season", "")
        color = SEASON_COLORS.get(season, "#888")
        fish_tags = " ".join(f'<span class="kw-tag" style="font-size:0.75em">{esc(f)}</span>' for f in m.get("target_fish", [])[:5])
        months_html += f'''<div class="cal-month" style="border-top:3px solid {color}">
            <div class="cal-header">
                <span class="cal-month-name">{esc(m.get("month", ""))}</span>
                <span class="cal-season" style="color:{color}">{esc(season)}</span>
            </div>
            <div class="cal-fish">{fish_tags}</div>
            <p class="cal-topic"><b>추천 소재:</b> {esc(m.get("recommended_topic", ""))}</p>
            <p class="cal-tip muted">{esc(m.get("content_tip", ""))}</p>
        </div>'''

    return f'''
    <section class="section">
      <h2>시즌 캘린더</h2>
      <p class="muted">월별 추천 어종과 콘텐츠 소재를 정리했습니다. 원투낚시 채널 운영의 연간 로드맵으로 활용하세요.</p>
      <div class="cal-grid">{months_html}</div>
    </section>'''


def build_strategy_section(summary: dict) -> str:
    if not summary:
        return ""

    sections = []

    # 히트 vs 비히트 비교
    hvn = summary.get("hit_vs_nothit", {})
    if hvn:
        sections.append(f'''
        <section class="section">
          <h2>알고리즘 탄 영상 vs 안 탄 영상</h2>
          <div class="compare-grid">
            <div class="compare-card hit-card">
              <h3>알고리즘 탄 영상 제목 패턴</h3>
              <ul>{"".join(f"<li>{esc(p)}</li>" for p in hvn.get("title_patterns_hit", []))}</ul>
            </div>
            <div class="compare-card nothit-card">
              <h3>알고리즘 안 탄 영상 제목 패턴</h3>
              <ul>{"".join(f"<li>{esc(p)}</li>" for p in hvn.get("title_patterns_nothit", []))}</ul>
            </div>
          </div>
          <div class="insight-box">
            <b>핵심 차이:</b> {esc(hvn.get("title_difference", ""))}
          </div>
          <div class="insight-box">
            <b>영상 길이:</b> 히트 평균 {esc(hvn.get("duration_hit_avg", ""))} vs 비히트 평균 {esc(hvn.get("duration_nothit_avg", ""))}
            <br>{esc(hvn.get("duration_insight", ""))}
          </div>
        </section>''')

    # 성공 요인별 그룹
    sfg = summary.get("success_factor_groups", {})
    if sfg:
        factor_meta = {
            "title_driven":     ("제목 주도",   "#e94560", "Aa"),
            "thumbnail_driven": ("썸네일 주도", "#0f3460", "&#9638;"),
            "content_driven":   ("콘텐츠 주도", "#533483", "&#9654;"),
            "timing_driven":    ("타이밍 주도", "#00b4d8", "&#9200;"),
            "topic_driven":     ("소재 주도",   "#90be6d", "&#9733;"),
        }
        # 전체 영상 수 (비율 바 계산용)
        total_factor_videos = sum(
            len(sfg.get(k, {}).get("video_ids", [])) for k in factor_meta
        )
        sfg_idx = 0
        group_cards = ""
        for key, (label, color, icon) in factor_meta.items():
            g = sfg.get(key, {})
            vids = g.get("video_ids", [])
            count = len(vids)
            if not count and not g.get("common_pattern"):
                continue
            pct = round(count / max(total_factor_videos, 1) * 100)

            # 영상별 상세 (video_details) — 토글 방식
            vd_html = ""
            video_details = g.get("video_details", [])
            if video_details:
                vd_items = ""
                for vd in video_details[:5]:
                    if isinstance(vd, dict):
                        vid = vd.get("video_id", "")
                        link = f"https://www.youtube.com/watch?v={vid}" if vid else "#"
                        thumb = f"https://img.youtube.com/vi/{vid}/default.jpg" if vid else ""
                        vd_items += f'''<div class="sfg-detail-item">
                            <img src="{thumb}" class="sfg-thumb" alt="">
                            <div class="sfg-detail-text">
                                <a href="{link}" target="_blank" class="sfg-detail-title">{esc(vid)}</a>
                                <span class="sfg-views">{fmt(vd.get("views", 0))} 조회</span>
                                <p class="sfg-mechanism">{esc(vd.get("specific_mechanism", ""))}</p>
                                <p class="sfg-lesson-item">원투 교훈: {esc(vd.get("wontoo_lesson", ""))}</p>
                            </div>
                        </div>'''
                vd_html = f'''<div class="sfg-details-wrap" id="sfg-detail-{sfg_idx}" style="display:none">
                    {vd_items}
                </div>
                <button class="sfg-toggle" onclick="event.stopPropagation();var el=document.getElementById('sfg-detail-{sfg_idx}');var btn=this;if(el.style.display==='none'){{el.style.display='block';btn.textContent='접기'}}else{{el.style.display='none';btn.textContent='대표 영상 {len(video_details)}개 보기'}}">대표 영상 {len(video_details)}개 보기</button>'''
                sfg_idx += 1

            group_cards += f'''<div class="sfg-card" style="--factor-color:{color}">
                <div class="sfg-header">
                    <span class="sfg-icon" style="background:{color}">{icon}</span>
                    <div class="sfg-header-text">
                        <h3 class="sfg-title">{label}</h3>
                        <span class="sfg-count">{count}개 영상 ({pct}%)</span>
                    </div>
                </div>
                <div class="sfg-bar-track"><div class="sfg-bar-fill" style="width:{pct}%;background:{color}"></div></div>
                <p class="sfg-pattern">{esc(g.get("common_pattern", ""))}</p>
                <div class="sfg-lesson-box">
                    <b>핵심 교훈</b>
                    <p>{esc(g.get("lesson", ""))}</p>
                </div>
                {vd_html}
            </div>'''

        if group_cards:
            sections.append(f'''
            <section class="section">
              <h2>성공 요인별 분류</h2>
              <p class="muted">72개 히트 영상을 알고리즘 성공의 핵심 요인별로 분류한 결과입니다.</p>
              <div class="sfg-grid">{group_cards}</div>
            </section>''')

    # 성공 패턴 분석
    sp = summary.get("success_patterns", {})
    if sp and any(sp.values()):
        sp_items = ""
        # 제목 키워드
        title_kw = sp.get("title_keywords", [])
        if title_kw:
            kw_tags = " ".join(f'<span class="kw-tag">{esc(k)}</span>' for k in title_kw)
            sp_items += f'<div class="strategy-card"><h4>자주 등장하는 제목 키워드</h4><div class="kw-cloud">{kw_tags}</div></div>'
        # 검증된 제목 공식
        title_formulas = sp.get("title_formulas", [])
        if title_formulas:
            formulas_items = ""
            for f in title_formulas:
                if isinstance(f, dict):
                    formulas_items += f'''<li>
                        <b>{esc(f.get("formula", ""))}</b>
                        <br><span class="muted">예시: {esc(f.get("example", ""))}</span>
                        {"<br><span class='muted'>성공 사례: " + esc(f.get("success_case", "")) + "</span>" if f.get("success_case") else ""}
                        {"<br><span style='font-size:0.82em'>" + esc(f.get("why_it_works", "")) + "</span>" if f.get("why_it_works") else ""}
                    </li>'''
                else:
                    formulas_items += f"<li>{esc(f)}</li>"
            sp_items += f'<div class="strategy-card"><h4>검증된 제목 공식</h4><ul>{formulas_items}</ul></div>'
        # 인기 어종
        pop_fish = sp.get("popular_fish", [])
        if pop_fish:
            fish_items = ""
            for f in pop_fish:
                if isinstance(f, dict):
                    fish_items += f'''<li>
                        <b>{esc(f.get("species", ""))}</b> ({f.get("count", 0)}회)
                        {"<br><span class='muted'>" + esc(f.get("why_popular", "")) + "</span>" if f.get("why_popular") else ""}
                    </li>'''
                else:
                    fish_items += f"<li>{esc(f)}</li>"
            sp_items += f'<div class="strategy-card"><h4>인기 어종 TOP</h4><ol>{fish_items}</ol></div>'
        # 최적 길이 + 시즌 + 썸네일 + 콘텐츠 구조
        misc_items = ""
        if sp.get("optimal_duration"):
            misc_items += f"<li><b>최적 영상 길이:</b> {esc(sp['optimal_duration'])}</li>"
        if sp.get("season_patterns"):
            misc_items += f"<li><b>시즌 패턴:</b> {esc(sp['season_patterns'])}</li>"
        thumb_pats = sp.get("thumbnail_patterns", [])
        if thumb_pats:
            misc_items += "<li><b>성공 썸네일:</b> " + ", ".join(esc(t) for t in thumb_pats) + "</li>"
        content_structs = sp.get("content_structures", [])
        if content_structs:
            misc_items += "<li><b>콘텐츠 구조:</b> " + ", ".join(esc(c) for c in content_structs) + "</li>"
        if misc_items:
            sp_items += f'<div class="strategy-card"><h4>성공 패턴 요약</h4><ul>{misc_items}</ul></div>'

        if sp_items:
            sections.append(f'''
            <section class="section">
              <h2>성공 패턴 분석</h2>
              <div class="strategy-grid">{sp_items}</div>
            </section>''')

    # 소재 추천
    strat = summary.get("actionable_strategy", {})
    topics = strat.get("recommended_topics", [])
    if topics:
        topic_cards = ""
        for t in topics:
            if isinstance(t, dict):
                # 촬영 체크리스트
                checklist_html = ""
                checklist = t.get("filming_checklist", [])
                if checklist:
                    cl_items = "".join(f"<li>{esc(c)}</li>" for c in checklist)
                    checklist_html = f'<div class="checklist-box"><b>촬영 체크리스트:</b><ul>{cl_items}</ul></div>'
                # 예상 잠재력
                potential_html = ""
                if t.get("estimated_potential"):
                    potential_html = f'<p class="potential-box">{esc(t["estimated_potential"])}</p>'
                # 콘텐츠 구조
                structure_html = ""
                if t.get("content_structure"):
                    structure_html = f'<p class="muted">영상 구성: {esc(t["content_structure"])}</p>'

                topic_cards += f'''<div class="topic-card">
                    <h4>{esc(t.get("topic", ""))}</h4>
                    <p>{esc(t.get("why", ""))}</p>
                    {"<p class='muted'>추천 제목: " + esc(t.get("title_suggestion", "")) + "</p>" if t.get("title_suggestion") else ""}
                    {"<p class='muted'>썸네일 팁: " + esc(t.get("thumbnail_tip", "")) + "</p>" if t.get("thumbnail_tip") else ""}
                    {structure_html}
                    {checklist_html}
                    {potential_html}
                </div>'''
            else:
                topic_cards += f'<div class="topic-card"><p>{esc(t)}</p></div>'
        sections.append(f'''
        <section class="section">
          <h2>추천 영상 소재</h2>
          <div class="topics-grid">{topic_cards}</div>
        </section>''')

    # 제목 공식 + 썸네일 가이드
    templates = strat.get("title_templates", [])
    thumb_guide = strat.get("thumbnail_guidelines", [])
    content_tips = strat.get("content_tips", [])

    formula_cards = ""
    if templates:
        for t in templates:
            if isinstance(t, dict):
                formula_cards += f'''<div class="strategy-card">
                    <h4>{esc(t.get("template", ""))}</h4>
                    <p class="muted">예시: {esc(t.get("example", ""))}</p>
                </div>'''
            else:
                formula_cards += f'<div class="strategy-card"><p>{esc(t)}</p></div>'

    tips_html = ""
    if thumb_guide or content_tips:
        tips_html = '<div class="strategy-grid">'
        if thumb_guide:
            tips_html += f'''<div class="strategy-card">
                <h4>썸네일 가이드라인</h4>
                <ul>{"".join(f"<li>{esc(g)}</li>" for g in thumb_guide)}</ul>
            </div>'''
        if content_tips:
            tips_html += f'''<div class="strategy-card">
                <h4>콘텐츠 구성 팁</h4>
                <ul>{"".join(f"<li>{esc(c)}</li>" for c in content_tips)}</ul>
            </div>'''
        opt_len = strat.get("optimal_length", "")
        upload = strat.get("upload_timing", "")
        if opt_len or upload:
            tips_html += f'''<div class="strategy-card">
                <h4>최적 설정</h4>
                <ul>
                  {"<li><b>영상 길이:</b> " + esc(opt_len) + "</li>" if opt_len else ""}
                  {"<li><b>업로드 시간:</b> " + esc(upload) + "</li>" if upload else ""}
                </ul>
            </div>'''
        tips_html += '</div>'

    if formula_cards or tips_html:
        sections.append(f'''
        <section class="section">
          <h2>전략 가이드</h2>
          {"<h3>제목 공식</h3><div class='strategy-grid'>" + formula_cards + "</div>" if formula_cards else ""}
          {tips_html}
        </section>''')

    # 국내 vs 해외
    kvi = summary.get("korean_vs_international", {})
    if kvi and any(kvi.values()):
        # 미개척 기회
        untapped_html = ""
        untapped = kvi.get("untapped_opportunities", [])
        if untapped:
            opp_cards = ""
            for opp in untapped:
                if isinstance(opp, dict):
                    opp_cards += f'''<div class="opportunity-card">
                        <h4>{esc(opp.get("opportunity", ""))}</h4>
                        <p><b>일본 검증:</b> {esc(opp.get("japan_evidence", ""))}</p>
                        <p><b>한국 갭:</b> {esc(opp.get("korea_gap", ""))}</p>
                        <p class="action-box">{esc(opp.get("action", ""))}</p>
                    </div>'''
            untapped_html = f'''
            <h3 style="margin-top:20px">한국 미개척 기회</h3>
            <div class="topics-grid">{opp_cards}</div>'''

        sections.append(f'''
        <section class="section">
          <h2>국내 vs 해외 인사이트</h2>
          <div class="compare-grid">
            <div class="compare-card">
              <h3>한국 채널 특징</h3>
              <p>{esc(kvi.get("korean_patterns", ""))}</p>
            </div>
            <div class="compare-card">
              <h3>해외 채널 특징</h3>
              <p>{esc(kvi.get("international_patterns", ""))}</p>
            </div>
          </div>
          <div class="insight-box">
            <b>크로스 인사이트:</b> {esc(kvi.get("cross_insights", ""))}
          </div>
          {untapped_html}
        </section>''')

    return "\n".join(sections)


def generate_html(videos: list[dict], summary: dict | None) -> str:
    hit_videos = [v for v in videos if v.get("is_algorithm_hit")]
    wontoo_hits = [v for v in hit_videos if v.get("category") == "원투낚시"]
    nothit_wontoo = [v for v in videos if not v.get("is_algorithm_hit") and v.get("category") == "원투낚시"]

    # 분석 데이터 캐싱 (파일 I/O 중복 방지)
    analyses: dict[str, dict | None] = {}
    for v in hit_videos:
        vid = v["video_id"]
        if vid not in analyses:
            analyses[vid] = load_analysis(vid)

    total_channels = len(set(v["channel_id"] for v in videos))
    total_hits = len(hit_videos)
    analyzed_count = sum(1 for v in hit_videos if analyses.get(v["video_id"]))

    # 히트 영상을 hit_ratio 기준으로 3단계 분류
    tier_counts = {"TIER1_ABSOLUTE": 0, "TIER2_RELATIVE": 0, "TIER3_SUB_RATIO": 0}
    for v in hit_videos:
        ratio = v.get("hit_ratio", 0)
        if ratio >= 10:
            tier_counts["TIER1_ABSOLUTE"] += 1
        elif ratio >= 5:
            tier_counts["TIER2_RELATIVE"] += 1
        else:
            tier_counts["TIER3_SUB_RATIO"] += 1

    # 어종/길이 데이터
    durations: list[int] = []
    factor_counts: dict[str, int] = {}
    # factor별 색상 매핑 (badge와 동일)
    FACTOR_COLORS = {
        "title": "#e94560", "thumbnail": "#0f3460", "content": "#533483",
        "timing": "#00b4d8", "topic": "#90be6d",
    }
    for v in hit_videos:
        a = analyses.get(v["video_id"])
        if a:
            pf = a.get("success_score", {}).get("primary_factor", "")
            if pf:
                factor_counts[pf] = factor_counts.get(pf, 0) + 1
        if v.get("duration"):
            durations.append(v["duration"])

    # 인기 어종 — summary.json의 popular_fish 사용 (번역 완료된 한국어)
    popular_fish = summary.get("success_patterns", {}).get("popular_fish", []) if summary else []
    top_fish = [(f.get("species", ""), f.get("count", 0)) for f in popular_fish[:5]]
    fish_labels = json.dumps([f[0] for f in top_fish], ensure_ascii=False)
    fish_data = json.dumps([f[1] for f in top_fish])

    duration_buckets = {"0-5분": 0, "5-10분": 0, "10-20분": 0, "20-30분": 0, "30분+": 0}
    for d in durations:
        minutes = d / 60
        if minutes <= 5: duration_buckets["0-5분"] += 1
        elif minutes <= 10: duration_buckets["5-10분"] += 1
        elif minutes <= 20: duration_buckets["10-20분"] += 1
        elif minutes <= 30: duration_buckets["20-30분"] += 1
        else: duration_buckets["30분+"] += 1

    # factor 차트 — badge 색상과 동기화
    factor_labels = json.dumps([strip_jp(k) for k in factor_counts.keys()], ensure_ascii=False)
    factor_data = json.dumps(list(factor_counts.values()))
    factor_colors = json.dumps([FACTOR_COLORS.get(k, "#888") for k in factor_counts.keys()])

    # 영상 카드
    video_cards = "\n".join(build_video_card(v, analyses.get(v["video_id"]), i) for i, v in enumerate(hit_videos[:30]))

    # 전략 섹션
    strategy_sections = build_strategy_section(summary)
    catalog_section = build_video_catalog_section(summary)
    viral_mechanisms_section = build_viral_mechanisms_section(summary)
    idea_pool_section = build_idea_pool_section(summary)
    season_calendar_section = build_season_calendar_section(summary)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>원투낚시 알고리즘 분석 리포트</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {{
  --bg: #1a1a2e; --card: #16213e; --accent: #0f3460;
  --highlight: #e94560; --text: #eee; --muted: #999;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; line-height:1.6; padding:20px; max-width:1200px; margin:0 auto; }}
.hero-header {{ text-align:center; margin:40px 0 30px; }}
.hero-logos {{ display:flex; align-items:center; justify-content:center; gap:16px; margin-bottom:16px; }}
.channel-logo {{ width:72px; height:72px; border-radius:50%; border:3px solid rgba(255,255,255,0.2); box-shadow:0 4px 20px rgba(0,0,0,0.4); transition:transform 0.3s; }}
.channel-logo:hover {{ transform:scale(1.1); }}
.yt-logo {{ width:80px; height:18px; opacity:0.9; }}
h1 {{ text-align:center; margin:0; font-size:2em; }}
h1 span {{ color:var(--highlight); }}
h2 {{ margin:25px 0 15px; padding-bottom:8px; border-bottom:2px solid var(--accent); }}
h3 {{ margin:10px 0 8px; color:var(--highlight); font-size:1em; }}
h4 {{ margin:8px 0 5px; color:var(--text); font-size:0.95em; }}
.dashboard {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:20px 0; }}
.stat-card {{ background:var(--card); border-radius:12px; padding:18px; text-align:center; border:1px solid var(--accent); }}
.stat-card .number {{ font-size:2.2em; font-weight:bold; color:var(--highlight); }}
.stat-card .label {{ color:var(--muted); font-size:0.85em; }}
.charts-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:15px; margin:20px 0; }}
.chart-card {{ background:var(--card); border-radius:12px; padding:18px; border:1px solid var(--accent); }}
.chart-card h3 {{ margin-bottom:12px; }}
.video-card-wrap {{ background:var(--card); border-radius:12px; margin:10px 0; border:1px solid var(--accent); transition:all .2s; cursor:pointer; }}
.video-card-wrap:hover {{ border-color:var(--highlight); box-shadow:0 4px 12px rgba(233,69,96,0.15); }}
.video-card {{ display:flex; gap:15px; padding:15px; }}
.thumb {{ width:200px; height:112px; object-fit:cover; border-radius:8px; flex-shrink:0; }}
.video-info {{ flex:1; min-width:0; }}
.video-title {{ color:var(--text); text-decoration:none; font-weight:bold; font-size:1.05em; display:block; margin-bottom:4px; }}
.video-title:hover {{ color:var(--highlight); }}
.video-meta {{ display:flex; flex-wrap:wrap; gap:8px; color:var(--muted); font-size:0.8em; margin:4px 0; }}
.badges {{ display:flex; gap:6px; flex-wrap:wrap; margin:4px 0; }}
.badge {{ display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.72em; color:white; font-weight:bold; }}
.scores-section {{ margin:8px 0; }}
.score-row {{ display:flex; align-items:center; gap:6px; margin:2px 0; }}
.score-label {{ width:45px; font-size:0.75em; color:var(--muted); }}
.score-track {{ flex:1; height:6px; background:#333; border-radius:3px; overflow:hidden; }}
.score-fill {{ height:100%; border-radius:3px; transition:width .3s; }}
.score-num {{ width:20px; font-size:0.75em; text-align:right; color:var(--muted); }}
.verdict {{ font-size:0.82em; color:var(--highlight); margin:4px 0; font-style:italic; }}
.video-summary {{ color:var(--muted); font-size:0.82em; margin-top:4px; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }}
.expand-hint {{ font-size:0.72em; color:var(--accent); }}
.video-detail {{ border-top:1px solid var(--accent); padding:20px; }}
.detail-block {{ background:rgba(0,0,0,0.2); border-radius:8px; padding:12px; margin:10px 0; }}
.detail-block h4 {{ color:var(--highlight); margin-bottom:6px; }}
.detail-block p {{ font-size:0.88em; margin:3px 0; }}
.detail-block ul {{ padding-left:18px; font-size:0.85em; }}
.detail-block li {{ margin:2px 0; }}
.highlight-block {{ border-left:3px solid var(--highlight); }}
.idea-block {{ border-left:3px solid #90be6d; }}
.idea-block li {{ margin:6px 0; }}
.muted {{ color:var(--muted); font-size:0.85em; }}
.section {{ margin:30px 0; }}
.strategy-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:12px; margin:12px 0; }}
.strategy-card {{ background:var(--card); border-radius:12px; padding:18px; border:1px solid var(--accent); }}
.strategy-card ul {{ padding-left:18px; }}
.strategy-card li {{ margin:4px 0; font-size:0.88em; }}
.compare-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:12px 0; }}
.compare-card {{ background:var(--card); border-radius:12px; padding:18px; border:1px solid var(--accent); }}
.compare-card ul {{ padding-left:18px; font-size:0.88em; }}
.hit-card {{ border-left:3px solid var(--highlight); }}
.nothit-card {{ border-left:3px solid var(--muted); }}
.insight-box {{ background:var(--card); border-radius:8px; padding:15px; margin:10px 0; border:1px solid var(--accent); font-size:0.9em; }}
.topics-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:12px; margin:12px 0; }}
.topic-card {{ background:var(--card); border-radius:12px; padding:18px; border:1px solid var(--accent); border-left:3px solid #90be6d; }}
.topic-card h4 {{ color:#90be6d; }}
.factor-card {{ background:var(--card); border-radius:12px; padding:18px; border:1px solid var(--accent); }}
.factor-card .lesson {{ font-style:italic; color:var(--highlight); margin-top:8px; }}
.kw-cloud {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }}
.kw-tag {{ background:var(--accent); color:var(--text); padding:4px 12px; border-radius:16px; font-size:0.82em; }}
.footer {{ text-align:center; color:var(--muted); margin-top:40px; padding:20px; font-size:0.85em; }}
.catalog-wrap {{ overflow-x:auto; margin:12px 0; }}
.catalog-table {{ width:100%; border-collapse:collapse; font-size:0.82em; }}
.catalog-table th {{ background:var(--accent); padding:8px 10px; text-align:left; position:sticky; top:0; white-space:nowrap; }}
.catalog-table td {{ padding:6px 10px; border-bottom:1px solid rgba(255,255,255,0.05); }}
.catalog-table tr:hover {{ background:rgba(233,69,96,0.08); }}
.catalog-table .num {{ text-align:right; white-space:nowrap; }}
.catalog-table .reason {{ max-width:300px; font-size:0.9em; color:var(--muted); }}
.catalog-link {{ color:var(--text); text-decoration:none; }}
.catalog-link:hover {{ color:var(--highlight); }}
.checklist-box {{ background:rgba(0,0,0,0.2); border-radius:8px; padding:10px; margin-top:8px; font-size:0.85em; }}
.checklist-box ul {{ padding-left:18px; margin-top:4px; }}
.checklist-box li {{ margin:2px 0; }}
.potential-box {{ background:rgba(144,190,109,0.15); border-radius:6px; padding:6px 10px; margin-top:6px; font-size:0.82em; color:#90be6d; }}
.opportunity-card {{ background:var(--card); border-radius:12px; padding:18px; border:1px solid var(--accent); border-left:3px solid #00b4d8; }}
.opportunity-card h4 {{ color:#00b4d8; }}
.opportunity-card p {{ font-size:0.88em; margin:4px 0; }}
.action-box {{ background:rgba(0,180,216,0.12); border-radius:6px; padding:6px 10px; margin-top:6px; font-size:0.85em; font-weight:bold; }}
.sfg-grid {{ display:flex; flex-direction:column; gap:16px; margin:16px 0; }}
.sfg-card {{ background:var(--card); border-radius:14px; padding:22px; border:1px solid var(--accent); border-left:4px solid var(--factor-color, var(--accent)); transition:box-shadow .2s; }}
.sfg-card:hover {{ box-shadow:0 4px 20px rgba(0,0,0,0.3); }}
.sfg-header {{ display:flex; align-items:center; gap:14px; margin-bottom:12px; }}
.sfg-icon {{ width:42px; height:42px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:1.2em; font-weight:bold; color:white; flex-shrink:0; }}
.sfg-header-text {{ flex:1; }}
.sfg-title {{ margin:0; font-size:1.1em; color:var(--text); }}
.sfg-count {{ font-size:0.82em; color:var(--muted); }}
.sfg-bar-track {{ height:6px; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden; margin-bottom:14px; }}
.sfg-bar-fill {{ height:100%; border-radius:3px; transition:width .5s ease; }}
.sfg-pattern {{ font-size:0.88em; line-height:1.7; margin-bottom:14px; color:var(--text); }}
.sfg-lesson-box {{ background:rgba(233,69,96,0.08); border-radius:10px; padding:14px 16px; margin-bottom:12px; }}
.sfg-lesson-box b {{ color:var(--highlight); font-size:0.82em; text-transform:uppercase; letter-spacing:0.5px; }}
.sfg-lesson-box p {{ font-size:0.88em; margin-top:6px; font-style:italic; color:var(--text); line-height:1.6; }}
.sfg-toggle {{ background:none; border:1px solid var(--accent); color:var(--muted); padding:6px 16px; border-radius:8px; cursor:pointer; font-size:0.78em; transition:all .2s; margin-top:4px; }}
.sfg-toggle:hover {{ border-color:var(--highlight); color:var(--highlight); }}
.sfg-details-wrap {{ margin-top:14px; display:flex; flex-direction:column; gap:10px; }}
.sfg-detail-item {{ display:flex; gap:12px; background:rgba(0,0,0,0.2); border-radius:10px; padding:12px; }}
.sfg-thumb {{ width:80px; height:45px; object-fit:cover; border-radius:6px; flex-shrink:0; }}
.sfg-detail-text {{ flex:1; min-width:0; }}
.sfg-detail-title {{ color:var(--text); text-decoration:none; font-weight:600; font-size:0.82em; }}
.sfg-detail-title:hover {{ color:var(--highlight); }}
.sfg-views {{ font-size:0.72em; color:var(--muted); margin-left:8px; }}
.sfg-mechanism {{ font-size:0.82em; margin:4px 0 2px; color:var(--text); line-height:1.5; }}
.sfg-lesson-item {{ font-size:0.78em; color:var(--highlight); font-style:italic; margin:0; }}
.mech-grid {{ display:flex; flex-direction:column; gap:16px; margin:16px 0; }}
.mech-card {{ background:var(--card); border-radius:14px; padding:20px; border:1px solid var(--accent); }}
.mech-header {{ display:flex; align-items:center; gap:12px; margin-bottom:10px; }}
.mech-count {{ width:36px; height:36px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:1em; font-weight:bold; color:white; flex-shrink:0; }}
.mech-title {{ margin:0; font-size:1em; color:var(--text); }}
.mech-desc {{ font-size:0.88em; color:var(--muted); margin-bottom:12px; line-height:1.6; }}
.mech-videos {{ display:flex; flex-direction:column; gap:8px; margin-bottom:12px; }}
.mech-video {{ display:flex; gap:10px; background:rgba(0,0,0,0.2); border-radius:8px; padding:10px; }}
.mech-apply {{ background:rgba(233,69,96,0.08); border-radius:10px; padding:12px 14px; }}
.mech-apply b {{ color:var(--highlight); font-size:0.82em; text-transform:uppercase; }}
.mech-apply p {{ font-size:0.85em; margin-top:4px; font-style:italic; line-height:1.6; }}
.pool-wrap {{ display:flex; flex-direction:column; gap:6px; margin:12px 0; }}
.pool-toggle {{ display:flex; align-items:center; gap:10px; width:100%; background:var(--card); border:1px solid var(--accent); border-radius:10px; padding:12px 16px; cursor:pointer; color:var(--text); font-size:0.9em; text-align:left; transition:all .2s; }}
.pool-toggle:hover {{ border-color:var(--highlight); }}
.pool-arrow {{ font-size:0.72em; color:var(--muted); width:16px; }}
.pool-label {{ font-weight:bold; flex:1; }}
.pool-count {{ color:var(--muted); font-size:0.82em; }}
.pool-list {{ background:var(--card); border:1px solid var(--accent); border-top:none; border-radius:0 0 10px 10px; padding:12px 18px 12px 36px; list-style:disc; }}
.pool-list li {{ margin:6px 0; font-size:0.85em; line-height:1.5; }}
.cal-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; margin:16px 0; }}
.cal-month {{ background:var(--card); border-radius:12px; padding:14px; border:1px solid var(--accent); }}
.cal-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
.cal-month-name {{ font-weight:bold; font-size:1.1em; }}
.cal-season {{ font-size:0.78em; font-weight:bold; }}
.cal-fish {{ display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px; }}
.cal-topic {{ font-size:0.82em; margin:4px 0; line-height:1.4; }}
.cal-tip {{ font-size:0.78em; line-height:1.4; }}
@media (max-width:700px) {{
  .video-card {{ flex-direction:column; }}
  .thumb {{ width:100%; height:auto; }}
  .compare-grid {{ grid-template-columns:1fr; }}
  .catalog-table {{ font-size:0.72em; }}
  .cal-grid {{ grid-template-columns:repeat(2,1fr); }}
}}
</style>
</head>
<body>

<div class="hero-header">
  <div class="hero-logos">
    <img src="https://yt3.googleusercontent.com/jo3CHEamOkt13F83E47L7nioyPT6CVJHYFnmh98kodd-P2VUBkLBahNRKbURUhEawubCSd89tT0=s160-c-k-c0x00ffffff-no-rj" alt="채널 로고" class="channel-logo">
    <svg class="yt-logo" viewBox="0 0 90 20" xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="20" height="20" rx="4" fill="#FF0000"/><polygon points="8,4 8,16 16,10" fill="#fff"/><path d="M27.97 3.12V18.98h-2.54l-.29-1.49c-.93 1.13-2.23 1.74-3.61 1.74-2.88 0-4.55-2.12-4.55-5.53V3.12h2.82v9.86c0 2.37.95 3.66 2.79 3.66 1.56 0 2.76-1.04 2.76-2.77V3.12h2.62zm7.08 16.11c-3.47 0-5.66-2.37-5.66-6.5V7.98c0-4.13 2.19-5.11 5.66-5.11 3.43 0 5.16.98 5.16 5.11v4.75c0 4.13-1.73 6.5-5.16 6.5zm0-2.12c1.72 0 2.52-1.24 2.52-4.13V7.73c0-2.12-.8-2.74-2.52-2.74-1.76 0-3.02.62-3.02 2.74v5.25c0 2.89 1.26 4.13 3.02 4.13z" fill="#fff"/><path d="M50.72 1.01h2.82v17.97h-2.82v-1.49c-.88 1.13-2.08 1.74-3.46 1.74-2.93 0-4.69-2.37-4.69-6.5V7.98c0-4.13 1.76-5.11 4.69-5.11 1.38 0 2.58.61 3.46 1.74V1.01zm0 7.22c0-2.37-.95-3.24-2.79-3.24-1.72 0-2.54 1.12-2.54 3.24v4.5c0 2.89.82 4.13 2.54 4.13 1.84 0 2.79-1.29 2.79-3.41V8.23zm13.59-5.11v2.25h-3.7v13.61h-2.82V5.37h-3.7V3.12h10.22z" fill="#fff"/></svg>
  </div>
  <h1><span>원투맨</span>을 위한 알고리즘 분석 리포트</h1>
</div>

<div class="dashboard">
  <div class="stat-card"><div class="number">{total_channels}</div><div class="label">분석 채널</div></div>
  <div class="stat-card"><div class="number">{total_hits}</div><div class="label">알고리즘 히트</div></div>
  <div class="stat-card"><div class="number">{len(wontoo_hits)}</div><div class="label">원투낚시 히트</div></div>
  <div class="stat-card"><div class="number">{analyzed_count}</div><div class="label">AI 분석 완료</div></div>
  <div class="stat-card"><div class="number">{len(nothit_wontoo)}</div><div class="label">비히트 원투(비교군)</div></div>
</div>

<section class="section">
  <h2>데이터 분석</h2>
  <div class="charts-grid">
    <div class="chart-card"><h3>히트 Tier 분포</h3><canvas id="tierChart"></canvas></div>
    <div class="chart-card"><h3>성공 핵심 요인 분포</h3><canvas id="factorChart"></canvas></div>
    <div class="chart-card"><h3>인기 어종 TOP 5</h3><canvas id="fishChart"></canvas></div>
    <div class="chart-card"><h3>영상 길이 분포</h3><canvas id="durationChart"></canvas></div>
  </div>
</section>

{strategy_sections}

{viral_mechanisms_section}

{season_calendar_section}

{idea_pool_section}

{catalog_section}

<section class="section">
  <h2>알고리즘 히트 영상 TOP {min(len(hit_videos), 30)} — 상세 분석</h2>
  <p class="muted">각 영상을 클릭하면 상세 분석을 볼 수 있습니다.</p>
  {video_cards}
</section>

<div class="footer">생성: {now} | 원투낚시 알고리즘 분석기</div>

<script>
Chart.defaults.color='#eee';Chart.defaults.borderColor='#333';

new Chart(document.getElementById('tierChart'),{{
  type:'doughnut',
  data:{{labels:['TIER1 절대 바이럴','TIER2 상대 바이럴','TIER3 구독자비율'],
  datasets:[{{data:[{tier_counts['TIER1_ABSOLUTE']},{tier_counts['TIER2_RELATIVE']},{tier_counts['TIER3_SUB_RATIO']}],
  backgroundColor:['#ff4444','#ff8800','#44bb44']}}]}},
  options:{{plugins:{{legend:{{position:'bottom'}}}}}}
}});

if({factor_data}.some(v=>v>0)){{
  new Chart(document.getElementById('factorChart'),{{
    type:'doughnut',
    data:{{labels:{factor_labels},
    datasets:[{{data:{factor_data},
    backgroundColor:{factor_colors}}}]}},
    options:{{plugins:{{legend:{{position:'bottom'}}}}}}
  }});
}} else {{
  document.getElementById('factorChart').parentElement.innerHTML='<h3>성공 핵심 요인 분포</h3><p style="color:#999;text-align:center;padding:40px 0">분석 데이터 대기 중</p>';
}}

if({fish_data}.some(v=>v>0)){{
  new Chart(document.getElementById('fishChart'),{{
    type:'pie',
    data:{{labels:{fish_labels},
    datasets:[{{data:{fish_data},
    backgroundColor:['#e94560','#0f3460','#533483','#00b4d8','#90be6d']}}]}},
    options:{{plugins:{{legend:{{position:'bottom'}}}}}}
  }});
}} else {{
  document.getElementById('fishChart').parentElement.innerHTML='<h3>인기 어종 TOP 5</h3><p style="color:#999;text-align:center;padding:40px 0">분석 데이터 대기 중</p>';
}}

new Chart(document.getElementById('durationChart'),{{
  type:'bar',
  data:{{labels:{json.dumps(list(duration_buckets.keys()), ensure_ascii=False)},
  datasets:[{{label:'영상 수',data:{json.dumps(list(duration_buckets.values()))},
  backgroundColor:'#e94560',borderRadius:6}}]}},
  options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{stepSize:1}}}}}}}}
}});

function toggleDetail(idx) {{
  const el = document.getElementById('detail-'+idx);
  if(el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}}
</script>
</body>
</html>"""


def main():
    if not VIDEOS_FILE.exists():
        print("❌ data/videos.json 없음 — 이전 단계를 먼저 실행하세요")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    videos, summary = load_data()
    html = generate_html(videos, summary)
    OUTPUT_FILE.write_text(html, encoding="utf-8")

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"✅ 리포트 생성: {OUTPUT_FILE} ({size_kb:.1f}KB)")


if __name__ == "__main__":
    main()

"""
주제별 주간동향 HWPX 빌더.
처리된 JSON 데이터를 받아 양식 기반 HWPX 문서를 생성한다.
--title 파라미터로 문서 제목을 동적으로 교체한다.

Usage:
  python build_hwpx.py --template 양식.hwpx --output out.hwpx --data items.json --today 26.04.06 --title "AI for Science 분야 국내외 동향"
"""
import json, zipfile, os, html, re, argparse, sys
from difflib import SequenceMatcher


def esc(t):
    return html.escape(str(t), quote=True)


# === 중복 제거 ===

def normalize_title(title):
    """제목을 정규화하여 비교용 문자열 생성."""
    if not title:
        return ""
    t = title.lower().strip()
    t = re.sub(r'[^\w\s]', '', t)  # 구두점 제거
    t = re.sub(r'\s+', ' ', t)     # 연속 공백 통합
    return t


def title_similarity(a, b):
    """두 제목의 유사도 (0.0 ~ 1.0)."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def normalize_url(url):
    """URL 정규화: 프로토콜/trailing slash 제거."""
    if not url:
        return ""
    u = url.strip().rstrip('/')
    u = re.sub(r'^https?://(www\.)?', '', u)
    return u.lower()


def source_priority(item):
    """소스 우선순위: 공식/논문 > 전문매체 > 일반매체."""
    t = item.get("type", "")
    if t == "paper":
        return 0
    if t == "patent":
        return 1
    return 2


def deduplicate(items):
    """중복 항목 제거. URL 동일 또는 제목 80% 이상 유사하면 중복으로 판정."""
    if not items:
        return items, 0

    # URL 기반 중복 제거
    url_groups = {}
    for item in items:
        nurl = normalize_url(item.get("url", ""))
        if nurl in url_groups:
            # 더 상세한 summary를 가진 것 선택
            existing = url_groups[nurl]
            if len(item.get("summary", "")) > len(existing.get("summary", "")):
                url_groups[nurl] = item
        else:
            url_groups[nurl] = item

    deduped = list(url_groups.values())

    # 제목 유사도 기반 중복 제거
    final = []
    removed = 0
    for item in deduped:
        is_dup = False
        title_en = item.get("title_en", item.get("title", ""))
        for existing in final:
            existing_title = existing.get("title_en", existing.get("title", ""))
            if title_similarity(title_en, existing_title) >= 0.8:
                # 우선순위 높은 것 유지
                if source_priority(item) < source_priority(existing):
                    final.remove(existing)
                    final.append(item)
                is_dup = True
                break
        if not is_dup:
            final.append(item)
        else:
            removed += 1

    total_removed = len(items) - len(final)
    return final, total_removed


# === 음슴체 변환 ===

def to_noun_ending(text):
    text = text.rstrip(".")
    replacements = [
        (r'을 달성했다$', '을 달성'), (r'를 달성했다$', '를 달성'),
        (r'에 성공했다$', '에 성공'), (r'를 발표했다$', '를 발표'),
        (r'을 발표했다$', '을 발표'), (r'를 시작했다$', '를 시작'),
        (r'을 시작했다$', '을 시작'), (r'를 기록했다$', '를 기록'),
        (r'을 기록했다$', '을 기록'), (r'를 초과했다$', '를 초과'),
        (r'을 초과했다$', '을 초과'), (r'를 보였다$', '를 시현'),
        (r'을 보였다$', '을 시현'), (r'를 보여주었다$', '를 시현'),
        (r'을 보여주었다$', '을 시현'), (r'를 구현한다$', '를 구현'),
        (r'을 구현한다$', '을 구현'), (r'를 제안한다$', '를 제안'),
        (r'을 제안한다$', '을 제안'), (r'를 제공한다$', '를 제공'),
        (r'을 제공한다$', '을 제공'), (r'를 해결한다$', '를 해결'),
        (r'을 해결한다$', '을 해결'), (r'를 지원한다$', '를 지원'),
        (r'을 지원한다$', '을 지원'), (r'를 수행한다$', '를 수행'),
        (r'을 수행한다$', '을 수행'),
        (r'를 목표로 한다$', '를 목표'), (r'을 목표로 한다$', '을 목표'),
        (r'를 목표로 하고 있다$', '를 목표'),
        (r'가 가능하다$', '가 가능'), (r'이 가능하다$', '이 가능'),
        (r'고 있다$', '는 중'), (r'중이다$', '중'),
        (r'예정이다$', '예정'), (r'있었다$', '있음'),
        (r'되었다$', '됨'), (r'하였다$', ''),
        (r'했다$', ''), (r'였다$', ''), (r'이다$', ''),
        (r'한다$', ''), (r'된다$', ''), (r'난다$', ''),
    ]
    for pat, rep in replacements:
        new = re.sub(pat, rep, text)
        if new != text:
            return new.rstrip()
    return text


def process_summary(text):
    sentences = re.split(r'(?<=\.) ', text)
    result = []
    for s in sentences:
        s = s.strip().rstrip(".")
        s = to_noun_ending(s)
        if s:
            result.append(s)
    return ". ".join(result)


def split_summary(text, limit=120):
    text = process_summary(text)
    if len(text) <= limit:
        return text, ""
    sentences = text.split(". ")
    if len(sentences) > 1:
        return sentences[0], ". ".join(sentences[1:])
    return text[:limit], text[limit:]


def dedup_source_in_title(source, title):
    if not source:
        return title
    for sep in [", ", " "]:
        prefix = source + sep
        if title.startswith(prefix):
            return title[len(prefix):]
    return title


# === HWPX XML builders ===

_field_id = [2000000000]
_field_seq = [627600491]
def next_field_id():
    _field_id[0] += 1
    return _field_id[0]


def make_url_para_with_link(url):
    fid = next_field_id()
    cmd_url = url.replace(":", "\\:") + ";1;0;0;"
    return (
        '  <hp:p id="0" paraPrIDRef="35" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">\n'
        '    <hp:run charPrIDRef="32">\n'
        '      <hp:t>   \u203b </hp:t>\n'
        '      <hp:ctrl>\n'
        f'        <hp:fieldBegin id="{fid}" type="HYPERLINK" name="" editable="0" dirty="1" zorder="-1" fieldid="{_field_seq[0]}">\n'
        '          <hp:parameters cnt="6" name="">\n'
        '            <hp:integerParam name="Prop">0</hp:integerParam>\n'
        f'            <hp:stringParam name="Command">{esc(cmd_url)}</hp:stringParam>\n'
        f'            <hp:stringParam name="Path">{esc(url)}</hp:stringParam>\n'
        '            <hp:stringParam name="Category">HWPHYPERLINK_TYPE_URL</hp:stringParam>\n'
        '            <hp:stringParam name="TargetType">HWPHYPERLINK_TARGET_BOOKMARK</hp:stringParam>\n'
        '            <hp:stringParam name="DocOpenType">HWPHYPERLINK_JUMP_CURRENTTAB</hp:stringParam>\n'
        '          </hp:parameters>\n'
        '        </hp:fieldBegin>\n'
        '      </hp:ctrl>\n'
        f'      <hp:t>{esc(url)}</hp:t>\n'
        '      <hp:ctrl>\n'
        f'        <hp:fieldEnd beginIDRef="{fid}" fieldid="{_field_seq[0]}"/>\n'
        '      </hp:ctrl>\n'
        '    </hp:run>\n'
        '    <hp:linesegarray>\n'
        '      <hp:lineseg textpos="0" vertpos="0" vertsize="1200" textheight="1200" baseline="1020" spacing="360" horzpos="0" horzsize="51024" flags="393216"/>\n'
        '    </hp:linesegarray>\n'
        '  </hp:p>'
    )


def make_entry(source, title, date_str, url, summary, detail=""):
    parts = date_str.split("-")
    if len(parts) == 3:
        mm_dd = f"{int(parts[1])}.{int(parts[2])}"
    else:
        mm_dd = date_str
    lines = []
    lines.append(
        '  <hp:p id="0" paraPrIDRef="33" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">\n'
        '    <hp:run charPrIDRef="34">\n'
        f'      <hp:t> \u25a1 {esc(source)}, {esc(title)}</hp:t>\n'
        '    </hp:run>\n'
        '    <hp:run charPrIDRef="35">\n'
        f'      <hp:t>({esc(mm_dd)})</hp:t>\n'
        '    </hp:run>\n'
        '    <hp:linesegarray>\n'
        '      <hp:lineseg textpos="0" vertpos="0" vertsize="1400" textheight="1400" baseline="1190" spacing="772" horzpos="0" horzsize="51024" flags="393216"/>\n'
        '    </hp:linesegarray>\n'
        '  </hp:p>'
    )
    lines.append(make_url_para_with_link(url))
    lines.append(
        '  <hp:p id="0" paraPrIDRef="36" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">\n'
        '    <hp:run charPrIDRef="30">\n'
        f'      <hp:t>  \u25cb {esc(summary)}</hp:t>\n'
        '    </hp:run>\n'
        '    <hp:linesegarray>\n'
        '      <hp:lineseg textpos="0" vertpos="0" vertsize="1400" textheight="1400" baseline="1190" spacing="772" horzpos="0" horzsize="51024" flags="393216"/>\n'
        '    </hp:linesegarray>\n'
        '  </hp:p>'
    )
    if detail:
        lines.append(
            '  <hp:p id="0" paraPrIDRef="36" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">\n'
            '    <hp:run charPrIDRef="30">\n'
            f'      <hp:t>    - {esc(detail)}</hp:t>\n'
            '    </hp:run>\n'
            '    <hp:linesegarray>\n'
            '      <hp:lineseg textpos="0" vertpos="0" vertsize="1400" textheight="1400" baseline="1190" spacing="772" horzpos="0" horzsize="51024" flags="393216"/>\n'
            '    </hp:linesegarray>\n'
            '  </hp:p>'
        )
    return "\n".join(lines)


def empty_para():
    return (
        '  <hp:p id="0" paraPrIDRef="34" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">\n'
        '    <hp:run charPrIDRef="30"/>\n'
        '    <hp:linesegarray>\n'
        '      <hp:lineseg textpos="0" vertpos="0" vertsize="1400" textheight="1400" baseline="1190" spacing="700" horzpos="0" horzsize="51024" flags="393216"/>\n'
        '    </hp:linesegarray>\n'
        '  </hp:p>'
    )


def build(template_path, output_path, items, today_str, title=None):
    """Build HWPX from template and processed items."""
    with zipfile.ZipFile(template_path, "r") as zin:
        section_xml = zin.read("Contents/section0.xml").decode("utf-8")
        header_xml = zin.read("Contents/header.xml").decode("utf-8")

    # Replace document title if --title provided
    if title:
        section_xml = section_xml.replace("휴머노이드 분야 국내외 동향", title)

    # Extract section header (up to empty para after date line)
    marker = 'charPrIDRef="33"/>'
    idx = section_xml.find(marker)
    end_p = section_xml.find("</hp:p>", idx) + len("</hp:p>")
    header_part = section_xml[:end_p]

    # Fix character spacing: body charPrs -> spacing=0, URL keeps -5
    for cid in ["30", "34", "35", "36", "37", "38", "39"]:
        pattern = f'<hh:charPr id="{cid}"'
        pos = header_xml.find(pattern)
        if pos >= 0:
            sp_start = header_xml.find('<hh:spacing', pos)
            sp_end = header_xml.find('/>', sp_start) + 2
            if sp_start >= 0 and sp_start < pos + 500:
                new_spacing = '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
                header_xml = header_xml[:sp_start] + new_spacing + header_xml[sp_end:]

    # Add charPr id=40 for hyperlink (blue, underline)
    new_charpr = '''      <hh:charPr id="40" height="1200" textColor="#0000FF" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
        <hh:fontRef hangul="4" latin="4" hanja="4" japanese="4" other="4" symbol="4" user="4"/>
        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
        <hh:spacing hangul="-5" latin="-5" hanja="-5" japanese="-5" other="-5" symbol="-5" user="-5"/>
        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
        <hh:underline type="BOTTOM" shape="SOLID" color="#0000FF"/>
        <hh:strikeout shape="NONE" color="#000000"/>
        <hh:outline type="NONE"/>
        <hh:shadow type="NONE" color="#B2B2B2" offsetX="10" offsetY="10"/>
      </hh:charPr>'''
    header_xml = header_xml.replace('itemCnt="40"', 'itemCnt="41"')
    header_xml = header_xml.replace('</hh:charProperties>', new_charpr + '\n    </hh:charProperties>')

    # Sort items by date descending
    items.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Build entries
    entries = [empty_para()]
    for item in items:
        summ, det = split_summary(item.get("summary", ""))
        title_clean = dedup_source_in_title(item.get("source", ""), item.get("title", ""))
        entries.append(make_entry(
            item.get("source", ""),
            title_clean,
            item.get("date", ""),
            item.get("url", ""),
            summ, det
        ))
    entries.append(empty_para())

    # Assemble section
    new_section = header_part + "\n" + "\n".join(entries) + "\n</hs:sec>\n"
    new_section = new_section.replace("{오늘날짜YY.MM.DD}", today_str)

    # Write HWPX
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    tmp = output_path + ".tmp"
    with zipfile.ZipFile(template_path, "r") as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item_info in zin.infolist():
                data = zin.read(item_info.filename)
                if item_info.filename == "Contents/section0.xml":
                    data = new_section.encode("utf-8")
                elif item_info.filename == "Contents/header.xml":
                    data = header_xml.encode("utf-8")
                if item_info.filename == "mimetype":
                    zout.writestr(item_info, data, compress_type=zipfile.ZIP_STORED)
                else:
                    zout.writestr(item_info, data)
    os.replace(tmp, output_path)
    return len(items)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="주제별 주간동향 HWPX 빌더")
    parser.add_argument("--template", required=True, help="HWPX 양식 파일 경로")
    parser.add_argument("--output", required=True, help="출력 HWPX 파일 경로")
    parser.add_argument("--data", required=True, help="JSON array of {source, title, date, url, summary}")
    parser.add_argument("--today", required=True, help="YY.MM.DD format")
    parser.add_argument("--title", default=None, help="문서 제목 (양식의 '휴머노이드 분야 국내외 동향'을 교체)")
    parser.add_argument("--dedup", action="store_true", default=True, help="중복 제거 수행 (기본: True)")
    parser.add_argument("--no-dedup", action="store_false", dest="dedup", help="중복 제거 건너뛰기")
    args = parser.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        items = json.load(f)

    original_count = len(items)

    if args.dedup:
        items, removed = deduplicate(items)
        if removed > 0:
            print(f"Dedup: {removed} duplicates removed ({original_count} -> {len(items)})")

    count = build(args.template, args.output, items, args.today, args.title)
    print(f"Generated: {args.output}")
    print(f"Total entries: {count}")

"""
누락된 문제(EMPTY) 재추출 스크립트
- 기존 auto_extract에서 놓친 문제들을 재추출
- 개선된 OCR 패턴 매칭 + 인접 문제 위치 기반 갭 분석
"""
import sqlite3
import json
import os
import re
import easyocr
from PIL import Image

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exam.db')
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
IMAGES_DIR = os.path.join(STATIC_DIR, 'images')
QUESTIONS_DIR = os.path.join(IMAGES_DIR, 'questions')
os.makedirs(QUESTIONS_DIR, exist_ok=True)

reader = easyocr.Reader(['ko', 'en'], gpu=False)


def find_question_markers_improved(image_path):
    """개선된 문제 마커 탐지 - 더 넓은 패턴 매칭"""
    results = reader.readtext(image_path, detail=1)
    markers = []

    for (bbox, text, conf) in results:
        text_clean = text.replace(' ', '').replace('\n', '')

        # 다양한 패턴: 【문제N】, [문제N], 문제N, 문제N], 【문제N, (문제N)
        patterns = [
            r'[【\[\(]?\s*문제\s*(\d+)\s*[】\]\)]?',
            r'문제\s*(\d+)',
            r'[【\[]문제(\d+)',
            r'問題\s*(\d+)',  # 한자 표기
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                q_num = int(match.group(1))
                if 1 <= q_num <= 10:  # 합리적 범위
                    y_top = min(pt[1] for pt in bbox)
                    y_bottom = max(pt[1] for pt in bbox)
                    markers.append({
                        'question_num': q_num,
                        'y_top': int(y_top),
                        'y_bottom': int(y_bottom),
                        'text': text,
                        'confidence': conf
                    })
                break

    # 중복 제거
    seen = {}
    for m in markers:
        qn = m['question_num']
        if qn not in seen or m['confidence'] > seen[qn]['confidence']:
            seen[qn] = m

    return sorted(seen.values(), key=lambda x: x['y_top'])


def get_existing_questions(conn, year, subject_order):
    """이미 추출된 문제들의 이미지 경로 조회"""
    rows = conn.execute(
        "SELECT question_num, question_image_paths FROM questions "
        "WHERE year = ? AND subject_order = ? ORDER BY question_num",
        (year, subject_order)
    ).fetchall()
    result = {}
    for r in rows:
        imgs = json.loads(r[1]) if r[1] else []
        result[r[0]] = imgs
    return result


def get_page_images(year, subject_order):
    """해당 연도/교시의 페이지 이미지 경로 목록"""
    session_name = f"{year}_{subject_order}교시"
    pages = []
    for i in range(1, 10):
        p = os.path.join(IMAGES_DIR, f"{session_name}_p{i}.png")
        if os.path.exists(p):
            pages.append(p)
    return pages


def extract_missing_for_session(year, subject_order, missing_nums):
    """한 교시의 누락된 문제들 추출"""
    session_name = f"{year}_{subject_order}교시"
    print(f"\n=== {session_name} (missing: {missing_nums}) ===")

    pages = get_page_images(year, subject_order)
    if not pages:
        print(f"  No pages found")
        return

    # 모든 페이지에서 문제 마커 재탐지
    page_data = []
    all_markers = []
    for pi, page_path in enumerate(pages):
        img = Image.open(page_path)
        w, h = img.size
        markers = find_question_markers_improved(page_path)
        page_name = os.path.basename(page_path)
        print(f"  {page_name} ({w}x{h}): markers {[m['question_num'] for m in markers]}")
        pd = {'path': page_path, 'width': w, 'height': h, 'markers': markers}
        page_data.append(pd)

        for m in markers:
            all_markers.append({**m, 'page_index': pi, 'page_width': w, 'page_height': h})

    if not all_markers:
        print(f"  WARNING: No markers found at all!")
        return

    detected_nums = sorted(set(m['question_num'] for m in all_markers))
    print(f"  Detected question nums: {detected_nums}")

    # 전체 문제 수 (보통 6문제)
    conn = sqlite3.connect(DB_PATH)
    total_q = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE year = ? AND subject_order = ?",
        (year, subject_order)
    ).fetchone()[0]
    all_expected = list(range(1, total_q + 1))

    # 각 문제의 영역 결정 (기존 + 신규 모두)
    question_regions = {}

    for i, marker in enumerate(all_markers):
        q_num = marker['question_num']
        start_page = marker['page_index']
        start_y = max(0, marker['y_top'] - 15)

        if i + 1 < len(all_markers):
            next_marker = all_markers[i + 1]
            end_page = next_marker['page_index']
            end_y = max(0, next_marker['y_top'] - 30)
        else:
            end_page = len(page_data) - 1
            end_y = page_data[end_page]['height'] - 100

        question_regions[q_num] = {
            'question_num': q_num,
            'start_page': start_page,
            'start_y': start_y,
            'end_page': end_page,
            'end_y': end_y
        }

    # 누락된 문제 처리
    for q_num in missing_nums:
        if q_num in question_regions:
            qr = question_regions[q_num]
            print(f"  문제{q_num}: Found marker -> cropping")
        else:
            # 마커가 감지 안된 경우: 인접 문제 사이의 갭 분석
            print(f"  문제{q_num}: No marker found, inferring from neighbors")

            # 이전 문제와 다음 문제의 위치 찾기
            prev_q = None
            next_q = None
            for qn in sorted(question_regions.keys()):
                if qn < q_num:
                    prev_q = qn
                elif qn > q_num and next_q is None:
                    next_q = qn

            if prev_q and next_q:
                # 두 이웃 사이의 공간
                pr = question_regions[prev_q]
                nr = question_regions[next_q]

                # 이전 문제의 영역 끝에서 다음 문제의 시작까지
                # 이전 문제 영역의 중간부터 다음 문제 시작까지
                if pr['end_page'] == nr['start_page']:
                    # 같은 페이지
                    mid_y = (pr['start_y'] + nr['start_y']) // 2
                    qr = {
                        'question_num': q_num,
                        'start_page': pr['end_page'],
                        'start_y': mid_y,
                        'end_page': nr['start_page'],
                        'end_y': max(0, nr['start_y'] - 30)
                    }
                else:
                    # 페이지 경계
                    # 이전 문제 페이지의 하단부터 다음 문제 페이지의 시작까지
                    mid_y_prev = (pr['start_y'] + page_data[pr['start_page']]['height']) // 2
                    qr = {
                        'question_num': q_num,
                        'start_page': pr['start_page'],
                        'start_y': mid_y_prev,
                        'end_page': nr['start_page'],
                        'end_y': max(0, nr['start_y'] - 30)
                    }
            elif prev_q:
                # 마지막 문제
                pr = question_regions[prev_q]
                last_page = len(page_data) - 1

                if pr['end_page'] == last_page:
                    mid_y = (pr['start_y'] + page_data[last_page]['height']) // 2
                    qr = {
                        'question_num': q_num,
                        'start_page': last_page,
                        'start_y': mid_y,
                        'end_page': last_page,
                        'end_y': page_data[last_page]['height'] - 100
                    }
                else:
                    qr = {
                        'question_num': q_num,
                        'start_page': pr['end_page'],
                        'start_y': page_data[pr['end_page']]['height'] // 2,
                        'end_page': last_page,
                        'end_y': page_data[last_page]['height'] - 100
                    }
            elif next_q:
                # 첫 문제
                nr = question_regions[next_q]
                qr = {
                    'question_num': q_num,
                    'start_page': 0,
                    'start_y': 30,
                    'end_page': nr['start_page'],
                    'end_y': max(0, nr['start_y'] - 30)
                }
            else:
                print(f"  문제{q_num}: Cannot determine region, skipping")
                continue

        # 크롭 실행
        crop_images = crop_question(page_data, qr, year, subject_order)
        if crop_images:
            conn.execute(
                "UPDATE questions SET question_image_paths = ? "
                "WHERE year = ? AND subject_order = ? AND question_num = ?",
                (json.dumps(crop_images), year, subject_order, q_num)
            )
            print(f"  문제{q_num}: Saved {len(crop_images)} crop images")

    conn.commit()
    conn.close()


def crop_question(page_data, qr, year, subject_order):
    """문제 영역을 크롭하여 저장"""
    q_num = qr['question_num']
    crop_images = []

    if qr['start_page'] == qr['end_page']:
        pi = qr['start_page']
        pd = page_data[pi]
        img = Image.open(pd['path'])

        start_y = max(0, qr['start_y'])
        end_y = min(pd['height'], qr['end_y'])

        if end_y <= start_y + 50:
            print(f"  문제{q_num}: Crop area too small ({start_y}-{end_y}), skipping")
            return []

        crop_box = (50, start_y, pd['width'] - 50, end_y)
        cropped = img.crop(crop_box)
        out_name = f"{year}_{subject_order}_q{q_num}.png"
        out_path = os.path.join(QUESTIONS_DIR, out_name)
        cropped.save(out_path, 'PNG')
        crop_images.append(f"images/questions/{out_name}")
        print(f"    -> {out_name} (page{pi+1}, y={start_y}-{end_y})")
    else:
        for pi in range(qr['start_page'], qr['end_page'] + 1):
            pd = page_data[pi]
            img = Image.open(pd['path'])

            if pi == qr['start_page']:
                y_start = max(0, qr['start_y'])
                y_end = pd['height'] - 100
            elif pi == qr['end_page']:
                y_start = 30
                y_end = min(pd['height'], qr['end_y'])
            else:
                y_start = 30
                y_end = pd['height'] - 100

            if y_end <= y_start + 50:
                continue

            crop_box = (50, y_start, pd['width'] - 50, y_end)
            cropped = img.crop(crop_box)

            suffix = chr(ord('a') + (pi - qr['start_page']))
            out_name = f"{year}_{subject_order}_q{q_num}{suffix}.png"
            out_path = os.path.join(QUESTIONS_DIR, out_name)
            cropped.save(out_path, 'PNG')
            crop_images.append(f"images/questions/{out_name}")
            print(f"    -> {out_name} (page{pi+1}, y={y_start}-{y_end})")

    return crop_images


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # EMPTY 문제 조회
    rows = conn.execute("""
        SELECT year, subject_order, question_num
        FROM questions
        WHERE (question_image_paths IS NULL OR question_image_paths = '[]' OR question_image_paths = '')
        ORDER BY year, subject_order, question_num
    """).fetchall()

    # 교시별로 그룹화
    sessions = {}
    for r in rows:
        key = (r['year'], r['subject_order'])
        if key not in sessions:
            sessions[key] = []
        sessions[key].append(r['question_num'])

    conn.close()

    print(f"Found {len(rows)} EMPTY questions in {len(sessions)} sessions")

    for (year, subject_order), missing_nums in sorted(sessions.items()):
        try:
            extract_missing_for_session(year, subject_order, missing_nums)
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()

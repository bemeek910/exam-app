"""
자동 문제 추출 스크립트
- easyocr로 각 페이지에서 【문제 N】 위치를 감지
- 문제별로 이미지를 크롭하여 저장
- DB에 question_text, question_image_paths 업데이트
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

# Initialize easyocr reader (Korean + English)
reader = easyocr.Reader(['ko', 'en'], gpu=False)


def find_question_markers(image_path):
    """이미지에서 【문제 N】 위치를 찾아 반환"""
    results = reader.readtext(image_path, detail=1)
    markers = []

    for (bbox, text, conf) in results:
        # 【문제 또는 [ 문제 또는 [문제 패턴 매칭
        # bbox: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        text_clean = text.replace(' ', '')

        # 문제 번호 추출
        match = re.search(r'[【\[]?\s*문제\s*(\d+)\s*[】\]]?', text)
        if match:
            q_num = int(match.group(1))
            y_top = min(pt[1] for pt in bbox)
            y_bottom = max(pt[1] for pt in bbox)
            markers.append({
                'question_num': q_num,
                'y_top': int(y_top),
                'y_bottom': int(y_bottom),
                'text': text,
                'confidence': conf
            })

    # 중복 제거 (같은 문제번호가 여러번 감지될 수 있음)
    seen = {}
    for m in markers:
        qn = m['question_num']
        if qn not in seen or m['confidence'] > seen[qn]['confidence']:
            seen[qn] = m

    return sorted(seen.values(), key=lambda x: x['y_top'])


def get_page_images(year, subject_order):
    """해당 연도/교시의 페이지 이미지 경로 목록 반환"""
    session_name = f"{year}_{subject_order}교시"
    pages = []
    for i in range(1, 10):
        p = os.path.join(IMAGES_DIR, f"{session_name}_p{i}.png")
        if os.path.exists(p):
            pages.append(p)
    return pages


def extract_session(year, subject_order, dry_run=False):
    """한 교시의 모든 문제를 추출"""
    session_name = f"{year}_{subject_order}교시"
    print(f"\n=== {session_name} ===")

    pages = get_page_images(year, subject_order)
    if not pages:
        print(f"  No pages found for {session_name}")
        return

    # 각 페이지에서 문제 마커 찾기
    page_data = []
    for page_path in pages:
        img = Image.open(page_path)
        w, h = img.size
        markers = find_question_markers(page_path)
        page_name = os.path.basename(page_path)
        print(f"  {page_name} ({w}x{h}): found markers {[m['question_num'] for m in markers]}")
        page_data.append({
            'path': page_path,
            'width': w,
            'height': h,
            'markers': markers,
            'rel_path': f"images/{os.path.basename(page_path)}"
        })

    # 모든 마커를 페이지 순서대로 정리
    all_markers = []
    for pi, pd in enumerate(page_data):
        for m in pd['markers']:
            all_markers.append({
                **m,
                'page_index': pi,
                'page_path': pd['path'],
                'page_width': pd['width'],
                'page_height': pd['height'],
                'page_rel': pd['rel_path']
            })

    if not all_markers:
        print(f"  WARNING: No question markers found!")
        return

    print(f"  Total markers found: {[m['question_num'] for m in all_markers]}")

    # 각 문제의 시작/끝 영역 결정
    question_regions = []
    for i, marker in enumerate(all_markers):
        q_num = marker['question_num']
        start_page = marker['page_index']
        start_y = max(0, marker['y_top'] - 15)  # 약간의 여유

        if i + 1 < len(all_markers):
            next_marker = all_markers[i + 1]
            end_page = next_marker['page_index']
            end_y = max(0, next_marker['y_top'] - 30)  # 다음 문제 시작 전까지
        else:
            # 마지막 문제: 마지막 페이지 끝까지
            end_page = len(page_data) - 1
            end_y = page_data[end_page]['height'] - 100  # 푸터 제외

        question_regions.append({
            'question_num': q_num,
            'start_page': start_page,
            'start_y': start_y,
            'end_page': end_page,
            'end_y': end_y
        })

    if dry_run:
        for qr in question_regions:
            print(f"  문제{qr['question_num']}: page{qr['start_page']+1} y={qr['start_y']} -> page{qr['end_page']+1} y={qr['end_y']}")
        return

    # 크롭 및 DB 업데이트
    conn = sqlite3.connect(DB_PATH)

    for qr in question_regions:
        q_num = qr['question_num']
        crop_images = []

        if qr['start_page'] == qr['end_page']:
            # 같은 페이지 내 문제
            pi = qr['start_page']
            pd = page_data[pi]
            img = Image.open(pd['path'])

            crop_box = (50, qr['start_y'], pd['width'] - 50, qr['end_y'])
            cropped = img.crop(crop_box)

            out_name = f"{year}_{subject_order}_q{q_num}.png"
            out_path = os.path.join(QUESTIONS_DIR, out_name)
            cropped.save(out_path, 'PNG')
            crop_images.append(f"images/questions/{out_name}")
            print(f"  문제{q_num}: {out_name} (page{pi+1}, y={qr['start_y']}-{qr['end_y']})")
        else:
            # 여러 페이지에 걸친 문제
            for pi in range(qr['start_page'], qr['end_page'] + 1):
                pd = page_data[pi]
                img = Image.open(pd['path'])

                if pi == qr['start_page']:
                    y_start = qr['start_y']
                    y_end = pd['height'] - 100  # 푸터 제외
                elif pi == qr['end_page']:
                    y_start = 30
                    y_end = qr['end_y']
                else:
                    y_start = 30
                    y_end = pd['height'] - 100

                crop_box = (50, y_start, pd['width'] - 50, y_end)
                cropped = img.crop(crop_box)

                suffix = chr(ord('a') + (pi - qr['start_page']))
                out_name = f"{year}_{subject_order}_q{q_num}{suffix}.png"
                out_path = os.path.join(QUESTIONS_DIR, out_name)
                cropped.save(out_path, 'PNG')
                crop_images.append(f"images/questions/{out_name}")
                print(f"  문제{q_num}: {out_name} (page{pi+1}, y={y_start}-{y_end})")

        # DB 업데이트 - question_text는 빈 문자열로, question_image_paths에 크롭 이미지 저장
        conn.execute(
            "UPDATE questions SET question_image_paths = ? "
            "WHERE year = ? AND subject_order = ? AND question_num = ?",
            (json.dumps(crop_images), year, subject_order, q_num)
        )

    conn.commit()
    conn.close()
    print(f"  Done: {session_name} ({len(question_regions)} questions)")


def extract_all_remaining():
    """아직 추출되지 않은 모든 연도/교시 처리"""
    conn = sqlite3.connect(DB_PATH)

    # 아직 question_image_paths가 비어있는 연도/교시 조회
    rows = conn.execute("""
        SELECT DISTINCT year, subject_order
        FROM questions
        WHERE (question_image_paths IS NULL OR question_image_paths = '[]' OR question_image_paths = '')
        ORDER BY year, subject_order
    """).fetchall()
    conn.close()

    print(f"Processing {len(rows)} sessions...")

    for year, subject_order in rows:
        try:
            extract_session(year, subject_order)
        except Exception as e:
            print(f"  ERROR in {year}_{subject_order}교시: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    extract_all_remaining()

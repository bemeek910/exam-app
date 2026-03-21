"""
수동 크롭으로 남은 EMPTY 문제들 보정
- fix_missing_questions.py에서 처리 못한 문제들
- 이미지를 직접 확인하여 정확한 크롭 좌표 지정
"""
import sqlite3
import json
import os
from PIL import Image

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exam.db')
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
IMAGES_DIR = os.path.join(STATIC_DIR, 'images')
QUESTIONS_DIR = os.path.join(IMAGES_DIR, 'questions')
os.makedirs(QUESTIONS_DIR, exist_ok=True)


def crop_and_save(source_rel, crop_box, out_name):
    src = os.path.join(STATIC_DIR, source_rel)
    img = Image.open(src)
    cropped = img.crop(crop_box)
    out_path = os.path.join(QUESTIONS_DIR, out_name)
    cropped.save(out_path, 'PNG')
    print(f"  Cropped: {out_name} from {source_rel} {crop_box}")
    return f"images/questions/{out_name}"


def update_db(conn, year, subject_order, question_num, img_paths):
    conn.execute(
        "UPDATE questions SET question_image_paths = ? "
        "WHERE year = ? AND subject_order = ? AND question_num = ?",
        (json.dumps(img_paths), year, subject_order, question_num)
    )
    print(f"  Updated DB: {year}_{subject_order}교시 문제{question_num} -> {len(img_paths)} images")


def main():
    conn = sqlite3.connect(DB_PATH)

    # 2014_2교시 문제4: p2.png 상단 (문제4는 p2 시작부터 문제5 전까지)
    print("=== 2014_2교시 문제4 ===")
    img = crop_and_save("images/2014_2교시_p2.png", (50, 30, 1600, 560), "2014_2_q4.png")
    update_db(conn, 2014, 2, 4, [img])

    # 2016_3교시 문제3: p1.png 하단 (문제3 CMMI... y~1050에서 페이지 끝)
    print("=== 2016_3교시 문제3 ===")
    img = crop_and_save("images/2016_3교시_p1.png", (50, 1050, 1600, 1250), "2016_3_q3.png")
    update_db(conn, 2016, 3, 3, [img])

    # 2019_1교시 문제2: p2.png 전체 (문제2는 p2 페이지 전체)
    print("=== 2019_1교시 문제2 ===")
    img = crop_and_save("images/2019_1교시_p2.png", (50, 30, 1600, 2200), "2019_1_q2.png")
    update_db(conn, 2019, 1, 2, [img])

    # 2019_1교시 문제4: p3.png 하단 (문제4는 p3의 약 y=780부터)
    print("=== 2019_1교시 문제4 ===")
    img = crop_and_save("images/2019_1교시_p3.png", (50, 760, 1600, 2200), "2019_1_q4.png")
    update_db(conn, 2019, 1, 4, [img])

    # 2020_1교시 문제5: p2.png 중간 (문제5는 y~660 ~ y~1150)
    # 2020_1교시 문제6: p2.png 하단 (문제6는 y~1150 ~ 끝)
    print("=== 2020_1교시 문제5 ===")
    img = crop_and_save("images/2020_1교시_p2.png", (50, 630, 1600, 1150), "2020_1_q5.png")
    update_db(conn, 2020, 1, 5, [img])

    print("=== 2020_1교시 문제6 ===")
    img = crop_and_save("images/2020_1교시_p2.png", (50, 1150, 1600, 2200), "2020_1_q6.png")
    update_db(conn, 2020, 1, 6, [img])

    # 2021_1교시 문제4: p2.png 하단 (문제4 IPSec ~y=1450) + 일부 p3.png 상단 불필요
    # p2.png에서 문제4 전체가 보임 (y=1430 ~ 2200)
    print("=== 2021_1교시 문제4 ===")
    img = crop_and_save("images/2021_1교시_p2.png", (50, 1420, 1600, 2200), "2021_1_q4.png")
    update_db(conn, 2021, 1, 4, [img])

    # 2022_1교시 문제4: p2.png 하단 (문제4 OSI 표현계층 ~ 테이블 포함, y~1100 ~ 끝)
    print("=== 2022_1교시 문제4 ===")
    img = crop_and_save("images/2022_1교시_p2.png", (50, 1080, 1600, 2200), "2022_1_q4.png")
    update_db(conn, 2022, 1, 4, [img])

    # 2024_2교시 문제3: p2.png 하단 (문제3 페이지 부재 ~ y=750부터)
    print("=== 2024_2교시 문제3 ===")
    img = crop_and_save("images/2024_2교시_p2.png", (50, 720, 1600, 2200), "2024_2_q3.png")
    update_db(conn, 2024, 2, 3, [img])

    conn.commit()
    conn.close()
    print("\nDone! All remaining EMPTY questions fixed.")


if __name__ == '__main__':
    main()

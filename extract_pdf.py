"""
기술지도사 2차시험 정보처리 기출문제 PDF -> SQLite 추출 스크립트
OCR 기반으로 확인된 정확한 페이지 매핑 사용
"""
import fitz
import sqlite3
import os
import json

PDF_PATH = r'd:\delete\bruce_project\960.자격증준비\10.기술지도사\비엔피랩\160.기출문제\기술지도사 2차시험 정보처리 문제(2013_2024년).pdf'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, 'static', 'images')
DB_PATH = os.path.join(BASE_DIR, 'exam.db')

# OCR로 확인된 정확한 페이지 매핑 (1-indexed)
# (시작페이지, 끝페이지, 연도, 회차, 교시, 과목명)
PAGE_MAP = [
    (1, 3, 2013, 28, 1, "정보통신개론"),
    (4, 6, 2013, 28, 2, "시스템응용"),
    (7, 9, 2013, 28, 3, "소프트웨어공학"),
    (10, 12, 2014, 29, 1, "정보통신개론"),
    (13, 14, 2014, 29, 2, "시스템응용"),
    (15, 16, 2014, 29, 3, "소프트웨어공학"),
    (17, 19, 2015, 30, 1, "정보통신개론"),
    (20, 21, 2015, 30, 2, "시스템응용"),
    (22, 23, 2015, 30, 3, "소프트웨어공학"),
    (24, 26, 2016, 31, 1, "정보통신개론"),
    (27, 29, 2016, 31, 2, "시스템응용"),
    (30, 31, 2016, 31, 3, "소프트웨어공학"),
    (32, 34, 2017, 32, 1, "정보통신개론"),
    (35, 37, 2017, 32, 2, "시스템응용"),
    (38, 39, 2017, 32, 3, "소프트웨어공학"),
    # page 40: 안내문 (skip)
    (41, 43, 2018, 33, 1, "정보통신개론"),
    # page 44: 안내문 (skip)
    (45, 47, 2018, 33, 2, "시스템응용"),
    # page 48: 안내문 (skip)
    (49, 50, 2018, 33, 3, "소프트웨어공학"),
    # page 51-52: 안내문 (skip)
    (53, 56, 2019, 34, 1, "정보통신개론"),
    # page 57-58: 안내문 (skip)
    (59, 61, 2019, 34, 2, "시스템응용"),
    # page 62: 안내문 (skip)
    (63, 65, 2019, 34, 3, "소프트웨어공학"),
    (66, 67, 2020, 35, 1, "정보통신개론"),
    (68, 71, 2020, 35, 2, "시스템응용"),
    (72, 73, 2020, 35, 3, "소프트웨어공학"),
    (74, 76, 2021, 36, 1, "정보통신개론"),
    (77, 79, 2021, 36, 2, "시스템응용"),
    (80, 82, 2021, 36, 3, "소프트웨어공학"),
    (83, 85, 2022, 37, 1, "정보통신개론"),
    (86, 87, 2022, 37, 2, "시스템응용"),
    (88, 89, 2022, 37, 3, "소프트웨어공학"),
    # 2023년 없음 (PDF에 미포함)
    (90, 91, 2024, 39, 1, "정보통신개론"),
    (92, 95, 2024, 39, 2, "시스템응용"),
    (96, 97, 2024, 39, 3, "소프트웨어공학"),
]


def create_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS questions")
    c.execute("DROP TABLE IF EXISTS pages")
    c.execute("""
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            session_num INTEGER NOT NULL,
            subject_order INTEGER NOT NULL,
            subject_name TEXT NOT NULL,
            page_in_subject INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            pdf_page INTEGER NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            session_num INTEGER NOT NULL,
            subject_order INTEGER NOT NULL,
            subject_name TEXT NOT NULL,
            question_num INTEGER NOT NULL,
            image_paths TEXT,
            question_text TEXT DEFAULT '',
            solution TEXT DEFAULT ''
        )
    """)
    c.execute("CREATE INDEX idx_questions_year ON questions(year)")
    c.execute("CREATE INDEX idx_questions_subject ON questions(subject_name)")
    conn.commit()
    return conn


def extract_and_store():
    doc = fitz.open(PDF_PATH)
    conn = create_db()
    c = conn.cursor()
    print(f"Total PDF pages: {doc.page_count}")

    os.makedirs(IMAGE_DIR, exist_ok=True)

    for start_page, end_page, year, session_num, subject_order, subject_name in PAGE_MAP:
        image_paths = []
        for pdf_page_1idx in range(start_page, end_page + 1):
            pdf_page_0idx = pdf_page_1idx - 1
            page_in_subject = pdf_page_1idx - start_page + 1

            page = doc[pdf_page_0idx]
            pix = page.get_pixmap(dpi=200)
            img_filename = f"{year}_{subject_order}교시_p{page_in_subject}.png"
            img_path = os.path.join(IMAGE_DIR, img_filename)
            pix.save(img_path)
            rel_path = f"images/{img_filename}"
            image_paths.append(rel_path)

            c.execute("""
                INSERT INTO pages (year, session_num, subject_order, subject_name,
                                  page_in_subject, image_path, pdf_page)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (year, session_num, subject_order, subject_name,
                  page_in_subject, rel_path, pdf_page_0idx))

            print(f"  PDF p{pdf_page_1idx}: {year}년 제{session_num}회 "
                  f"{subject_order}교시({subject_name}) p{page_in_subject}")

        # 해당 과목에 6문제 생성
        image_paths_json = json.dumps(image_paths)
        for q_num in range(1, 7):
            c.execute("""
                INSERT INTO questions (year, session_num, subject_order, subject_name,
                                     question_num, image_paths, question_text, solution)
                VALUES (?, ?, ?, ?, ?, ?, '', '')
            """, (year, session_num, subject_order, subject_name,
                  q_num, image_paths_json))

    conn.commit()

    c.execute("SELECT COUNT(*) FROM pages")
    page_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM questions")
    q_count = c.fetchone()[0]
    c.execute("SELECT DISTINCT year FROM questions ORDER BY year")
    years = [r[0] for r in c.fetchall()]

    print(f"\nDone!")
    print(f"Pages in DB: {page_count}")
    print(f"Questions in DB: {q_count}")
    print(f"Years: {years}")

    conn.close()
    doc.close()


if __name__ == '__main__':
    extract_and_store()

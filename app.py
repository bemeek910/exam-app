"""
기술지도사 2차시험 정보처리 기출문제 조회 웹 앱
"""
from flask import Flask, render_template, request, jsonify
import sqlite3
import json
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exam.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    db = get_db()
    years = [r[0] for r in db.execute(
        "SELECT DISTINCT year FROM questions ORDER BY year").fetchall()]
    subjects = [r[0] for r in db.execute(
        "SELECT DISTINCT subject_name FROM questions ORDER BY subject_order").fetchall()]
    db.close()
    return render_template('index.html', years=years, subjects=subjects)


@app.route('/api/questions')
def api_questions():
    year = request.args.get('year', type=int)
    subject = request.args.get('subject', '')

    db = get_db()
    query = "SELECT * FROM questions WHERE 1=1"
    params = []

    if year:
        query += " AND year = ?"
        params.append(year)
    if subject:
        query += " AND subject_name = ?"
        params.append(subject)

    query += " ORDER BY year, subject_order, question_num"
    rows = db.execute(query, params).fetchall()

    results = []
    for r in rows:
        # 개별 문제 이미지가 있으면 사용, 없으면 과목 전체 이미지 사용
        question_image_paths = []
        try:
            question_image_paths = json.loads(r['question_image_paths']) if r['question_image_paths'] else []
        except (KeyError, json.JSONDecodeError):
            pass

        results.append({
            'id': r['id'],
            'year': r['year'],
            'session_num': r['session_num'],
            'subject_order': r['subject_order'],
            'subject_name': r['subject_name'],
            'question_num': r['question_num'],
            'image_paths': json.loads(r['image_paths']) if r['image_paths'] else [],
            'question_image_paths': question_image_paths,
            'question_text': r['question_text'] or '',
            'solution': r['solution'],
        })
    db.close()
    return jsonify(results)


@app.route('/api/solution', methods=['POST'])
def save_solution():
    data = request.json
    qid = data.get('id')
    solution = data.get('solution', '')

    db = get_db()
    db.execute("UPDATE questions SET solution = ? WHERE id = ?", (solution, qid))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/generate_solution', methods=['POST'])
def generate_solution():
    """테스트용: 클로드 API로 풀이 생성 (데모)"""
    data = request.json
    qid = data.get('id')

    db = get_db()
    row = db.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
    if not row:
        db.close()
        return jsonify({'error': 'Question not found'}), 404

    # 실제 Claude API 호출 대신 데모 풀이 생성
    year = row['year']
    subject = row['subject_name']
    q_num = row['question_num']

    demo_solution = f"""## {year}년 {subject} 문제 {q_num} 풀이

이 풀이는 데모용입니다. 실제 운영 시에는 Claude API를 연동하여 자동 풀이를 생성합니다.

### 풀이 방향
- 해당 문제의 핵심 개념을 정리합니다.
- 문제에서 요구하는 사항을 단계별로 답변합니다.
- 배점에 맞게 답안을 구성합니다.

*Claude API 연동 시 이 부분에 AI가 생성한 상세 풀이가 표시됩니다.*"""

    db.execute("UPDATE questions SET solution = ? WHERE id = ?", (demo_solution, qid))
    db.commit()
    db.close()

    return jsonify({'solution': demo_solution})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

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
    qid = request.args.get('id', type=int)
    year = request.args.get('year', type=int)
    subject = request.args.get('subject', '')
    keyword = request.args.get('keyword', '').strip()

    db = get_db()
    query = "SELECT * FROM questions WHERE 1=1"
    params = []

    if qid:
        query += " AND id = ?"
        params.append(qid)
    if year:
        query += " AND year = ?"
        params.append(year)
    if subject:
        query += " AND subject_name = ?"
        params.append(subject)
    if keyword:
        query += " AND (question_text LIKE ? OR solution LIKE ?)"
        params.append(f'%{keyword}%')
        params.append(f'%{keyword}%')

    query += " ORDER BY year DESC, subject_order, question_num"
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


@app.route('/api/autocomplete')
def api_autocomplete():
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify([])

    db = get_db()
    rows = db.execute("""
        SELECT id, year, subject_order, subject_name, question_num, question_text
        FROM questions
        WHERE question_text LIKE ? OR solution LIKE ?
        ORDER BY year DESC, subject_order, question_num
        LIMIT 15
    """, (f'%{q}%', f'%{q}%')).fetchall()

    results = []
    for r in rows:
        text = r['question_text'] or ''
        # 키워드 주변 미리보기 추출
        idx = text.lower().find(q.lower())
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(text), idx + len(q) + 40)
            snippet = ('...' if start > 0 else '') + text[start:end].replace('\n', ' ') + ('...' if end < len(text) else '')
        else:
            snippet = text[:60].replace('\n', ' ') + ('...' if len(text) > 60 else '')

        results.append({
            'id': r['id'],
            'year': r['year'],
            'subject': r['subject_name'],
            'question_num': r['question_num'],
            'label': f"{r['year']}년 {r['subject_order']}교시 {r['subject_name']} Q{r['question_num']}",
            'snippet': snippet,
        })
    db.close()
    return jsonify(results)


@app.route('/api/top_keywords')
def api_top_keywords():
    import re
    from collections import Counter

    # 제외할 일반 단어/시험 용어
    stopwords = {
        # 시험 공통 표현
        '문제', '다음', '물음', '물음에', '답하시오', '설명하시오', '기술하시오', '쓰시오',
        '설명', '하시오', '관한', '관하여', '각각', '가지', '경우', '다음과',
        '것이다', '있다', '한다', '때문', '위한', '위해', '대한', '통해',
        '사용', '이용', '활용', '방법', '개념', '특징', '장점', '단점',
        '비교', '차이', '차이점', '정의', '기능', '구성', '종류', '유형',
        '과정', '절차', '단계', '원리', '목적', '역할', '구조', '방식',
        '이유', '필요성', '중요성', '의미', '표현', '작성', '계산', '구하시오',
        '나열', '열거', '기술', '기술하고', '서술', '제시', '답안', '답변',
        '것을', '수행', '처리', '동작', '실행', '운영', '관리', '제어',
        '시스템', '정보', '데이터', '프로그램', '문장', '조건', '결과',
        '모델', '기법', '기반', '대해', '포함', '해당', '나타', '표시',
        '같은', '이와', '아래', '위의', '그림', '참조', '예를', '들어',
        '주어진', '가정', '가정한다', '것이', '이를', '또한', '그리고',
        '대하여', '가지만', '개념을', '모델의',
        # 배점 관련
        '10점', '20점', '30점', '12점', '15점', '5점', '6점', '4점',
        '3점', '2점', '8점', '7점', '1점',
        # 일반 조사/어미/동사 활용
        '있는', '없는', '하는', '되는', '하고', '하여', '에서', '으로',
        '에는', '에서의', '와의', '간의', '별로', '마다', '부터', '까지',
        '이상', '이하', '이내', '각각의', '모든', '여러', '하나',
        '작성하시오', '쓰고', '논하시오', '답하고',
        '개의', '있을', '없을', '어떤', '이름', '가지를',
        # 일반 단어
        '소프트웨어', '정보처리', '정보기술', '기술지도사',
        '설명하고', '계층의', '갖는', '교시', '정보통신개론', '소프트웨어공학',
        '시스템응용', '모델을', '소프트웨어의', '가지름', '드시', '개념올',
        '단계로', '소작업', '기소지', '알고리증올', '볼록',
        # OCR 잡음/오류
        '씌오', '하씌오', '됩하시오', '기숤하시오', '합하시오',
        '물응', '뭏음', '답하', '잇는', '잇다', '를의',
        '네트위크', '폐이지', '텔레이선', '릴레이선',
    }

    # OCR 오류 보정 매핑
    corrections = {
        '네트위크': '네트워크', '폐이지': '페이지', '텔레이선': '릴레이션',
        '릴레이선': '릴레이션', '스캐줄링': '스케줄링', '스케쥴링': '스케줄링',
        '테스탕': '테스트', '알고리듬': '알고리즘', '리패트랑': '리팩토링',
        '프로토콘': '프로토콜', '프로토글': '프로토콜', '프로토록': '프로토콜',
        '데이타': '데이터', '컴퓨타': '컴퓨터',
        '이유름': '이유를', '스레출림': '스케줄링',
        '트랜책선': '트랜잭션', '컴포년트': '컴포넌트', '프로제트': '프로젝트',
        '결함올': '결함을', '정의름': '정의를', '나열하고': '나열',
        '주소름': '주소를', '교착상': '교착상태', '불렉박스': '블랙박스',
        '레벌': '레벨', '가밧을': '값을', '알고리증올': '알고리즘을',
        '기소지': '기억장치', '개념올': '개념을',
        '아키택처': '아키텍처', '모델에': '모델', '스타일의': '스타일',
        '작업올': '작업을', '방식올': '방식을', '아키': '아키텍처',
        '택처': '아키텍처',
    }
    # 보정 후에도 제외할 단어
    post_stopwords = {'이유를', '결함을', '정의를', '나열', '기관',
                      '정보처리분야', '영화', '스튜디오', '관점',
                      '하나의', '마지막', '단위', '포트', '한국산업인력공단',
                      '번호', '방식에', '방식의', '디지털', '시작',
                      '단점올', '시스템에', '외부', '시간', '사용자',
                      '순서대로', '시스템의', '정의와', '기법에', '기본',
                      '기스지', '처리보아', '주소를', '알고리즘을', '기억장치',
                      '개념을', '값을',
                      '따라', '가밧을', '관계', '다음은', '이다',
                      '정의하고', '자료', '제시하고', '작업', '원칙',
                      '스타일의', '컴퓨터', '구분', '이틀', '위하여',
                      '해당하는', '의미와', '작업올', '작업을', '모델',
                      '채우시오', '방식을', '제시하시오', '각각에', '홍길동',
                      '공학', '택처', '과정올', '모델올', '필요한',
                      '문올', '기스고', '문을', '기업', '다음의', '이용하',
                      '소프트웨어', '있는', '에서', '여러', '관점에서',
                      '쓰고', '완성하시오', '최근', '관련된', '요소들',
                      '이들', '제외한', '관점의', '좋은', '효율적으로',
                      '데이터베이스'}

    db = get_db()
    results = {}

    for session in [1, 2, 3]:
        rows = db.execute(
            "SELECT question_text FROM questions WHERE subject_order = ? AND question_text IS NOT NULL AND question_text != ''",
            (session,)
        ).fetchall()

        counter = Counter()
        for r in rows:
            text = r['question_text']

            # 영문 기술 용어 추출 (2글자 이상 대문자 약어 또는 영문 단어)
            eng_terms = re.findall(r'[A-Za-z][A-Za-z0-9/\-\.]{1,}(?:\s+[A-Za-z][A-Za-z0-9/\-\.]+)*', text)
            for t in eng_terms:
                t = t.strip().strip('.')
                if len(t) >= 2 and t.lower() not in {'the', 'and', 'for', 'that', 'with', 'from', 'this', 'are', 'not', 'but', 'can', 'has', 'its', 'was', 'will', 'all', 'each', 'int', 'byte', 'bit', 'ms', 'ns'}:
                    # 대문자 약어는 그대로, 아니면 원형 유지
                    if t.isupper() and len(t) <= 10:
                        counter[t] += 1
                    elif len(t) >= 3:
                        counter[t] += 1

            # 한글 키워드 추출 (2~8글자 한글 단어)
            ko_words = re.findall(r'[가-힣]{2,8}', text)
            for w in ko_words:
                w = corrections.get(w, w)
                if w not in stopwords and len(w) >= 2:
                    counter[w] += 1

        # 조사 붙은 변형 병합 (예: '암호화를' → '암호화')
        suffix_patterns = ['을', '를', '의', '에', '이', '은', '는', '과', '와', '로', '에서', '으로']
        merged = Counter()
        for word, cnt in counter.items():
            base = word
            for sfx in sorted(suffix_patterns, key=len, reverse=True):
                if word.endswith(sfx) and len(word) - len(sfx) >= 2:
                    candidate = word[:-len(sfx)]
                    if candidate in counter:
                        base = candidate
                        break
            merged[base] += cnt
        # 빈도 2 미만 제거, 상위 30개
        filtered = {k: v for k, v in merged.items() if v >= 2 and k not in stopwords and k not in post_stopwords}
        top30 = sorted(filtered.items(), key=lambda x: -x[1])[:30]
        results[str(session)] = [{'keyword': k, 'count': v} for k, v in top30]

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

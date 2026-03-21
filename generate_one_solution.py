"""
테스트: 하나의 문제에 대해 Claude API로 풀이를 생성하여 DB에 저장
2024년 1교시(정보통신개론) 문제1을 대상으로 테스트
"""
import sqlite3
import os
import json

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exam.db')


def generate_solution_for_question(year, subject_order, question_num):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT * FROM questions
        WHERE year = ? AND subject_order = ? AND question_num = ?
    """, (year, subject_order, question_num)).fetchone()

    if not row:
        print(f"Question not found: {year}년 {subject_order}교시 문제{question_num}")
        conn.close()
        return

    qid = row['id']
    subject_name = row['subject_name']

    print(f"Generating solution for: {year}년 {subject_name} 문제{question_num} (id={qid})")

    # 문제 설명 (2024년 1교시 문제1 - 이미지에서 확인한 내용)
    question_desc = """
2024년도 제39회 기술지도사 2차시험 정보통신개론 문제 1:

【문제 1】인터넷에 관한 다음 물음에 답하시오. (30점)

(1) 아래 구성도에서 호스트(Host), L2 스위치(Switch)의 인터페이스 A, 라우터의
    인터페이스 B에 해당하는 프로토콜 계층 구조를 각각 설명하시오. (10점)
    [구성도: Host - L2 Switch(A) - Router(B) - Internet, Ethernet 연결]

(2) 물리(Physical address), IP 주소, 포트 번호(Port Number)가 사용되는 계층
    및 각각의 용도를 기술하시오. (10점)

(3) 인터넷 프로토콜 TCP와 UDP를 연결설정단계, 오류제어, 흐름제어 기능 측면에서
    비교하여 설명하시오. (10점)
"""

    if HAS_ANTHROPIC:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"""다음은 기술지도사 2차 시험 기출문제입니다.
이 문제에 대한 모범답안을 작성해주세요.
배점에 맞게 상세하게 답변하되, 핵심 개념을 정확하게 설명해주세요.

{question_desc}

답변 형식:
- 각 소문항별로 명확하게 구분하여 답변
- 핵심 키워드와 개념을 포함
- 실제 시험에서 고득점을 받을 수 있는 수준으로 작성
"""
            }]
        )
        solution = message.content[0].text
        print(f"Solution generated ({len(solution)} chars)")
    else:
        print("anthropic 모듈이 없어서 데모 풀이를 생성합니다.")
        solution = f"""## {year}년 {subject_name} 문제 {question_num} 모범답안

### (1) 프로토콜 계층 구조 (10점)

**호스트(Host)의 프로토콜 계층:**
- 응용 계층 (Application Layer): HTTP, FTP, SMTP 등
- 전송 계층 (Transport Layer): TCP, UDP
- 네트워크 계층 (Network Layer): IP
- 데이터 링크 계층 (Data Link Layer): Ethernet (MAC)
- 물리 계층 (Physical Layer): 전기적 신호

**L2 스위치 인터페이스 A:**
- 데이터 링크 계층 (Data Link Layer): Ethernet 프레임 처리, MAC 주소 기반 스위칭
- 물리 계층 (Physical Layer): 전기적 신호 전달
- L2 스위치는 2계층 장비로 MAC 주소 테이블을 기반으로 프레임을 전달

**라우터 인터페이스 B:**
- 네트워크 계층 (Network Layer): IP 패킷 라우팅
- 데이터 링크 계층 (Data Link Layer): Ethernet
- 물리 계층 (Physical Layer): 전기적 신호
- 라우터는 3계층 장비로 IP 주소 기반 라우팅 수행

### (2) 주소 체계와 용도 (10점)

**물리 주소 (Physical Address / MAC Address):**
- 사용 계층: 데이터 링크 계층 (Layer 2)
- 48비트(6바이트) 주소, 16진수로 표현 (예: AA:BB:CC:DD:EE:FF)
- 용도: 같은 네트워크(LAN) 내에서 장치 간 프레임 전달에 사용
- NIC(네트워크 인터페이스 카드)에 고유하게 할당

**IP 주소:**
- 사용 계층: 네트워크 계층 (Layer 3)
- IPv4: 32비트, IPv6: 128비트
- 용도: 서로 다른 네트워크 간 패킷 라우팅에 사용
- 논리적 주소로 네트워크와 호스트를 식별

**포트 번호 (Port Number):**
- 사용 계층: 전송 계층 (Layer 4)
- 16비트 (0~65535)
- 용도: 하나의 호스트에서 실행 중인 여러 프로세스(애플리케이션)를 식별
- Well-known 포트(0-1023): HTTP(80), HTTPS(443), FTP(21) 등

### (3) TCP와 UDP 비교 (10점)

| 구분 | TCP | UDP |
|------|-----|-----|
| **연결 설정** | 연결 지향형(Connection-oriented). 3-Way Handshake(SYN→SYN-ACK→ACK)로 연결 설정, 4-Way Handshake로 연결 해제 | 비연결형(Connectionless). 연결 설정 과정 없이 즉시 데이터 전송 |
| **오류 제어** | 체크섬, 확인응답(ACK), 재전송 메커니즘을 통한 신뢰성 있는 데이터 전달 보장. 손실된 세그먼트 자동 재전송 | 체크섬만으로 기본적인 오류 검출. 오류 발생 시 재전송하지 않음. 상위 계층에서 오류 처리 필요 |
| **흐름 제어** | 슬라이딩 윈도우(Sliding Window) 방식으로 흐름제어 수행. 수신측의 수신 윈도우 크기에 맞춰 전송량 조절 | 흐름 제어 메커니즘 없음. 전송측이 수신측의 처리 능력과 무관하게 데이터 전송 |
"""

    # DB에 저장
    conn.execute("UPDATE questions SET solution = ? WHERE id = ?", (solution, qid))
    conn.commit()
    conn.close()
    print(f"Solution saved to DB for question id={qid}")
    print("\n--- 생성된 풀이 미리보기 ---")
    print(solution[:500] + "...")


if __name__ == '__main__':
    generate_solution_for_question(2024, 1, 1)

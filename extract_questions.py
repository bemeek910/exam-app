"""
문제별 텍스트 및 이미지 추출 스크립트
- 각 문제의 텍스트를 question_text에 저장
- 그림이 포함된 문제는 해당 그림만 크롭하여 별도 이미지로 저장
- question_image_paths에 개별 문제 이미지 경로 저장
"""
import sqlite3
import json
import os
from PIL import Image

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exam.db')
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
IMAGES_DIR = os.path.join(STATIC_DIR, 'images')


def ensure_column_exists():
    """question_image_paths 컬럼이 없으면 추가"""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("SELECT question_image_paths FROM questions LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE questions ADD COLUMN question_image_paths TEXT DEFAULT '[]'")
        conn.commit()
        print("Added question_image_paths column")
    conn.close()


def crop_and_save(source_image_path, crop_box, output_filename):
    """이미지에서 특정 영역을 크롭하여 저장"""
    src = os.path.join(STATIC_DIR, source_image_path)
    out_dir = os.path.join(IMAGES_DIR, 'questions')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, output_filename)

    img = Image.open(src)
    cropped = img.crop(crop_box)
    cropped.save(out_path, 'PNG')
    print(f"  Cropped: {output_filename} ({crop_box})")
    return f"images/questions/{output_filename}"


def update_question(conn, year, subject_order, question_num, question_text, question_image_paths=None):
    """DB에 문제 텍스트 및 이미지 경로 업데이트"""
    if question_image_paths is None:
        question_image_paths = []
    conn.execute(
        "UPDATE questions SET question_text = ?, question_image_paths = ? "
        "WHERE year = ? AND subject_order = ? AND question_num = ?",
        (question_text, json.dumps(question_image_paths), year, subject_order, question_num)
    )


def extract_2024_1():
    """2024년 1교시 정보통신개론 - 테스트 케이스"""
    print("=== 2024년 1교시 정보통신개론 ===")
    conn = sqlite3.connect(DB_PATH)
    year, subject_order = 2024, 1

    # 문제 1: 네트워크 구성도 포함
    img1 = crop_and_save(
        "images/2024_1교시_p1.png",
        (100, 200, 1550, 600),  # 네트워크 구성도 영역
        "2024_1_q1_fig1.png"
    )
    update_question(conn, year, subject_order, 1,
        "【문제 1】 인터넷에 관한 다음 물음에 답하시오. (30점)\n\n"
        "(1) 아래 구성도에서 호스트(Host), L2 스위치(Switch)의 인터페이스 A, "
        "라우터의 인터페이스 B에 해당하는 프로토콜 계층 구조를 각각 설명하시오. (10점)\n\n"
        "[그림 참조]\n\n"
        "(2) 물리 주소(Physical address), IP 주소, 포트 번호(Port Number)가 사용되는 계층 "
        "및 각각의 용도를 기술하시오. (10점)\n\n"
        "(3) 인터넷 프로토콜 TCP와 UDP를 연결설정단계, 오류제어, 흐름제어 기능 측면에서 "
        "비교하여 설명하시오. (10점)",
        [img1]
    )

    # 문제 2: 변조 다이어그램 포함
    img2 = crop_and_save(
        "images/2024_1교시_p1.png",
        (100, 1250, 1550, 1750),  # 변조 다이어그램 영역
        "2024_1_q2_fig1.png"
    )
    update_question(conn, year, subject_order, 2,
        "【문제 2】 변조(Modulation)에 관한 다음 물음에 답하시오. (30점)\n\n"
        "(1) QPSK와 DQPSK 방식의 차이점을 설명하시오. (8점)\n\n"
        "(2) 아래 그림에서 신호 P(t)의 주파수 스펙트럼(x축: 주파수, y축: 진폭)을 나타내고 "
        "이유를 설명하시오. (단, fc > fm) (10점)\n\n"
        "[그림 참조]\n\n"
        "(3) OFDM(Orthogonal Frequency Division Multiplexing) 전송방식에서 직교의 의미를 "
        "설명하고, 직교성을 확보하기 위한 부반송파(Sub-carrier)간의 주파수 조건을 기술하시오. (12점)",
        [img2]
    )

    # 문제 3: 텍스트만
    update_question(conn, year, subject_order, 3,
        "【문제 3】 신호에 관한 다음 물음에 답하시오. (10점)\n\n"
        "(1) 비트열(Bitstream) 전송에서 지터(Jitter)의 의미를 설명하고, 전송률이 1 Mbps인 "
        "비트열의 지터 규격이 0.1 UI 이하인 경우 최대로 허용되는 지터 값을 구하시오. (7점)\n\n"
        "(2) 전자기파 신호의 주파수가 높을수록 나타나는 현상을 파장, 회절성, 직진성 측면에서 "
        "기술하시오. (3점)",
        []
    )

    # 문제 4: 텍스트만
    update_question(conn, year, subject_order, 4,
        "【문제 4】 IPv6 주소에 관한 다음 물음에 답하시오. (10점)\n\n"
        "(1) 주소 2001:1:1:1::1이 통합(Aggregatable) 글로벌 유니캐스트 주소인 이유를 "
        "설명하시오. (4점)\n\n"
        "(2) 기관에 할당된 주소 블록(Block)이 2001:1:1/48이고 서브넷 ID가 3, 인터페이스 "
        "ID가 1:1:1:1인 호스트의 IPv6 주소를 쓰고, 그 이유를 설명하시오. (6점)",
        []
    )

    # 문제 5: 텍스트만
    update_question(conn, year, subject_order, 5,
        "【문제 5】 터널링(Tunneling) 프로토콜에 관한 다음 물음에 답하시오. (10점)\n\n"
        "(1) 캡슐화(Encapsulating)의 의미와 기능을 설명하시오. (7점)\n\n"
        "(2) 터널링 프로토콜 종류 3가지를 쓰시오. (3점)",
        []
    )

    # 문제 6: 텍스트만
    update_question(conn, year, subject_order, 6,
        "【문제 6】 멀티캐스팅(Multicasting)에 관한 다음 물음에 답하시오. (10점)\n\n"
        "(1) 멀티캐스팅 IP주소에서 그룹(Group) ID가 정의되는 이유를 설명하시오. (4점)\n\n"
        "(2) IGMP 프로토콜의 그룹 관리 기능에 관하여 설명하시오. (6점)",
        []
    )

    conn.commit()
    conn.close()
    print("Done: 2024년 1교시 (6 questions updated)")


def extract_2013_1():
    """2013년 1교시 정보통신개론"""
    print("=== 2013년 1교시 정보통신개론 ===")
    conn = sqlite3.connect(DB_PATH)
    year, subject_order = 2013, 1

    # 문제 1: p1.png 전체가 문제1
    img1 = crop_and_save(
        "images/2013_1교시_p1.png",
        (50, 290, 1600, 2200),
        "2013_1_q1.png"
    )
    update_question(conn, year, subject_order, 1,
        "【문제 1】 장거리 전송 및 다중화 목적으로 정보를 전송하는 방식에는 베이스밴드(Baseband)전송, "
        "브로드밴드(Broadband)전송 및 PCM(Pulse Code Modulation)전송 방식이 있다. "
        "다음 물음에 답하시오. (30점)\n\n"
        "(1) 베이스밴드 전송 방식, 브로드밴드 전송 방식, 그리고 PCM 전송 방식의 개념과 특징을 "
        "각각 설명하시오. (9점)\n\n"
        "(2) 베이스밴드 전송 방식 중 단류 방식, 복류 방식, NRZ(Non Return to Zero) 방식, "
        "RZ(Return to Zero) 방식, 바이폴라(Bipolar) 방식의 개념과 특징을 각각 설명하시오. (13점)\n\n"
        "(3) 디지털 데이터 신호 \"1010110\"에 대한 단류 NRZ 방식, 단류 RZ 방식, 복류 NRZ 방식, "
        "복류 RZ 방식의 디지털 전송 신호 파형을 다음과 같은 형식으로 도시하시오. (8점)\n\n"
        "[그림 참조]",
        [img1]
    )

    # 문제 2: p2.png 상단 (보기 박스 포함)
    img2 = crop_and_save(
        "images/2013_1교시_p2.png",
        (50, 30, 1600, 1080),
        "2013_1_q2.png"
    )
    update_question(conn, year, subject_order, 2,
        "【문제 2】 모바일 어플리케이션 개발 방식에 따른 앱(App)의 형태인 네이티브앱(Native App), "
        "웹앱(Web App), 하이브리드앱(Hybrid App), 클라우드 스트리밍에 대하여 다음의 물음에 답하시오. (30점)\n\n"
        "(1) 위의 4 가지 형태의 앱의 개념 및 특징을 각각 설명하시오. (12점)\n\n"
        "(2) 다음 <보기>에서 제시된 용어들을 해당되는 앱에 각각 나열하시오. (6점)\n"
        "(단, 제시된 용어가 두 가지 이상에 해당할 경우 중복으로 사용하여 나열하시오.)\n\n"
        "[그림 참조]\n\n"
        "(3) 위의 4 가지 형태의 앱 개발 방식의 장단점을 비교하여 설명하시오. (12점)",
        [img2]
    )

    # 문제 3: p2.png 중하단
    img3 = crop_and_save(
        "images/2013_1교시_p2.png",
        (50, 1150, 1600, 1700),
        "2013_1_q3.png"
    )
    update_question(conn, year, subject_order, 3,
        "【문제 3】 네트워크 접속장치는 인터네트워킹을 위하여 어떤 프로토콜을 사용하느냐에 따라 "
        "리피터(repeater), 허브(hub), 브리지(bridge), 라우터(router), 게이트웨이(gateway) 등을 "
        "사용하며 OSI 참조모델의 프로토콜 각 계층에 매핑될 수 있다. 이러한 네트워크 접속 장치 "
        "5가지를 OSI의 어떤 계층과 연관되는지를 포함하여 기능을 각각 설명하시오. (10점)",
        []
    )

    # 문제 4: p2.png 하단
    img4 = crop_and_save(
        "images/2013_1교시_p2.png",
        (50, 1700, 1600, 2050),
        "2013_1_q4.png"
    )
    update_question(conn, year, subject_order, 4,
        "【문제 4】 최근 활성화되고 있는 영상 콘텐츠 서비스 중에서 OTT(Over The Top)와 "
        "IPTV(Internet Protocol Television)의 차이점과 현재 국내에서 서비스되고 있는 예를 "
        "각각 2가지만 설명하시오. (10점)",
        []
    )

    # 문제 5: p3.png 상단
    img5 = crop_and_save(
        "images/2013_1교시_p3.png",
        (50, 30, 1600, 310),
        "2013_1_q5.png"
    )
    update_question(conn, year, subject_order, 5,
        "【문제 5】 사물지능 통신(Machine to Machine : M2M)에 대하여 다음 물음에 답하시오. (10점)\n\n"
        "(1) 사물지능 통신의 개념을 정의하시오. (4점)\n\n"
        "(2) 사물지능 통신 기술 및 응용 분야에 대해 설명하시오. (6점)",
        []
    )

    # 문제 6: p3.png 중하단 (그래프 + 라우팅 테이블 포함)
    img6 = crop_and_save(
        "images/2013_1교시_p3.png",
        (50, 310, 1600, 2200),
        "2013_1_q6.png"
    )
    update_question(conn, year, subject_order, 6,
        "【문제 6】 Dijkstra의 최소 비용 경로배정(least-cost routing) 알고리즘을 이용하여 "
        "노드 간에 최단경로를 구한다. (10점)\n\n"
        "(1) 다음 그림에서 시작 노드를 s 로 해서 라우팅 테이블을 작성하시오. (5점)\n"
        "(단, 그림에서 아크(arc)에 표시된 숫자는 아크로 연결된 두 노드 사이의 비용(cost)을 의미한다.)\n\n"
        "[그림 참조]\n\n"
        "(2) 알고리즘 적용 과정을 단계별로 라우팅 절차를 도시하시오. (5점)",
        [img6]
    )

    conn.commit()
    conn.close()
    print("Done: 2013년 1교시 (6 questions)")


def extract_2013_2():
    """2013년 2교시 시스템응용"""
    print("=== 2013년 2교시 시스템응용 ===")
    conn = sqlite3.connect(DB_PATH)
    year, subject_order = 2013, 2

    # 문제 1: p1.png 상단~중단 (working set 문제, 수열 포함)
    img1 = crop_and_save(
        "images/2013_2교시_p1.png",
        (50, 290, 1600, 1200),
        "2013_2_q1.png"
    )
    update_question(conn, year, subject_order, 1,
        "【문제 1】 가상기억장치 할당 알고리즘의 하나인 working set 모델에 대하여 다음 물음에 답하시오. (30점)\n\n"
        "(1) working set와 working set 모델의 개념을 설명하시오. (5점)\n\n"
        "(2) 페이지에 대한 참조가 다음과 같을 때 시점 t 의 working set을 구하시오.\n"
        "(단, △은 working set 윈도우 크기(window size)이고 △=10 이다.) (5점)\n\n"
        "[그림 참조]\n\n"
        "(3) 프로세스들의 working set 총합이 가용 프레임의 수를 넘어설 때 운영체제가 수행하는 일을 설명하시오. (10점)\n\n"
        "(4) working set 윈도우 크기 △ 관점에서 working set 모델의 효과를 설명하시오. (10점)",
        [img1]
    )

    # 문제 2: p1.png 하단 + p2.png 상단 (RAID, 테이블 포함) - 2장
    img2a = crop_and_save(
        "images/2013_2교시_p1.png",
        (50, 1200, 1600, 1950),
        "2013_2_q2a.png"
    )
    img2b = crop_and_save(
        "images/2013_2교시_p2.png",
        (50, 30, 1600, 660),
        "2013_2_q2b.png"
    )
    update_question(conn, year, subject_order, 2,
        "【문제 2】 다음은 컴퓨터 시스템에서 저장 장치 기술인 레이드(RAID)의 각 레벨(level)별 "
        "레이드 구조, 특성 및 최소 필요 디스크 수를 설명하고 있다. 레이드 1의 설명을 참고하여 "
        "다음 물음에 답하시오. (30점)\n\n"
        "(1) 각 레이드 레벨의 구조를 그리시오. (10점)\n\n"
        "(2) 각 레이드 레벨의 특성을 설명하시오. (15점)\n\n"
        "(3) 각 레이드 레벨에 대하여 최소 필요 디스크 수를 쓰시오. (5점)\n\n"
        "[그림 참조]",
        [img2a, img2b]
    )

    # 문제 3: p2.png 하단 + p3.png 상단 (관계대수 테이블) - 2장
    img3a = crop_and_save(
        "images/2013_2교시_p2.png",
        (50, 700, 1600, 2200),
        "2013_2_q3a.png"
    )
    img3b = crop_and_save(
        "images/2013_2교시_p3.png",
        (50, 30, 1600, 400),
        "2013_2_q3b.png"
    )
    update_question(conn, year, subject_order, 3,
        "【문제 3】 다음과 같은 테이블에 대하여 물음에 답하시오. (10점)\n\n"
        "[그림 참조]\n\n"
        "(1) 다음 관계대수의 결과 테이블을 구하시오. (2점)\n"
        "    ΠA(R1) ∩ ΠA(R2)\n\n"
        "(2) 다음 관계대수의 결과 테이블을 구하시오. (단, ∞은 자연 조인을 나타낸다.) (4점)\n"
        "    R1∞R2\n\n"
        "(3) 다음 관계대수의 결과 테이블을 구하시오. (2점)\n"
        "    σC=거(R3)\n\n"
        "(4) 관계 대수 R2 × R3의 결과 테이블의 튜플(tuple) 개수를 쓰시오. (2점)",
        [img3a, img3b]
    )

    # 문제 4: p3.png 중단
    update_question(conn, year, subject_order, 4,
        "【문제 4】 중앙처리장치 스케줄링 알고리즘의 성능을 평가하는 기준(performance criteria) "
        "5가지를 설명하고 성능평가 기준 값을 높여야 하는 것과 낮게 해야 하는 것으로 구분하시오. (10점)",
        []
    )

    # 문제 5: p3.png 중단
    update_question(conn, year, subject_order, 5,
        "【문제 5】 시맨틱웹(Semantic Web)에 대한 다음 물음에 답하시오. (10점)\n\n"
        "(1) 시맨틱웹(Semantic Web)과 시맨틱웹의 핵심 구성 요소인 온톨로지(Ontology) 개념을 설명하시오. (6점)\n\n"
        "(2) 시맨틱웹의 활용(응용) 분야에 대해서 설명하시오. (4점)",
        []
    )

    # 문제 6: p3.png 하단
    update_question(conn, year, subject_order, 6,
        "【문제 6】 유료 방송 업계에서 HTML5 기반의 스마트 TV 바람이 불고 있다. "
        "HTML5에 대하여 다음 물음에 답하시오. (10점)\n\n"
        "(1) HTML5 개발 목표를 설명하시오. (2점)\n\n"
        "(2) HTML5 표준의 목적 및 내용을 설명하시오. (3점)\n\n"
        "(3) HTML5 주요특징을 설명하시오. (5점)",
        []
    )

    conn.commit()
    conn.close()
    print("Done: 2013년 2교시 (6 questions)")


def extract_2013_3():
    """2013년 3교시 소프트웨어공학"""
    print("=== 2013년 3교시 소프트웨어공학 ===")
    conn = sqlite3.connect(DB_PATH)
    year, subject_order = 2013, 3

    # 문제 1: p1.png 상단
    img1 = crop_and_save(
        "images/2013_3교시_p1.png",
        (50, 200, 1600, 750),
        "2013_3_q1.png"
    )
    update_question(conn, year, subject_order, 1,
        "【문제 1】 어느 기업에서 소프트웨어 전문가를 채용하려고 한다. 채용 공고에 전문가가 "
        "담당할 업무를 다음의 4가지로 제시하였다. 각각의 업무를 구체적으로 설명하고, "
        "어떤 지식과 기술을 가지고 있는 지원자를 선발해야 하는지 설명하시오. (30점)\n\n"
        "[담당업무]\n"
        "(1) 소프트웨어 구조 설계(Software Architecture Design) (7점)\n"
        "(2) 소프트웨어 재구조화(Software Restructuring) (7점)\n"
        "(3) 도메인 분석(Domain Analysis) (8점)\n"
        "(4) 코드 리팩토링(Code Refactoring) (8점)",
        []
    )

    # 문제 2: p1.png 하단 + p2.png (CPM 네트워크 다이어그램 + 테이블) - 2장
    img2a = crop_and_save(
        "images/2013_3교시_p1.png",
        (50, 750, 1600, 2200),
        "2013_3_q2a.png"
    )
    img2b = crop_and_save(
        "images/2013_3교시_p2.png",
        (50, 30, 1600, 1550),
        "2013_3_q2b.png"
    )
    update_question(conn, year, subject_order, 2,
        "【문제 2】 정보시스템 개발의 일정관리를 위하여 CPM(Critical Path Method) 네트워크를 "
        "이용하는 것이 효율적이다. CPM 네트워크에 대하여 다음 물음에 답하시오. (30점)\n\n"
        "(1) 위의 CPM 네트워크에서 다음 각 노드(Node)에 해당하는 (TE, TL)을 계산하시오. (12점)\n\n"
        "(2) 위의 CPM 네트워크를 사용하여 다음 작업 일정표를 완성하시오. (8점)\n\n"
        "(3) CPM 네트워크의 장점을 5가지 이상 설명하시오. (10점)\n\n"
        "[그림 참조]",
        [img2a, img2b]
    )

    # 문제 3: p3.png 상단
    update_question(conn, year, subject_order, 3,
        "【문제 3】 최근 소프트웨어에 대한 의존도가 높아지면서 소프트웨어 품질의 중요성이 "
        "강조되고 있다. 이와 관련된 다음 물음에 답하시오. (10점)\n\n"
        "(1) ISO에서 요구하고 있는 품질의 개념을 설명하시오. (4점)\n\n"
        "(2) ISO에서 요구하는 품질의 요소들을 설명하시오. (6점)",
        []
    )

    # 문제 4: p3.png 중단
    update_question(conn, year, subject_order, 4,
        "【문제 4】 실제 존재하는 실세계를 그 용도와 관점에 따라 여러 가지 모습 또는 지도로 "
        "나타낼 수 있듯이 소프트웨어 시스템은 크게 세 가지 관점에서 기술될 수 있다. "
        "이들 중에서 한 가지는 기능(function) 관점에서 기술하는 것으로 자료 흐름도를 예로 들 수 있다. "
        "기능 관점을 제외한 두 가지 관점의 내용을 설명하고 각각의 예를 드시오. (10점)",
        []
    )

    # 문제 5: p3.png 중하단
    update_question(conn, year, subject_order, 5,
        "【문제 5】 소프트웨어의 좋은(우수한) 설계는 프로그램을 효율적으로 작성할 수 있도록 하고 "
        "시스템의 변화에 쉽게 적용할 수 있어야 한다. 소프트웨어 설계 단계에서 품질에 영향을 미치는 "
        "요소들은 결합도(coupling), 이해도(understandability), 적응도(adoptability), "
        "독립성(functional independence), 응집도(cohesion) 등이 있다. "
        "이와 관련된 다음 물음에 답하시오. (10점)\n\n"
        "(1) 응집도의 의미를 설명하시오. (5점)\n\n"
        "(2) 좋은 설계를 위해서 이들 요소들 사이에 요구되는 상호관계를 설명하시오. (5점)",
        []
    )

    # 문제 6: p3.png 하단
    update_question(conn, year, subject_order, 6,
        "【문제 6】 현재까지 웹 어플리케이션을 위한 다양한 설계 방법들이 제안되었다. "
        "이와 관련된 다음 물음에 답하시오. (10점)\n\n"
        "(1) 객체지향 하이퍼미디어 설계방법(OOHDM: Objective Oriented Hypermedia "
        "Design Method)의 개념을 설명하시오. (4점)\n\n"
        "(2) OOHDM의 구성요소를 나열하고 설명하시오. (6점)",
        []
    )

    conn.commit()
    conn.close()
    print("Done: 2013년 3교시 (6 questions)")


if __name__ == '__main__':
    ensure_column_exists()
    extract_2013_1()
    extract_2013_2()
    extract_2013_3()

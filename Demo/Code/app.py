from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import oracledb
from datetime import datetime
from email.mime.text import MIMEText
import smtplib

app = Flask(__name__)
app.secret_key = '1234kyb'

# Oracle DB 연결
connection = oracledb.connect(user="d202000826", password="21-76018500KYB", dsn="localhost:1521/xeXDB")

# 공지사항 데이터
notices = [
    {"title": "2025년 여름 이벤트 일정 안내", "date": "2025-06-02"},
    {"title": "서버 점검 공지", "date": "2025-05-03"},
    {"title": "신규 사원 모집 공고", "date": "2025-05-01"},
    {"title": "2025년 봄 맞이 할인 이벤트", "date": "2025-04-15"},
    {"title": "사이트 점검 안내", "date": "2025-04-10"},
    {"title": "고객 서비스 이용 안내", "date": "2025-03-28"},
    {"title": "2025년 여름 시즌 세일 시작", "date": "2025-03-22"},
    {"title": "신규 기능 업데이트", "date": "2025-03-10"},
    {"title": "고객센터 휴무 안내", "date": "2025-02-25"},
    {"title": "2025년 첫 결제 프로모션", "date": "2025-02-15"},
    {"title": "서버 확장 완료 안내", "date": "2025-02-01"},
    {"title": "2025년 고객 만족도 조사", "date": "2025-01-20"},
    {"title": "사내 워크샵 공지", "date": "2025-01-10"},
    {"title": "신규 상품 출시 안내", "date": "2025-01-01"},
    {"title": "2024년 결산 보고", "date": "2024-12-25"},
    {"title": "2024년 연말 행사 안내", "date": "2024-12-15"},
    {"title": "계정 보안 강화 안내", "date": "2024-12-01"},
    {"title": "2025년 신년 맞이 이벤트", "date": "2024-11-25"},
    {"title": "고객 개인정보 보호 공지", "date": "2024-11-10"},
    {"title": "서비스 이용약관 변경 안내", "date": "2024-10-30"}
]

# FAQ 데이터
faqs = [
    {"question": "회원가입은 어떻게 하나요?", "answer": "회원가입은 로그인 페이지지에서 '회원가입' 버튼을 클릭하여 가능합니다."},
    {"question": "제가 예약한 항공편은 어떻게 조회하나요?", "answer": "My Airline -> 나의 예약 내역 메뉴에서 기간을 설정하면 조회 가능합니다."},
    {"question": "항공권을 예약하고 싶어요.", "answer": "CNU Airline -> 항공권 예약 메뉴를 통해 예약 가능합니다."},
    {"question": "결제 오류가 발생했어요.", "answer": "결제 오류 시 고객센터로 문의 주시면 빠르게 처리해 드리겠습니다."}
]

# 관리자 계정
ADMIN_CNO = 'admin'
ADMIN_PASSWORD = '1234'

# 홈 페이지 렌더링 (기본적으로 로그인 페이지로 연결)
@app.route('/')
def home():
    return render_template('login.html')

# 로그인 처리 라우팅
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    # 로그인 요청 처리 (POST)
    cno = request.form['id']
    password = request.form['password']
    
    # 관리자용 페이지로 이동동
    if cno == ADMIN_CNO and password == ADMIN_PASSWORD:
        return render_template('admin.html')
    
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM CUSTOMER WHERE cno=:1 AND passwd=:2", [cno, password])
    user = cursor.fetchone()

    if user:
        # 로그인 성공 -> 세션 저장 후 메인 화면(대시보드)으로 이동
        session['user'] = user[1]
        session['cno'] = user[0]
        return redirect(url_for('dashboard'))
    else:
        # 로그인 실패 시 오류 메시지 전달
        return render_template('login.html', error='로그인 정보가 올바르지 않습니다.')

# 관리자용 통계 질의
@app.route('/load_custoer', methods=['POST'])
def load_customer():
    cursor = connection.cursor()
    cursor.execute("""
    SELECT 
        a.cno, 
        b.name,
        b.passwd,
        b.email,
        b.passportnumber,
        a.cancel_count,
        RANK() OVER (ORDER BY cancel_count DESC) AS cancel_rank
    FROM (
        SELECT 
            cno, 
            COUNT(*) AS cancel_count
        FROM CANCEL
        GROUP BY CNO
    ) a, CUSTOMER b
    WHERE b.cno = a.cno
    ORDER BY cancel_rank
                   """,[])
    
    rows = cursor.fetchall()

    customers = [
    {
        "cno": row[0],
        "name": row[1],
        "email": row[2],
        "password": row[3],
        "passportnumber": row[4],
        "count": row[5],
        "rank": row[6]
    }
    for row in rows
]

    return render_template('admin.html', customers=customers)

# 회원가입 처리 라우팅
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # 입력 정보 수집
        username = request.form['username']
        name = request.form['name']
        password = request.form['password']
        email = request.form['email']
        passport = request.form['passport']

        # DB에 신규 고객 정보 삽입
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO CUSTOMER
            VALUES (:1, :2, :3, :4, :5)
            """, [username, name, password, email, passport]
        )
        connection.commit()

        flash("회원가입이 완료되었습니다!", "success")

    return render_template('signup.html')

# 로그인 후 메인 페이지(대시보드)
@app.route('/main')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))
    return render_template('main.html', user=session['user'])

# 항공권 예약 화면
@app.route('/ticket_reservation')
def ticket_reservation():
    return render_template('ticket_reservation.html', tickets=[])

# 항공권 조회 처리
@app.route('/ticket_find')
def ticket_find():
    # 사용자가 입력한 검색 조건 수집
    departure = request.args.get('departure')
    arrival = request.args.get('arrival')
    departure_date = request.args.get('departure_date')
    seat_class = request.args.get('seat_class')

    cursor = connection.cursor()

    # 정렬 기준 선택
    sort_by = request.args.get("sort_by")

    if sort_by == "time":
        # 항공편 및 좌석 정보 조회 쿼리
        query = """
        SELECT A.flightno, A.departureairport, A.arrivalairport, 
                TO_CHAR(A.departuredatetime, 'YYYY-MM-DD HH24:MI') as departure_time,
                TO_CHAR(A.arrivaldatetime, 'YYYY-MM-DD HH24:MI') as arrival_time,
                S.seatclass, S.price, S.no_of_seats
            FROM AIRPLANE A
            JOIN SEATS S ON A.flightno = S.flightno
            AND A.departuredatetime = S.departuredatetime    
            WHERE A.departureairport = :1
            AND A.arrivalairport = :2
            AND A.departuredatetime BETWEEN TO_DATE(:3, 'YYYY-MM-DD') AND TO_DATE(:4, 'YYYY-MM-DD') + 1
            AND S.seatclass = UPPER(:5)
            ORDER BY S.departuredatetime ASC
        """
    elif sort_by == "price":
        # 항공편 및 좌석 정보 조회 쿼리
        query = """
        SELECT A.flightno, A.departureairport, A.arrivalairport, 
                TO_CHAR(A.departuredatetime, 'YYYY-MM-DD HH24:MI') as departure_time,
                TO_CHAR(A.arrivaldatetime, 'YYYY-MM-DD HH24:MI') as arrival_time,
                S.seatclass, S.price, S.no_of_seats
            FROM AIRPLANE A
            JOIN SEATS S ON A.flightno = S.flightno
            AND A.departuredatetime = S.departuredatetime    
            WHERE A.departureairport = :1
            AND A.arrivalairport = :2
            AND A.departuredatetime BETWEEN TO_DATE(:3, 'YYYY-MM-DD') AND TO_DATE(:4, 'YYYY-MM-DD') + 1
            AND S.seatclass = UPPER(:5)
            ORDER BY S.price ASC
        """
    else: query = ""
    cursor.execute(query, [departure, arrival, departure_date, departure_date, seat_class])
    rows = cursor.fetchall()

    # 결과를 리스트로 정리하여 탬플릿에 전달
    tickets = []
    for row in rows:
        tickets.append({
            'flight_no': row[0],
            'departure': row[1],
            'arrival': row[2],
            'departure_time': row[3],
            'arrival_time': row[4],
            'seat_class': row[5],
            'price': row[6],
            'no_seats': row[7]
        })

    for ticket in tickets:
        query = """
            SELECT COUNT(*)
            FROM RESERVE
            WHERE flightno = :1
            AND departuredatetime = :2
        """
        cursor.execute(query, [(ticket['flight_no']),
                               datetime.strptime(ticket['departure_time'], "%Y-%m-%d %H:%M")])
        number = cursor.fetchone()
        ticket['no_seats'] = int(ticket['no_seats']) - int(number[0])

    return render_template('ticket_reservation.html', tickets=tickets)

# 예약 내역 조회 
@app.route('/reservation_lookup')
def reservation_lookup():
    if 'user' not in session:
        return redirect(url_for('home'))

    cursor = connection.cursor()
    cursor.execute("""
        SELECT a.airline, r.flightno, a.departureairport, a.arrivalairport,
               r.departuredatetime, a.arrivaldatetime, r.payment
        FROM RESERVE r, AIRPLANE a
        WHERE r.CNO = :1
        AND r.flightno = a.flightno
        AND r.departuredatetime = a.departuredatetime
    """, [session['cno']])
    rows = cursor.fetchall()

    reservations = [
        {
            'airline': row[0],
            'flight_number': row[1],
            'departure_airport': row[2],
            'arrival_airport': row[3],
            'departure_time': row[4],
            'arrival_time': row[5],
            'fare': row[6]
        }
        for row in rows
    ]

    return render_template('reservation_lookup.html', reservations=reservations)

# 항공권 예약 처리 
@app.route('/reserve', methods=['POST'])
def reserve():
    if "user" not in session:
        return redirect(url_for('home'))
    
    cursor = connection.cursor()

    # 예약 정보 수집 
    flightno = request.form['flightno']
    departuredatetime_str = request.form['departuredatetime']
    seatclass = request.form['seatclass']
    payment = request.form['payment']
    reservedatetime = datetime.now()
    no_seats = request.form['no_seats']
    print(no_seats)
    if(int(no_seats) <= 0):
        flash("예약할 수 없는 항공편입니다. 다른 항공편을 선택하세요.")
        return redirect("/ticket_reservation")

    # 현재 로그인된 사용자의 CNO, email 확인
    cursor.execute("SELECT cno, email FROM CUSTOMER WHERE name=:1", [session['user']])
    row = cursor.fetchone()
    if not row:
        flash("회원 정보를 찾을 수 없습니다.")
        return redirect("/ticket_reservation")
    cno = row[0]
    email = row[1]

    # 출발 일시 문자열을 datetime 객체로 변경 
    departuredatetime = datetime.strptime(departuredatetime_str, "%Y-%m-%d %H:%M")

    cursor.execute("""
                   INSERT INTO RESERVE VALUES (:1, :2, :3, :4, :5, :6)
                   """, [flightno, departuredatetime, seatclass, payment, reservedatetime, cno])
    
    connection.commit()

    flash("예약이 완료되었습니다.")

    # 탑승권 내용 작성
    ticket_content = f"""
    항공편 예약이 완료되었습니다!

    ▶ 항공편 번호: {flightno}
    ▶ 출발 일시: {departuredatetime}
    ▶ 좌석 등급: {seatclass}
    ▶ 결제 금액: {payment}원

    감사합니다.
    """
    if email:
        send_email(email, "탑승권 예약 완료", ticket_content)

    return redirect("/reservation_lookup")

# 이메일 전송 메커니즘 함수
def send_email(to_email, subject, body):
    # 전송자 정보 하드코딩
    from_email = "kyb8732@gmail.com"
    from_password = "amex jdxn rtbj vnms"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(from_email, from_password)
            smtp.send_message(msg)
        print("이메일 전송 완료")
    except Exception as e:
        print("이메일 전송 실패: ", e)

# 예약 취소 처리 
@app.route('/cancel_reservation', methods=['POST'])
def cancel_reservation():
    if 'user' not in session:
        return redirect(url_for('home'))

    flight_number = request.form['flight_number']
    departure_time = request.form['departure_time']

    try:
        cursor = connection.cursor()
        # Cancel 테이블 업데이트를 위한 취소 대상 항공권 정보 불러오기
        cursor.execute(""" 
            SELECT SEATCLASS, PAYMENT
            FROM RESERVE
            WHERE cno = (
                SELECT cno FROM CUSTOMER WHERE name = :1
            ) AND flightno = :2 AND departuredatetime = TO_DATE(:3, 'YYYY-MM-DD HH24:MI:SS')
        """, [session['user'], flight_number, departure_time])

        row = cursor.fetchone()
        seatclass = row[0]
        payment = row[1] # refund 금액은 무조건 전액 환불로 설정!
        canceldatetime = datetime.now()

        # 해당 예약 정보 삭제 
        cursor.execute("""
            DELETE FROM RESERVE 
            WHERE cno = (
                SELECT cno FROM CUSTOMER WHERE name = :1
            ) AND flightno = :2 AND departuredatetime = TO_DATE(:3, 'YYYY-MM-DD HH24:MI:SS')
        """, [session['user'], flight_number, departure_time])
        connection.commit()

        # 출발 일시 문자열을 datetime 객체로 변경 
        departuredatetime = datetime.strptime(departure_time, "%Y-%m-%d %H:%M:%S")

        # Cancel 테이블에 해당 취소 내역 저장
        cursor.execute("""
            INSERT INTO CANCEL
            VALUES (:1, :2, :3, :4, :5, :6)
            """, [flight_number, departuredatetime, seatclass, payment, canceldatetime, session['cno']])
        connection.commit()

        flash("예약이 성공적으로 취소되었습니다.", "success")
        
    except Exception as e:
        print("예약 취소 오류:", e)
        flash("예약 취소 중 오류가 발생했습니다.", "error")

    return redirect(url_for('reservation_lookup'))

# 사용자 히스토리 조회 페이지 
@app.route("/my_history")
def my_history():
    if 'user' not in session:
        return redirect(url_for('home'))
    return render_template('my_history.html', user=session['user'])

# 히스토리 데이터 반환 
@app.route("/get_my_history")
def get_my_history():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    # 기간 필터 수집 
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    cursor = connection.cursor()
    # 항공권 예약 내역 조회 
    cursor.execute("""
        SELECT a.airline,
        a.departureairport,
        a.arrivalairport,
        a.flightno,
        a.departuredatetime,
        a.arrivaldatetime,
        b.payment,
        b.reservedatetime
        FROM AIRPLANE a
        JOIN RESERVE b
        ON a.flightno = b.flightno
        AND a.departuredatetime = b.departuredatetime
        WHERE a.departuredatetime BETWEEN TO_DATE(:1, 'YYYY-MM-DD HH24:MI:SS')
                                    AND TO_DATE(:2, 'YYYY-MM-DD HH24:MI:SS') + 1
        ORDER BY  a.departuredatetime ASC
                   """, [start_date, end_date])
    rows = cursor.fetchall()

    reservations = [
        {
            'airline': row[0],
            'departure': row[1],
            'arrival': row[2],
            'flight_no': row[3],
            'departure_time': row[4],
            'arrival_time': row[5],
            'payment': row[6],
            'reserved_date': row[7]
        }
        for row in rows
    ]

    cursor.execute("""
        SELECT a.airline,
        a.departureairport,
        a.arrivalairport,
        a.flightno,
        a.departuredatetime,
        a.arrivaldatetime,
        b.refund,
        b.canceldatetime
        FROM AIRPLANE a
        JOIN CANCEL b
        ON a.flightno = b.flightno
        AND a.departuredatetime = b.departuredatetime
        WHERE a.departuredatetime BETWEEN TO_DATE(:1, 'YYYY-MM-DD HH24:MI:SS')
                                    AND TO_DATE(:2, 'YYYY-MM-DD HH24:MI:SS')+1
        ORDER BY  a.departuredatetime ASC
                   """, [start_date, end_date])
    
    rows = cursor.fetchall()
    cancellations = [
        {
            'airline': row[0],
            'departure': row[1],
            'arrival': row[2],
            'flight_no': row[3],
            'departure_time': row[4],
            'arrival_time': row[5],
            'refund': row[6],
            'cancelled_date': row[7]
        }
        for row in rows
    ]
    # JSON 형태로 데이터 탬플릿에 전달 
    return render_template('my_history.html', reservations=reservations, cancellations=cancellations)

# 세션에 로그인된 고객 정보 
@app.route("/customer")
def customer_info():
    if 'user' not in session:
        return redirect(url_for('home'))
    return render_template('customer.html', user=session['user'])

# 공지사항 
@app.route("/notice")
def notice():
    if 'user' not in session:
        return redirect(url_for('home'))
    return render_template('notice.html', user=session['user'])

# FAQ 
@app.route("/faq")
def faq():
    if 'user' not in session:
        return redirect(url_for('home'))
    return render_template('faq.html', user=session['user'])

# 세션에 로그인된 고객 정보 -> 초기 화면    
@app.route("/update_profile")
def update_profile():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT cno, name, passwd, email, passportnumber
        FROM CUSTOMER
        WHERE cno =:1
        """, [session['cno']]
    )

    row = cursor.fetchone()

    user_info = {
        'userid': row[0],
        'name': row[1],
        'email': row[3],
        'passport': row[4]
    }
    return user_info

# 세션에 로그인된 고객 정보 업데이트 -> 업데이트 버튼 클릭 시 
@app.route("/update_customer", methods=['POST'])
def update_customer():
    if 'user' not in session:
        return redirect(url_for('home'))
    
    user_id = request.form['userid']
    password = request.form['password']
    name = request.form['name']
    email = request.form['email']
    passport = request.form['passport']
    print(user_id, password, name, email, passport)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE CUSTOMER
            SET CNO =:1, NAME =:2, PASSWD =:3, EMAIL =:4, PASSPORTNUMBER =:5
            WHERE CNO =:6
            """, [user_id, name, password, email, passport, session['cno']]
        )
        connection.commit()
        flash("고객 정보가 성공적으로 변경됐습니다.", "success")
    except Exception as e:
        print("고객 정보 변경 오류:", e)
        flash("고객 정보 변경경 중 오류가 발생했습니다.", "error")

    return render_template('customer.html', user=session['user'])

# 키워드 기반 공지사항 검색 
@app.route("/get_notice")
def get_notice():
    keyword = request.args.get('keyword', '').lower()  # 입력된 키워드
    if keyword:
        filtered_notices = [notice for notice in notices if keyword in notice['title'].lower()]
    else:
        filtered_notices = notices
    return jsonify(filtered_notices)

# 키워드 기반 FAQ 검색
@app.route('/get_faq', methods=['GET'])
def get_faq():
    keyword = request.args.get('keyword', '').lower()  # 검색어를 소문자로 변환
    filtered_faqs = [faq for faq in faqs if keyword in faq['question'].lower() or keyword in faq['answer'].lower()]
    return jsonify(filtered_faqs)

if __name__ == '__main__':
    app.run(debug=True)

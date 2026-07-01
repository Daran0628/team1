from dotenv import load_dotenv
load_dotenv()

import os
import random

from app import app, db
from flask_bcrypt import generate_password_hash
from domain.model.Member import Member
from domain.model.Department import Department
from domain.enum.AccountType import AccountType
from domain.enum.EnrollmentStatus import EnrollmentStatus
from domain.enum.WorkType import WorkType

## python seed.py로 적용

MAIL_DOMAIN = os.getenv("MAIL_DOMAIN", "1mail.local")

DEV_DEPT_ID       = "00000000-0000-0000-0000-000000000001"
ADMIN_DEPT_ID     = "00000000-0000-0000-0000-000000000002"
HR_DEPT_ID        = "00000000-0000-0000-0000-000000000003"
PLAN_DEPT_ID      = "00000000-0000-0000-0000-000000000004"
SALES_DEPT_ID     = "00000000-0000-0000-0000-000000000005"
MARKETING_DEPT_ID = "00000000-0000-0000-0000-000000000006"
FINANCE_DEPT_ID   = "00000000-0000-0000-0000-000000000007"
OPS_DEPT_ID       = "00000000-0000-0000-0000-000000000008"

DEPARTMENTS = [
    {"id": DEV_DEPT_ID,       "department_name": "개발팀"},
    {"id": ADMIN_DEPT_ID,     "department_name": "관리팀"},
    {"id": HR_DEPT_ID,        "department_name": "인사팀"},
    {"id": PLAN_DEPT_ID,      "department_name": "기획팀"},
    {"id": SALES_DEPT_ID,     "department_name": "영업팀"},
    {"id": MARKETING_DEPT_ID, "department_name": "마케팅팀"},
    {"id": FINANCE_DEPT_ID,   "department_name": "재무팀"},
    {"id": OPS_DEPT_ID,       "department_name": "IT운영팀"},
]

TEST_USERS = [
    {
        "name_ko":        "홍길동",
        "account_id":     "hong1",
        "employee_no":    "EMP001",
        "department_id":  DEV_DEPT_ID,
        "email":          f"hong1@{MAIL_DOMAIN}",
        "password":       "hong1pass1",
        "enrollment_status": EnrollmentStatus.ACTIVE,
        "account_type":   AccountType.User,
        "work_type":      WorkType.FULL_TIME,
        "address":        "서울시 강남구",
    },
    {
        "name_ko":        "관리자",
        "account_id":     "admin1",
        "employee_no":    "EMP000",
        "department_id":  ADMIN_DEPT_ID,
        "email":          f"admin1@{MAIL_DOMAIN}",
        "password":       "admin1pass1",
        "enrollment_status": EnrollmentStatus.ACTIVE,
        "account_type":   AccountType.Admin,
        "work_type":      WorkType.FULL_TIME,
        "address":        "서울시 서초구",
    },
]

_names = [
    "김민준","이서준","박도윤","최예준","정지훈","강민재","조현우","윤지호","장우진","임시우",
    "한도현","오준혁","서유진","신하린","권민서","황지민","송다은","안서윤","백예린","유채원",
    "문지호","남현우","노승현","고태윤","배지훈","양도윤","손현수","전민규","류지훈","하승민",
    "곽예린","진수빈","심유진","채서연","허가은","표은지","나지원","주민지","탁예은","염소희",
    "변재현","여준호","추현민","공지후","도민성","천유나","마은호","설지훈"
]

_depts = [d["id"] for d in DEPARTMENTS]
_addrs = ["서울 강남구","서울 송파구","서울 마포구","경기 성남시","경기 수원시","부산 해운대구","대전 서구","광주 북구"]

for idx, name in enumerate(_names, start=2):
    TEST_USERS.append({
        "name_ko":           name,
        "account_id":        f"user{idx:02d}",
        "employee_no":       f"EMP{idx:03d}",
        "department_id":     random.choice(_depts),
        "email":             f"user{idx:02d}@{MAIL_DOMAIN}",
        "password":          "testpass1a",
        "enrollment_status": random.choice([EnrollmentStatus.ACTIVE, EnrollmentStatus.ACTIVE, EnrollmentStatus.ON_LEAVE]),
        "account_type":      AccountType.User,
        "work_type":         random.choice([WorkType.FULL_TIME, WorkType.CONTRACT, WorkType.PART_TIME, WorkType.INTERN]),
        "address":           random.choice(_addrs),
    })

with app.app_context():

    # ── 부서 시드 ────────────────────────────────────────────
    for dept in DEPARTMENTS:
        exists = Department.query.filter_by(id=dept["id"]).first()
        if exists:
            continue
        db.session.add(Department(id=dept["id"], department_name=dept["department_name"]))
    db.session.commit()

    # ── 회원 시드 ────────────────────────────────────────────
    for data in TEST_USERS:
        exists = Member.query.filter_by(account_id=data["account_id"]).first()
        if exists:
            exists.password = generate_password_hash(data["password"]).decode("utf-8")
            exists.email    = data["email"]
            print(f"[UPDATE] {data['account_id']} 비밀번호·이메일 갱신")
            continue
        member = Member(
            name_ko=           data["name_ko"],
            account_id=        data["account_id"],
            employee_no=       data["employee_no"],
            department_id=     data["department_id"],
            email=             data["email"],
            password=          generate_password_hash(data["password"]).decode("utf-8"),
            enrollment_status= data["enrollment_status"],
            account_type=      data["account_type"],
            work_type=         data["work_type"],
            address=           data["address"],
        )
        db.session.add(member)
        print(f"[OK]   {data['account_id']} / {data['password']}")
    db.session.commit()

    print("회원/부서 시드 완료")

    # ── 메일박스 생성 (전체 사용자) ───────────────────────────
    # 주의: Mailcow 서버(같은 LAN)에 연결 가능할 때만 성공합니다.
    #       연결 안 되면 이 아래에서 에러가 날 수 있어요 — 그래도
    #       위쪽 회원/부서 데이터는 이미 커밋됐으니 걱정 없어요.
    import time
    from service.MailService.MailService import MailService
    mail_service = MailService()
    members = Member.query.all()
    failed = []
    for m in members:
        try:
            ok = mail_service.create_mailbox(m.account_id, m.name_ko)
        except Exception as e:
            print(f"[FAIL MAIL] {m.account_id} 연결 오류: {e}")
            failed.append(m)
            continue
        if ok:
            print(f"[OK MAIL]   {m.account_id}@{MAIL_DOMAIN} 메일박스 생성")
        else:
            print(f"[SKIP MAIL] {m.account_id} 이미 존재하거나 생성 실패")
            failed.append(m)
        time.sleep(0.3)

    if failed:
        print(f"\n재시도 중... ({len(failed)}개)")
        for m in failed:
            time.sleep(0.5)
            try:
                ok = mail_service.create_mailbox(m.account_id, m.name_ko)
            except Exception as e:
                print(f"[FAIL MAIL] {m.account_id} 재시도 오류: {e}")
                continue
            print(f"{'[OK MAIL]  ' if ok else '[FAIL MAIL]'} {m.account_id} 재시도 {'성공' if ok else '실패'}")

    print("완료")
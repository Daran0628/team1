from dotenv import load_dotenv
load_dotenv()

from app import app, db
from flask_bcrypt import generate_password_hash
from domain.model.member import Member
from domain.enum.AccountType import AccountType
from domain.enum.EnrollmentStatus import EnrollmentStatus
from domain.enum.WorkType import WorkType

## python seed.py로 적용

TEST_USERS = [
    {
        "name_ko":        "홍길동",
        "account_id":     "hong1",
        "employee_no":    "EMP001",
        "dept_path_name": "개발팀",
        "email":          "hong1@test.com",
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
        "dept_path_name": "관리팀",
        "email":          "admin1@test.com",
        "password":       "admin1pass1",
        "enrollment_status": EnrollmentStatus.ACTIVE,
        "account_type":   AccountType.Admin,
        "work_type":      WorkType.FULL_TIME,
        "address":        "서울시 서초구",
    },
]

with app.app_context():
    for data in TEST_USERS:
        exists = Member.query.filter_by(account_id=data["account_id"]).first()
        if exists:
            print(f"[SKIP] {data['account_id']} 이미 존재")
            continue

        member = Member(
            name_ko=           data["name_ko"],
            account_id=        data["account_id"],
            employee_no=       data["employee_no"],
            dept_path_name=    data["dept_path_name"],
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
    print("완료")

from dotenv import load_dotenv
load_dotenv()

from app import app, db
from flask_bcrypt import generate_password_hash
from domain.model.Member import Member
from domain.model.Department import Department
from domain.enum.AccountType import AccountType
from domain.enum.EnrollmentStatus import EnrollmentStatus
from domain.enum.WorkType import WorkType

## python seed.py로 적용

DEV_DEPT_ID   = "00000000-0000-0000-0000-000000000001"
ADMIN_DEPT_ID = "00000000-0000-0000-0000-000000000002"

TEST_USERS = [
    {
        "name_ko":        "홍길동",
        "account_id":     "hong1",
        "employee_no":    "EMP001",
        "department_id":  DEV_DEPT_ID,
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
        "department_id":  ADMIN_DEPT_ID,
        "email":          "admin1@test.com",
        "password":       "admin1pass1",
        "enrollment_status": EnrollmentStatus.ACTIVE,
        "account_type":   AccountType.Admin,
        "work_type":      WorkType.FULL_TIME,
        "address":        "서울시 서초구",
    },
]

DEPARTMENTS = [
    {
        "id": DEV_DEPT_ID,
        "department_name": "개발팀"
    },
    {
        "id": ADMIN_DEPT_ID,
        "department_name": "관리팀"
    }
]

with app.app_context():

    for dept in DEPARTMENTS:
        exists = Department.query.filter_by(id=dept["id"]).first()

        if exists:
            continue

        db.session.add(
            Department(
                id=dept["id"],
                department_name=dept["department_name"]
            )
        )

    db.session.commit()

    for data in TEST_USERS:
        exists = Member.query.filter_by(account_id=data["account_id"]).first()
        if exists:
            print(f"[SKIP] {data['account_id']} 이미 존재")
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

    
    print("완료")

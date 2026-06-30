from dotenv import load_dotenv
load_dotenv()

from app import app, db
from flask_bcrypt import generate_password_hash
from domain.model.Member import Member
from domain.model.StorageBucket import StorageBucket
from domain.model.StorageResource import StorageResource
from domain.model.Vdi import Vdi, VdiSnapshot
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

    # # ── Object Storage 더미 데이터 ─────────────────────────────
    # hong1  = Member.query.filter_by(account_id="hong1").first()
    # admin1 = Member.query.filter_by(account_id="admin1").first()

    # SEED_BUCKET_NAME = "dev-uploads"
    # seed_bucket = StorageBucket.query.filter_by(bucket_name=SEED_BUCKET_NAME).first()
    # if not seed_bucket:
    #     seed_bucket = StorageBucket(
    #         bucket_name=SEED_BUCKET_NAME,
    #         created_by=admin1.id if admin1 else "00000000-0000-0000-0000-000000000000",
    #     )
    #     db.session.add(seed_bucket)
    #     db.session.flush()   # bucket_name FK 확보
    #     print(f"[OK BUCKET]    {SEED_BUCKET_NAME}")
    # else:
    #     print(f"[SKIP BUCKET]  {SEED_BUCKET_NAME} 이미 존재")

    # STORAGE_DATA = [
    #     {
    #         "resource_name": "홍길동_보고서.pdf",
    #         "bucket_name":   SEED_BUCKET_NAME,
    #         "s3_key":        "uploads/hong1/reports/report-2026.pdf",
    #         "owner_id":      hong1.id  if hong1  else None,
    #     },
    #     {
    #         "resource_name": "관리자_공지문.docx",
    #         "bucket_name":   SEED_BUCKET_NAME,
    #         "s3_key":        "uploads/admin1/notices/notice-2026.docx",
    #         "owner_id":      admin1.id if admin1 else None,
    #     },
    # ]

    # for data in STORAGE_DATA:
    #     if not data["owner_id"]:
    #         print(f"[SKIP STORAGE] {data['resource_name']} — 멤버 없음")
    #         continue
    #     exists = StorageResource.query.filter_by(s3_key=data["s3_key"]).first()
    #     if exists:
    #         print(f"[SKIP STORAGE] {data['resource_name']} 이미 존재")
    #         continue
    #     resource = StorageResource(
    #         resource_name=data["resource_name"],
    #         bucket_name=  data["bucket_name"],
    #         s3_key=       data["s3_key"],
    #         owner_id=     data["owner_id"],
    #     )
    #     db.session.add(resource)
    #     print(f"[OK STORAGE]   {data['resource_name']}")

    # db.session.commit()

    # ── VDI 더미 데이터 ─────────────────────────────────────────
    hong1  = Member.query.filter_by(account_id="hong1").first()
    admin1 = Member.query.filter_by(account_id="admin1").first()

    VDI_DATA = [
        {
            "container_name": "hong1-desktop",
            "image":          "ubuntu-desktop:22.04",
            "status":         "STOPPED",
            "assigned_to":    hong1.id  if hong1  else None,
        },
        {
            "container_name": "admin1-desktop",
            "image":          "ubuntu-desktop:22.04",
            "status":         "RUNNING",
            "assigned_to":    admin1.id if admin1 else None,
        },
    ]

    created_vdis = []
    for data in VDI_DATA:
        if not data["assigned_to"]:
            print(f"[SKIP VDI] {data['container_name']} — 멤버 없음")
            continue
        exists = Vdi.query.filter_by(container_name=data["container_name"]).first()
        if exists:
            print(f"[SKIP VDI] {data['container_name']} 이미 존재")
            created_vdis.append(exists)
            continue
        vdi = Vdi(
            container_name=data["container_name"],
            image=         data["image"],
            status=        data["status"],
            assigned_to=   data["assigned_to"],
        )
        db.session.add(vdi)
        db.session.flush()   # snapshot FK를 위해 vdi_id 확보
        created_vdis.append(vdi)
        print(f"[OK VDI]   {data['container_name']}")

    db.session.commit()

    # ── VDI Snapshot 더미 데이터 ────────────────────────────────
    SNAPSHOT_DATA = [
        {
            "vdi":           created_vdis[0] if len(created_vdis) > 0 else None,
            "snapshot_name": "초기 스냅샷",
            "image_tag":     "hong1-desktop:snap-001",
            "created_by":    hong1.id  if hong1  else None,
        },
        {
            "vdi":           created_vdis[1] if len(created_vdis) > 1 else None,
            "snapshot_name": "관리자 기본 스냅샷",
            "image_tag":     "admin1-desktop:snap-001",
            "created_by":    admin1.id if admin1 else None,
        },
    ]

    for data in SNAPSHOT_DATA:
        if not data["vdi"] or not data["created_by"]:
            print(f"[SKIP SNAP] {data['snapshot_name']} — VDI 또는 멤버 없음")
            continue
        exists = VdiSnapshot.query.filter_by(
            vdi_id=data["vdi"].vdi_id,
            snapshot_name=data["snapshot_name"],
        ).first()
        if exists:
            print(f"[SKIP SNAP] {data['snapshot_name']} 이미 존재")
            continue
        snap = VdiSnapshot(
            vdi_id=       data["vdi"].vdi_id,
            snapshot_name=data["snapshot_name"],
            image_tag=    data["image_tag"],
            created_by=   data["created_by"],
        )
        db.session.add(snap)
        print(f"[OK SNAP]  {data['snapshot_name']} → {data['image_tag']}")

    db.session.commit()
    print("VDI 시드 완료")

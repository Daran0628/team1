from dotenv import load_dotenv
load_dotenv()

from app import app, db
from domain.model.Member import Member
from flask_bcrypt import generate_password_hash

with app.app_context():
    members = Member.query.filter(Member.account_id.like('user%')).all()
    for m in members:
        m.password = generate_password_hash('testpass1a').decode('utf-8')
        print(f'[OK] {m.account_id} 비밀번호 변경 완료')
    db.session.commit()
    print(f'총 {len(members)}명 업데이트 완료')

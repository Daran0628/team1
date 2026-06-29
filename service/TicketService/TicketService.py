from domain.model.Ticket import Ticket
from extensions import db, redis_client


class TicketService:

    ADMIN_NOTIFY_KEY = "admin:new_ticket_count"

    def get_all(self):
        """티켓 전체 목록 (최신순)"""
        return Ticket.query.order_by(Ticket.created_at.desc()).all()

    def get_my_tickets(self, member_id: str):
        """내 티켓 목록"""
        return Ticket.query.filter_by(member_id=member_id)\
                           .order_by(Ticket.created_at.desc()).all()

    def get_one(self, ticket_id: str):
        """티켓 단건 조회"""
        ticket = Ticket.query.get(ticket_id)
        if ticket is None:
            raise ValueError("존재하지 않는 티켓입니다.")
        return ticket

    def create(self, member_id: str, title: str, content: str, priority: str = "MEDIUM"):
        """티켓 생성 + 관리자 알림 카운트 증가"""
        ticket = Ticket(
            member_id=member_id,
            title=title,
            content=content,
            priority=priority,
            status="OPEN",
        )
        db.session.add(ticket)
        db.session.commit()

        # Redis 알림 카운트 증가
        try:
            redis_client.incr(self.ADMIN_NOTIFY_KEY)
        except Exception:
            pass

        return ticket

    def get_notify_count(self):
        """관리자 알림 카운트 조회"""
        try:
            count = redis_client.get(self.ADMIN_NOTIFY_KEY)
            return int(count) if count else 0
        except Exception:
            return 0

    def clear_notify_count(self):
        """관리자 알림 카운트 초기화"""
        try:
            redis_client.delete(self.ADMIN_NOTIFY_KEY)
        except Exception:
            pass

    def update_status(self, ticket_id: str, status: str):
        """티켓 상태 변경 (관리자)"""
        ticket = Ticket.query.get(ticket_id)
        if ticket is None:
            raise ValueError("존재하지 않는 티켓입니다.")
        ticket.status = status
        db.session.commit()
        return ticket

    def delete(self, ticket_id: str):
        """티켓 삭제"""
        ticket = Ticket.query.get(ticket_id)
        if ticket is None:
            raise ValueError("존재하지 않는 티켓입니다.")
        db.session.delete(ticket)
        db.session.commit()
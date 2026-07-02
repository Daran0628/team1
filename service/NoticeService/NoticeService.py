from domain.model.Notice import Notice
from extensions import db


class NoticeService:

    def get_all(self):
        """공지사항 전체 목록 (고정글 먼저, 최신순)"""
        return Notice.query.order_by(
            Notice.is_pinned.desc(),
            Notice.created_at.desc()
        ).all()

    def _get_or_raise(self, notice_id: str) -> Notice:
        notice = Notice.query.get(notice_id)
        if notice is None:
            raise ValueError("존재하지 않는 공지사항입니다.")
        return notice    

    def get_one(self, notice_id: str):
        """공지사항 단건 조회 (조회수 증가 없음 - 수정용)"""
        notice = self._get_or_raise(notice_id)
        return notice

    def get_one_for_view(self, notice_id: str):
        """공지사항 단건 조회 + 조회수 증가 (상세보기용)"""
        notice = self._get_or_raise(notice_id)
        notice.view_count += 1
        db.session.commit()
        return notice

    def create(self, member_id: str, title: str, content: str, is_pinned: bool = False):
        """공지사항 등록"""
        notice = Notice(
            member_id=member_id,
            title=title,
            content=content,
            is_pinned=is_pinned,
        )
        db.session.add(notice)
        db.session.commit()
        return notice

    def update(self, notice_id: str, title: str, content: str, is_pinned: bool):
        """공지사항 수정"""
        notice = self._get_or_raise(notice_id)
        notice.title     = title
        notice.content   = content
        notice.is_pinned = is_pinned
        db.session.commit()
        return notice

    def delete(self, notice_id: str):
        """공지사항 삭제"""
        notice = self._get_or_raise(notice_id)
        db.session.delete(notice)
        db.session.commit()
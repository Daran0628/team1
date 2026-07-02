from domain.model.Faq import Faq
from extensions import db


class FaqService:

    def get_all(self, category: str = None):
        """FAQ 전체 목록 (카테고리 필터 가능)"""
        query = Faq.query.order_by(Faq.created_at.desc())
        if category:
            query = query.filter_by(category=category)
        return query.all()

    def get_one(self, faq_id: str):
        """FAQ 단건 조회"""
        faq = Faq.query.get(faq_id)
        if faq is None:
            raise ValueError("존재하지 않는 FAQ입니다.")
        return faq

    def create(self, member_id: str, question: str, answer: str, category: str = None):
        """FAQ 등록"""
        faq = Faq(
            member_id=member_id,
            question=question,
            answer=answer,
            category=category,
        )
        db.session.add(faq)
        db.session.commit()
        return faq

    def update(self, faq_id: str, question: str, answer: str, category: str = None):
        """FAQ 수정"""
        faq = Faq.query.get(faq_id)
        if faq is None:
            raise ValueError("존재하지 않는 FAQ입니다.")
        faq.question = question
        faq.answer   = answer
        faq.category = category
        db.session.commit()
        return faq

    def delete(self, faq_id: str):
        """FAQ 삭제"""
        faq = Faq.query.get(faq_id)
        if faq is None:
            raise ValueError("존재하지 않는 FAQ입니다.")
        db.session.delete(faq)
        db.session.commit()
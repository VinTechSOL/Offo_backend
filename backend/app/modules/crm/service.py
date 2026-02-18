from sqlalchemy.orm import Session
from app.modules.crm.repository import CrmRepository


class CrmService:

    @staticmethod
    def get_customers(db: Session, branch_id: int):
        return CrmRepository.get_customers_with_order_stats(db, branch_id)

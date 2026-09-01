from sqlalchemy.orm import Session
from app.modules.crm.repository import CrmRepository


class CrmService:

    @staticmethod
    def get_customers(db: Session, branch_id: int):
        return CrmRepository.get_customers_with_order_stats(db, branch_id)

    @staticmethod
    def get_customer_orders(db: Session, branch_id: int, customer_id: int):
        return CrmRepository.get_customer_order_history(db, branch_id, customer_id)
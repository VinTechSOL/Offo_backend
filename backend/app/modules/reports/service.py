from sqlalchemy.orm import Session
from app.modules.reports.repository import ReportsRepository


class ReportsService:

    @staticmethod
    def get_overview(db: Session, branch_id: int):
        return ReportsRepository.get_overview(db, branch_id)

    @staticmethod
    def get_menu_performance(db: Session, branch_id: int):
        return ReportsRepository.get_menu_performance(db, branch_id)

    @staticmethod
    def get_customer_insights(db: Session, branch_id: int):
        return ReportsRepository.get_customer_insights(db, branch_id)

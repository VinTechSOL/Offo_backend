from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.modules.reports.repository import ReportsRepository


class ReportsService:

    @staticmethod
    def resolve_dates(
        filter_by=None,
        start_date=None,
        end_date=None,
    ):

        now = datetime.now(timezone.utc)

        if filter_by == "1d":
            return now - timedelta(days=1), now

        if filter_by == "1w":
            return now - timedelta(weeks=1), now

        if filter_by == "1m":
            return now - timedelta(days=30), now

        if filter_by == "1y":
            return now - timedelta(days=365), now

        return start_date, end_date

    @staticmethod
    def get_overview(
        db: Session,
        branch_id: int,
        filter_by=None,
        start_date=None,
        end_date=None,
    ):

        start_date, end_date = ReportsService.resolve_dates(
            filter_by,
            start_date,
            end_date
        )

        return ReportsRepository.get_overview(
            db,
            branch_id,
            start_date,
            end_date
        )

    @staticmethod
    def get_menu_performance(
        db: Session,
        branch_id: int,
        filter_by=None,
        start_date=None,
        end_date=None,
    ):

        start_date, end_date = ReportsService.resolve_dates(
            filter_by,
            start_date,
            end_date
        )

        return ReportsRepository.get_menu_performance(
            db,
            branch_id,
            start_date,
            end_date
        )

    @staticmethod
    def get_customer_insights(
        db: Session,
        branch_id: int,
        filter_by=None,
        start_date=None,
        end_date=None,
    ):

        start_date, end_date = ReportsService.resolve_dates(
            filter_by,
            start_date,
            end_date
        )

        return ReportsRepository.get_customer_insights(
            db,
            branch_id,
            start_date,
            end_date
        )
from enum import Enum


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in-progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketIssueType(str, Enum):
    MISSING_ITEM = "missing_item"
    FOOD_QUALITY = "food_quality"
    PICKUP_ISSUE = "pickup_issue"
    PAYMENT_BILLING = "payment_billing"
    OTHER = "other"
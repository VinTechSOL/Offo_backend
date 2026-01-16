from enum import Enum


class NotificationRecipient(str, Enum):
    USER = "USER"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class NotificationChannel(str, Enum):
    IN_APP = "IN_APP"
    SMS = "SMS"


class NotificationPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NotificationEvent(str, Enum):
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_REMINDER = "ORDER_REMINDER"
    ORDER_PREPARING ="ORDER_PREPARING"
    ORDER_READY = "ORDER_READY"
    ORDER_COMPLETED = "ORDER_COMPLETED"
    ORDER_EXPIRED = "ORDER_EXPIRED"
    SCHEDULED_REMINDER = "SCHEDULED_REMINDER"

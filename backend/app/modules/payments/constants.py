from enum import Enum


class PaymentGateway(str, Enum):
    PHONEPE = "PHONEPE"


class PaymentIntentStatus(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"

    REFUND_INITIATED = "REFUND_INITIATED"
    REFUNDED="REFUNDED"
    REFUND_FAILED = "REFUND_FAILED"
    
    FAILED = "FAILED"


class PaymentAttemptStatus(str, Enum):
    INITIATED = "INITIATED"
    REDIRECTED = "REDIRECTED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PaymentType(str, Enum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"

import uuid


def generate_merchant_order_id() -> str:
    """
    Generates a unique merchant order ID for PhonePe.

    Example:
    OFFO_9b6b5d7b1d8e4c57b8c1e0a4b2c9f1d3
    """
    return f"OFFO_{uuid.uuid4().hex}"


def generate_merchant_refund_id() -> str:
    """
    Generates a unique merchant refund ID for PhonePe.

    Example:
    OFFO_REF_9b6b5d7b1d8e4c57b8c1e0a4b2c9f1d3
    """
    return f"OFFO_REF_{uuid.uuid4().hex}"
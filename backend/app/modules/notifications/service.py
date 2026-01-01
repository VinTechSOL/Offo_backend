class NotificationService:

    @staticmethod
    def notify_vendor_incoming(db, order_id: int, branch_id: int):
        # TEMP: replace with real notification later
        print(f"🔔 Vendor notified: Incoming order {order_id} for branch {branch_id}")

    @staticmethod
    def notify_order_expired(db, order_id: int, user_id: int):
        # TEMP
        print(f"⏰ Order expired: {order_id} for user {user_id}")

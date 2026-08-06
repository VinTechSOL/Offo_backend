from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from phonepe.sdk.pg.env import Env

from app.core.config import settings


class PhonePeSDK:

    _client = None

    @classmethod
    def get_client(cls):
        """
        Returns singleton PhonePe SDK client.

        PhonePe recommends creating only one client
        instance during application lifetime.
        """

        if cls._client is None:

            env = (
                Env.PRODUCTION
                if settings.PHONEPE_ENV.upper() == "PRODUCTION"
                else Env.SANDBOX
            )

            cls._client = StandardCheckoutClient.get_instance(
                client_id=settings.PHONEPE_CLIENT_ID,
                client_secret=settings.PHONEPE_CLIENT_SECRET,
                client_version=settings.PHONEPE_CLIENT_VERSION,
                env=env,
                should_publish_events=False,
                should_retry=False,
            )

        return cls._client
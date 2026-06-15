import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SubsidyClient:
    def __init__(self):
        self.url = settings.SUBSIDY_API_URL

    def get_subsidy_by_hoa_name(self, hoa_name: str) -> list | None:
        """
        Returns a list of subsidy objects for the given HOA name,
        an empty list if no application is found, or None if the external API is unavailable.
        """
        try:
            response = requests.get(
                self.url,
                params={"aanvrager": hoa_name},
                timeout=5,
            )
            response.raise_for_status()

            try:
                data = response.json()
            except ValueError:
                logger.error("Subsidy API returned invalid JSON for HOA: %s", hoa_name)
                return None

            return data.get("_embedded", {}).get("openbaar_subsidieregister", [])

        except requests.RequestException as e:
            logger.error("Subsidy API request failed for HOA '%s': %s", hoa_name, e)
            return None

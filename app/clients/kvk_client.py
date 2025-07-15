import requests
from django.conf import settings
from urllib.parse import urlencode


class KvkClient:
    def __init__(self):
        self.url = settings.KVK_API_URL

    def search_kvk_by_hoa_name(self, hoa_name):
        query_params = urlencode({"q": hoa_name})
        url = f"{self.url}?{query_params}"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            try:
                response_data = response.json()
            except ValueError:
                return None

            results = response_data.get("resultatenHR", [])
            if results:
                return results[0].get("dossiernummer")
            return None
        except requests.RequestException as e:
            print(f"KVK-API request failed: {e}")
            return None

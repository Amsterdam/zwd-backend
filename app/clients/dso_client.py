import requests
from django.conf import settings

from utils.exceptions import NotFoundException


class DsoClient:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {self._get_access_token()}"}

    def get_hoa_name_by_bag_id(self, bag_id):
        url = f"{settings.DSO_API_URL}?brkVveIsEigendomVve=ja&votIdentificatie={bag_id}"
        response = requests.get(url, headers=self.headers)
        response_data = response.json()
        wonen_verblijfsobject_list = response_data.get("_embedded", {}).get(
            "wonen_verblijfsobject", []
        )
        if wonen_verblijfsobject_list:
            hoa = wonen_verblijfsobject_list[0]
            return hoa["brkVveStatutaireNaam"]
        raise NotFoundException(f"HomeownerAssociation with bag ID {bag_id} not found.")

    def get_hoa_by_name(self, hoa_name):
        url = f"{settings.DSO_API_URL}?brkVveStatutaireNaam={hoa_name}&_pageSize=300"
        hoa_json = self._get_paginated_response(url)
        verblijfsobjecten = hoa_json.get("_embedded", {}).get(
            "wonen_verblijfsobject", []
        )

        # Filter for residential use only
        woon_objecten = [
            obj for obj in verblijfsobjecten if obj.get("eigWoningvoorraad") == "true"
        ]

        # Use dict to deduplicate by 'votIdentificatie'
        return list({obj["votIdentificatie"]: obj for obj in woon_objecten}.values())

    def search_hoa_by_name(self, hoa_name):
        url = f"{settings.DSO_API_URL}?brkVveIsEigendomVve=ja&brkVveStatutaireNaam[like]=*{hoa_name}*&_pageSize=300"
        hoa_json = self._get_paginated_response(url)
        hoa_verblijfsobject = hoa_json["_embedded"]["wonen_verblijfsobject"]
        return list(
            {hoa["brkVveStatutaireNaam"]: hoa for hoa in hoa_verblijfsobject}.values()
        )

    def _get_paginated_response(self, url):
        response = requests.get(url, headers=self.headers)
        response_json = response.json()
        while "_links" in response_json and "next" in response_json["_links"]:
            next_page = response_json["_links"]["next"]["href"]
            paged_response = requests.get(next_page, headers=self.headers)
            paged_json = paged_response.json()
            response_json["_embedded"]["wonen_verblijfsobject"].extend(
                paged_json["_embedded"]["wonen_verblijfsobject"]
            )
            response_json["_links"] = paged_json["_links"]
        return response_json

    def _get_access_token(self):
        url = settings.DSO_AUTH_URL
        payload = {
            "client_id": settings.DSO_CLIENT_ID,
            "grant_type": "client_credentials",
            "client_secret": settings.DSO_CLIENT_SECRET,
            "scope": "openid email",
        }
        response = requests.post(url, data=payload).json()
        return response["access_token"]

from django.test import TestCase
from unittest.mock import patch


from apps.homeownerassociation.models import (
    HomeownerAssociation,
    Owner,
    PriorityZipCode,
)
from model_bakery import baker


class HomeownerAssociationModelTest(TestCase):
    @patch("apps.homeownerassociation.models.DsoClient")
    def test_get_or_create_hoa_by_bag_id_new_hoa(self, MockDsoClient):
        # Mock the DsoClient and its methods
        mock_client = MockDsoClient.return_value
        mock_client.get_hoa_name_by_bag_id.return_value = "New HOA"
        mock_client.get_hoa_by_name.return_value = [
            {"pndOorspronkelijkBouwjaar": 2010, "votIdentificatie": "123"},
        ]

        # Call the method
        result = HomeownerAssociation().get_or_create_hoa_by_bag_id("some_bag_id")
        # Assert a new HOA is created
        self.assertIsInstance(result, HomeownerAssociation)
        self.assertEqual(result.name, "New HOA")
        self.assertEqual(result.build_year, 2010)
        self.assertEqual(result.number_of_appartments, 1)
        mock_client.get_hoa_name_by_bag_id.assert_called_once_with("some_bag_id")
        mock_client.get_hoa_by_name.assert_called_once_with("New HOA")

    @patch("apps.homeownerassociation.models.DsoClient")
    def test_get_or_create_hoa_by_bag_id_new_creates_owners(self, MockDsoClient):
        mock_client = MockDsoClient.return_value
        mock_client.get_hoa_name_by_bag_id.return_value = "HOA"
        mock_client.get_hoa_by_name.return_value = [
            {
                "pndOorspronkelijkBouwjaar": 2010,
                "votIdentificatie": "333",
                "eigCategorieEigenaar": "Corporatie",
                "brkStatutaireNaam": "Corpo1",
            },
            {
                "pndOorspronkelijkBouwjaar": 2010,
                "votIdentificatie": "444",
                "eigCategorieEigenaar": "Particulier",
                "brkStatutaireNaam": "John Doe",
            },
            {
                "pndOorspronkelijkBouwjaar": 2010,
                "votIdentificatie": "555",
                "eigCategorieEigenaar": "Corporatie",
                "brkStatutaireNaam": "Corpo1",
            },
            {
                "pndOorspronkelijkBouwjaar": 2010,
                "votIdentificatie": "666",
                "eigCategorieEigenaar": "Particulier",
                "brkStatutaireNaam": "Jane Smith",
            },
            {
                "pndOorspronkelijkBouwjaar": 2010,
                "votIdentificatie": "777",
                "eigCategorieEigenaar": "Corporatie",
                "brkStatutaireNaam": "AnotherCorp",
            },
        ]
        result = HomeownerAssociation().get_or_create_hoa_by_bag_id("unique_id")

        owners = result.owners.all()
        self.assertEqual(owners.count(), 4)

        picobello = owners.filter(name="Corpo1").first()
        self.assertEqual(picobello.type, "Corporatie")
        self.assertEqual(picobello.number_of_appartments, 2)

        john_doe = owners.filter(name="John Doe").first()
        self.assertEqual(john_doe.type, "Particulier")
        self.assertEqual(john_doe.number_of_appartments, 1)

        jane_smith = owners.filter(name="Jane Smith").first()
        self.assertEqual(jane_smith.type, "Particulier")
        self.assertEqual(jane_smith.number_of_appartments, 1)

        another_corp = owners.filter(name="AnotherCorp").first()
        self.assertEqual(another_corp.type, "Corporatie")
        self.assertEqual(another_corp.number_of_appartments, 1)

    @patch("apps.homeownerassociation.models.DsoClient")
    def test_get_or_create_hoa_by_bag_id_creates_district_and_neighbordhood(
        self, MockDsoClient
    ):
        mock_client = MockDsoClient.return_value
        mock_client.get_hoa_name_by_bag_id.return_value = "HOA"
        mock_client.get_hoa_by_name.return_value = [
            {
                "pndOorspronkelijkBouwjaar": 2010,
                "votIdentificatie": "333",
                "gbdSdlNaam": "District1",
                "gbdBrtNaam": "Neighborhood1",
            },
        ]
        result = HomeownerAssociation().get_or_create_hoa_by_bag_id("unique_id")
        self.assertIsInstance(result, HomeownerAssociation)
        self.assertEqual(result.district.name, "District1")
        self.assertEqual(result.neighborhood.name, "Neighborhood1")
        self.assertEqual(result.district.neighborhoods.count(), 1)
        self.assertEqual(result.neighborhood.homeowner_associations.count(), 1)

    def test_is_small(
        self,
    ):
        hoa = baker.make(HomeownerAssociation, number_of_appartments=12)
        self.assertTrue(hoa.is_small)
        hoa = baker.make(HomeownerAssociation, number_of_appartments=13)
        self.assertFalse(hoa.is_small)

    def test_has_major_shareholder(self):
        hoa = baker.make(HomeownerAssociation, number_of_appartments=12)
        baker.make(
            Owner, homeowner_association=hoa, number_of_appartments=3, type="Corporatie"
        )
        self.assertTrue(hoa.has_major_shareholder)

        hoa = baker.make(HomeownerAssociation, number_of_appartments=12)
        baker.make(
            Owner, homeowner_association=hoa, number_of_appartments=2, type="Corporatie"
        )
        self.assertFalse(hoa.has_major_shareholder)

        hoa = baker.make(HomeownerAssociation, number_of_appartments=12)
        baker.make(
            Owner,
            homeowner_association=hoa,
            number_of_appartments=8,
            type="Natuurlijk persoon",
        )
        self.assertFalse(hoa.has_major_shareholder)

    def test_is_priority_neighborhood_true(self):
        zip_code = "1234AB"
        baker.make(PriorityZipCode, zip_code=zip_code)
        hoa = baker.make(HomeownerAssociation, zip_code=zip_code)
        self.assertTrue(hoa.is_priority_neighborhood)

    def test_is_priority_neighborhood_false(self):
        zip_code = "5678CD"
        hoa = baker.make(HomeownerAssociation, zip_code=zip_code)
        self.assertFalse(hoa.is_priority_neighborhood)

    def test_is_priority_neighborhood_no_zip_code(self):
        hoa = baker.make(HomeownerAssociation, zip_code=None)
        self.assertFalse(hoa.is_priority_neighborhood)

    def test_is_priority_neighborhood_empty_zip_code(self):
        hoa = baker.make(HomeownerAssociation, zip_code="")
        self.assertFalse(hoa.is_priority_neighborhood)

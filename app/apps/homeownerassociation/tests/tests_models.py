from django.test import TestCase
from unittest.mock import patch
from apps.homeownerassociation.models import HomeownerAssociation


class HomeownerAssociationModelTest(TestCase):

    @patch("apps.homeownerassociation.models.DsoClient")
    def test_get_or_create_hoa_by_bag_id_existing_hoa(self, MockDsoClient):
        # Mock the DsoClient and its methods
        mock_client = MockDsoClient.return_value
        mock_client.get_hoa_name_by_bag_id.return_value = "Test HOA"

        # Create an existing HOA
        existing_hoa = HomeownerAssociation.objects.create(
            name="Test HOA", build_year=2000, number_of_appartments=10
        )

        # Call the method
        result = HomeownerAssociation.get_or_create_hoa_by_bag_id("some_bag_id")

        # Assert the existing HOA is returned
        self.assertEqual(result, existing_hoa)
        mock_client.get_hoa_name_by_bag_id.assert_called_once_with("some_bag_id")

    @patch("apps.homeownerassociation.models.DsoClient")
    def test_get_or_create_hoa_by_bag_id_existing_hoa_no_new_hoa(self, MockDsoClient):
        # Mock the DsoClient and its methods
        mock_client = MockDsoClient.return_value
        mock_client.get_hoa_name_by_bag_id.return_value = "Test HOA"

        # Create an existing HOA
        existing_hoa = HomeownerAssociation.objects.create(
            name="Test HOA", build_year=2000, number_of_appartments=10
        )

        # Call the method
        result = HomeownerAssociation.get_or_create_hoa_by_bag_id("some_bag_id")

        # Assert the existing HOA is returned
        self.assertEqual(result, existing_hoa)
        mock_client.get_hoa_name_by_bag_id.assert_called_once_with("some_bag_id")
        mock_client.get_hoa_by_name.assert_not_called()

    @patch("apps.homeownerassociation.models.DsoClient")
    def test_get_or_create_hoa_by_bag_id_new_hoa(self, MockDsoClient):
        # Mock the DsoClient and its methods
        mock_client = MockDsoClient.return_value
        mock_client.get_hoa_name_by_bag_id.return_value = "New HOA"
        mock_client.get_hoa_by_name.return_value = [
            {"pndOorspronkelijkBouwjaar": 2010, "votIdentificatie": "123"},
            {"pndOorspronkelijkBouwjaar": 2010, "votIdentificatie": "123"},
        ]

        # Call the method
        result = HomeownerAssociation.get_or_create_hoa_by_bag_id("some_bag_id")
        # Assert a new HOA is created
        self.assertIsInstance(result, HomeownerAssociation)
        self.assertEqual(result.name, "New HOA")
        self.assertEqual(result.build_year, 2010)
        self.assertEqual(result.number_of_appartments, 1)
        mock_client.get_hoa_name_by_bag_id.assert_called_once_with("some_bag_id")
        mock_client.get_hoa_by_name.assert_called_once_with("New HOA")

    # write a test to verify that duplicate appartements are only counted once
    @patch("apps.homeownerassociation.models.DsoClient")
    def test_get_or_create_hoa_by_bag_id_new_hoa_duplicate_appartments(
        self, MockDsoClient
    ):
        mock_client = MockDsoClient.return_value
        mock_client.get_hoa_name_by_bag_id.return_value = "HOA"
        mock_client.get_hoa_by_name.return_value = [
            {"pndOorspronkelijkBouwjaar": 2010, "votIdentificatie": "333"},
            {"pndOorspronkelijkBouwjaar": 2010, "votIdentificatie": "333"},
            {"pndOorspronkelijkBouwjaar": 2010, "votIdentificatie": "444"},
        ]
        result = HomeownerAssociation.get_or_create_hoa_by_bag_id("unique_id")
        self.assertIsInstance(result, HomeownerAssociation)
        self.assertEqual(result.name, "HOA")
        self.assertEqual(result.build_year, 2010)
        self.assertEqual(result.number_of_appartments, 2)

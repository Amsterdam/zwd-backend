from django.core import management
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from utils.test_utils import get_authenticated_client, get_unauthenticated_client


class CaseApiTest(APITestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()
        self.client = get_authenticated_client()
        self.case = self._create_case()

    def test_unauthenticated_get(self):
        url = reverse("cases-list")
        client = get_unauthenticated_client()
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_get(self):
        url = reverse("cases-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_case(self):
        self._create_case()
        case_id = self.case
        url = reverse("cases-detail", args=[case_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_document_success(self):
        url = reverse("cases-create-document")
        document_data = {
            "document": SimpleUploadedFile(
                "test_document.pdf", b"file_content", content_type="application/pdf"
            ),
            "case": self.case,
            "name": "document_name",
        }
        response = self.client.post(url, data=document_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)

    def test_create_document_blocked_file_extension(self):
        url = reverse("cases-create-document")
        document_data = {
            "document": SimpleUploadedFile(
                "test_document.exe", b"file_content", content_type="application/pdf"
            ),
            "case": self.case,
            "name": "document_name",
        }
        response = self.client.post(url, data=document_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_document_invalid_case(self):
        url = reverse("cases-create-document")
        document_data = {
            "document": SimpleUploadedFile(
                "test_document.pdf", b"file_content", content_type="application/pdf"
            ),
            "case": 1231321,
            "name": "document_name",
        }
        response = self.client.post(url, data=document_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_document_invalid_data(self):
        url = reverse("cases-create-document")
        document_data = {}
        response = self.client.post(url, data=document_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_documents_success(self):
        self._create_sample_document()
        url = reverse("cases-get-documents", args=[self.case])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_get_documents_empty(self):
        url = reverse("cases-get-documents", args=[self.case])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_download_document_success(self):
        document = (
            self._create_sample_document()
        )  # Create and retrieve the document instance
        url = reverse("cases-download-document", args=[self.case, document["id"]])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Content-Disposition", response)

    def test_download_document_not_found(self):
        non_existent_doc_id = 999
        url = reverse("cases-download-document", args=[self.case, non_existent_doc_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_document_success(self):
        document = self._create_sample_document()
        url = reverse("cases-delete-document", args=[self.case, document["id"]])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_document_not_found(self):
        non_existent_doc_id = 999
        url = reverse("cases-delete-document", args=[self.case, non_existent_doc_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def _create_sample_document(self):
        url = reverse("cases-create-document")
        document_data = {
            "document": SimpleUploadedFile(
                "test_document.pdf", b"file_content", content_type="application/pdf"
            ),
            "case": self.case,
            "name": "document_name",
        }
        response = self.client.post(url, data=document_data, format="multipart")
        return response.data

    def _create_case(self):
        url = reverse("cases-list")
        data = {"description": "Test case description"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["id"]

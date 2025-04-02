from unittest.mock import patch
from django.core import management
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.workflow.models import WorkflowOption
from apps.advisor.models import Advisor
from apps.cases.models import AdviceType, Case
from apps.homeownerassociation.models import HomeownerAssociation
from utils.test_utils import get_authenticated_client, get_unauthenticated_client
from model_bakery import baker
from django.utils import timezone


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

    def test_update_advisor_success(self):
        url = reverse("cases-update-advisor", args=[self.case])
        advisor = baker.make("Advisor")
        data = {"advisor": advisor.id}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_advisor_not_found(self):
        url = reverse("cases-update-advisor", args=[self.case])
        data = {"advisor": 999}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_advisor_bad_request(self):
        url = reverse("cases-update-advisor", args=[self.case])
        data = {"adv": 999}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_advisors_hbo_success(self):
        advisor_name = "Advisor_hbo"
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_appartments=13
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.HBO.value,
        )
        baker.make(Advisor, advice_type_hbo=True, enabled=True, name=advisor_name)
        url = reverse("cases-advisors", args=[case.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], advisor_name)

    def test_get_advisors_ea_success(self):
        advisor_name = "Advisor_ea"
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_appartments=13
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        baker.make(
            Advisor, advice_type_energieadvies=True, enabled=True, name=advisor_name
        )
        url = reverse("cases-advisors", args=[case.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], advisor_name)

    def test_get_advisors_small_hoa_ea_success(self):
        advisor_name = "Advisor_small"
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_appartments=11
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        baker.make(Advisor, small_hoa=True, enabled=True, name=advisor_name)
        baker.make(Advisor, advice_type_energieadvies=True, enabled=True, name="random")
        url = reverse("cases-advisors", args=[case.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], advisor_name)

    def test_get_advisors_small_hoa_hbo_success(self):
        advisor_name = "Advisor_small"
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_appartments=11
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.HBO.value,
        )
        baker.make(Advisor, small_hoa=True, enabled=True, name=advisor_name)
        baker.make(Advisor, advice_type_hbo=True, enabled=True, name="random")
        url = reverse("cases-advisors", args=[case.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], advisor_name)

    def test_get_advisors_not_found(self):
        url = reverse("cases-advisors", args=[999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_processes_returns_options(self):
        case = self._create_case()
        option_name = "test_workflow_option"
        baker.make(WorkflowOption, name=option_name)
        url = reverse("cases-processes", args=[case])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(option["name"] == option_name for option in response.data))

    def test_processes_closed_cases(self):
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_appartments=13
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
            end_date=timezone.datetime.now(),
        )
        option_name = "test_workflow_option"
        option_name_closed_case = "test_workflow_option_closed"
        baker.make(WorkflowOption, name=option_name)
        baker.make(
            WorkflowOption, name=option_name_closed_case, enabled_on_case_closed=True
        )
        url = reverse("cases-processes", args=[case.id])
        response = self.client.get(url)
        self.assertFalse(any(option["name"] == option_name for option in response.data))
        self.assertTrue(
            any(option["name"] == option_name_closed_case for option in response.data)
        )

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

    # Django test create a test db, celery is unaware of that db so mock celery methods
    @patch("apps.cases.views.CaseViewSet.start_workflow")
    def _create_case(self, mock_start_workflow):
        mock_start_workflow.return_value = "task_start_workflow: completed"
        url = reverse("cases-list")
        data = {"description": "Test case description"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["id"]

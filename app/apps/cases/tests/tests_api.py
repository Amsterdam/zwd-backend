from unittest.mock import patch
from django.core import management
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.workflow.models import WorkflowOption
from apps.advisor.models import Advisor
from apps.cases.models import (
    AdviceType,
    ApplicationType,
    Case,
    CaseDocument,
    CaseStatus,
)
from apps.homeownerassociation.models import HomeownerAssociation, Neighborhood
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

    def test_retrieve_cases_filter_by_district(self):
        district_name = "District A"
        district = baker.make("District", name=district_name)
        homeowner_association = baker.make(
            HomeownerAssociation,
            number_of_apartments=13,
            district=district,
            name="ABC",
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        url = reverse("cases-list")
        response = self.client.get(url, {"district": district_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], case.id)

    def test_retrieve_cases_filter_by_wijk(self):
        wijk_name = "Wijk B"
        wijk = baker.make("Wijk", name=wijk_name)
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=20, wijk=wijk, name="ABC"
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.HBO.value,
        )
        url = reverse("cases-list")
        response = self.client.get(url, {"wijk": wijk_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], case.id)

    def test_retrieve_cases_filter_by_neighborhood(self):
        neighborhood_name = "Buurt A"
        neighborhood = baker.make(Neighborhood, name=neighborhood_name)
        homeowner_association = baker.make(
            HomeownerAssociation,
            number_of_apartments=20,
            neighborhood=neighborhood,
            name="ABC",
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.HBO.value,
        )
        url = reverse("cases-list")
        response = self.client.get(url, {"neighborhood": neighborhood})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], case.id)

    def test_retrieve_cases_filter_by_status(self):
        case_status = baker.make(CaseStatus, name="Closed")
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13, name="ABC"
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.HBO.value,
            status=case_status,
        )
        url = reverse("cases-list")
        response = self.client.get(url, {"status": case_status})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], case.id)

    def test_search_cases_by_homeowner_association(self):
        homeowner_association_name = "Homeowner Association A"
        homeowner_association = baker.make(
            HomeownerAssociation,
            number_of_apartments=13,
            name=homeowner_association_name,
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        url = reverse("cases-list")
        homeowner_association_name_partial = homeowner_association_name[2:8]
        response = self.client.get(url, {"search": homeowner_association_name_partial})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], case.id)

    def test_create_document_success(self):
        url = reverse("cases-create-document")
        fake_pdf = b"%PDF-1.4\n%Fake PDF content"
        document_data = {
            "document": SimpleUploadedFile(
                "test_document.pdf", fake_pdf, content_type="application/pdf"
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

    def test_update_document_name(self):
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        case = baker.make(Case, homeowner_association=homeowner_association)
        case_document = baker.make(CaseDocument, case=case, name="old_name")
        url = reverse("cases-update-document-name", args=[case.id, case_document.id])
        data = {"name": "new_name"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        case_document.refresh_from_db()
        self.assertEqual(case_document.name, "new_name")
        self.assertEqual(response.data["name"], "new_name")

    def test_update_document_name_not_found(self):
        url = reverse("cases-update-document-name", args=[self.case, 999])
        data = {"name": "new_name"}
        response = self.client.patch(url, data, format="json")
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
            HomeownerAssociation, number_of_apartments=13
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
            HomeownerAssociation, number_of_apartments=13
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
            HomeownerAssociation, number_of_apartments=11
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
            HomeownerAssociation, number_of_apartments=11
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
            HomeownerAssociation, number_of_apartments=13
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

    def test_retrieve_case_status(self):
        url = reverse("case-status-list")
        case_status = baker.make(CaseStatus, name="Test Status")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(response.data[0], case_status.name)

    @patch("apps.cases.views.CaseViewSet.start_workflow")
    def test_create_course_case_success(self, mock_start_workflow):
        """Test creating a Course case without advice_type"""
        mock_start_workflow.return_value = "task_start_workflow: completed"
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        url = reverse("cases-list")
        data = {
            "application_type": ApplicationType.COURSE.value,
            "description": "Course test case",
            "homeowner_association": homeowner_association.id,
            "request_date": timezone.now().date().isoformat(),
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["application_type"], ApplicationType.COURSE.value
        )
        self.assertIsNone(response.data.get("advice_type"))

        # Verify prefixed_dossier_id has CUR suffix
        case = Case.objects.get(id=response.data["id"])
        self.assertTrue(case.prefixed_dossier_id.endswith("CUR"))

    @patch("apps.cases.views.CaseViewSet.start_workflow")
    def test_create_advice_case_requires_advice_type(self, mock_start_workflow):
        """Test that advice_type is required when application_type is ADVICE"""
        mock_start_workflow.return_value = "task_start_workflow: completed"
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        url = reverse("cases-list")
        data = {
            "application_type": ApplicationType.ADVICE.value,
            # Missing advice_type - should fail
            "description": "Advice test case",
            "homeowner_association": homeowner_association.id,
            "request_date": timezone.now().date().isoformat(),
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("advice_type", response.data)

    @patch("apps.cases.views.CaseViewSet.start_workflow")
    def test_create_advice_case_with_advice_type_success(self, mock_start_workflow):
        """Test creating an Advice case with advice_type"""
        mock_start_workflow.return_value = "task_start_workflow: completed"
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        url = reverse("cases-list")
        data = {
            "application_type": ApplicationType.ADVICE.value,
            "advice_type": AdviceType.ENERGY_ADVICE.value,
            "description": "Energy advice test case",
            "homeowner_association": homeowner_association.id,
            "request_date": timezone.now().date().isoformat(),
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["application_type"], ApplicationType.ADVICE.value
        )
        self.assertEqual(response.data["advice_type"], AdviceType.ENERGY_ADVICE.value)

    def test_filter_cases_by_course_application_type(self):
        """Test filtering cases by Course application type"""
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        course_case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            application_type=ApplicationType.COURSE.value,
            advice_type=None,
        )
        # Create another case with different application type
        baker.make(
            Case,
            homeowner_association=homeowner_association,
            application_type=ApplicationType.ADVICE.value,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )

        url = reverse("cases-list")
        response = self.client.get(
            url, {"application_type": ApplicationType.COURSE.value}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], course_case.id)

    def _create_sample_document(self):
        url = reverse("cases-create-document")
        fake_pdf = b"%PDF-1.4\n%Fake PDF content"
        document_data = {
            "document": SimpleUploadedFile(
                "test_document.pdf", fake_pdf, content_type="application/pdf"
            ),
            "case": self.case,
            "name": "document_name",
        }
        response = self.client.post(url, data=document_data, format="multipart")
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        return response.data

    # Django test create a test db, celery is unaware of that db so mock celery methods
    @patch("apps.cases.views.CaseViewSet.start_workflow")
    def _create_case(self, mock_start_workflow):
        mock_start_workflow.return_value = "task_start_workflow: completed"
        url = reverse("cases-list")
        data = {
            "description": "Test case description",
            "request_date": timezone.now().date().isoformat(),
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["id"]

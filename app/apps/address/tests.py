from django.core import management
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cases.models import Case, CaseDocument
from apps.homeownerassociation.models import HomeownerAssociation
from apps.workflow.models import GenericCompletedTask
from model_bakery import baker
from utils.test_utils import get_authenticated_client, get_test_user


class AddressApiTest(APITestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()
        self.client = get_authenticated_client()
        self.user = get_test_user()

        self.hoa = baker.make(HomeownerAssociation, number_of_apartments=20)
        self.case = baker.make(Case, homeowner_association=self.hoa)

    def test_get_mijn_amsterdam_eindpresentatie_document_returns_document_id(self):
        case_document = CaseDocument.objects.create(
            case=self.case,
            name="eindpresentatie.pdf",
            document=SimpleUploadedFile(
                "eindpresentatie.pdf",
                b"%PDF-1.4\n%Fake PDF content",
                content_type="application/pdf",
            ),
        )
        GenericCompletedTask.objects.create(
            case=self.case,
            task_name="Activity_0qoynbp",
            description="Completed eindpresentatie task",
            author=self.user,
            variables={
                "mapped_form_data": {
                    "document_name": {"value": case_document.name},
                }
            },
        )

        url = reverse(
            "address-mijn-amsterdam-eindpresentatie-document",
            kwargs={"case_id": self.case.id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["case_id"], self.case.id)
        self.assertEqual(response.data["eindpresentatie_document_id"], case_document.id)

    def test_get_mijn_amsterdam_eindpresentatie_document_returns_null_without_match(
        self,
    ):
        url = reverse(
            "address-mijn-amsterdam-eindpresentatie-document",
            kwargs={"case_id": self.case.id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["eindpresentatie_document_id"])

    def test_download_mijn_amsterdam_eindpresentatie_document(self):
        case_document = CaseDocument.objects.create(
            case=self.case,
            name="eindpresentatie.pdf",
            document=SimpleUploadedFile(
                "eindpresentatie.pdf",
                b"%PDF-1.4\n%Fake PDF content",
                content_type="application/pdf",
            ),
        )
        GenericCompletedTask.objects.create(
            case=self.case,
            task_name="Activity_0qoynbp",
            description="Completed eindpresentatie task",
            author=self.user,
            variables={
                "mapped_form_data": {
                    "document_name": {"value": case_document.name},
                }
            },
        )

        url = reverse(
            "address-mijn-amsterdam-eindpresentatie-document-download",
            kwargs={"case_id": self.case.id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Content-Disposition", response)

    def test_download_mijn_amsterdam_eindpresentatie_document_not_found(self):
        url = reverse(
            "address-mijn-amsterdam-eindpresentatie-document-download",
            kwargs={"case_id": self.case.id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

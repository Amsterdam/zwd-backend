from unittest.mock import patch
from django.core import management
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.homeownerassociation.models import (
    District,
    HomeownerAssociation,
    Neighborhood,
    Wijk,
)
from apps.cases.models import AdviceType, Case, CaseDocument, CaseStatus
from apps.workflow.models import CaseUserTask, CaseWorkflow, GenericCompletedTask
from utils.test_utils import (
    get_authenticated_client,
    get_test_user,
    get_unauthenticated_client,
)
import uuid
from django.core.files.uploadedfile import SimpleUploadedFile
from model_bakery import baker


class CaseUserTaskApiTests(APITestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()
        self.client = get_authenticated_client()

    def test_unauthenticated_get(self):
        url = reverse("tasks-list")
        client = get_unauthenticated_client()
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_get(self):
        url = reverse("tasks-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_get_empty(self):
        url = reverse("tasks-list")
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(
            data, {"count": 0, "next": None, "previous": None, "results": []}
        )

    def test_retrieve_tasks_filter_by_district(self):
        url = reverse("tasks-list")
        district_name = "District A"
        district = baker.make(District, name=district_name)
        baker.make(District, name="other district")
        homeowner_association = baker.make(
            HomeownerAssociation,
            number_of_appartments=13,
            district=district,
            name="ABC",
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        workflow = baker.make(
            CaseWorkflow, case=case, completed=False, workflow_type="sub_workflow"
        )
        case_user_task = baker.make(
            CaseUserTask,
            case=case,
            task_name="task1",
            completed=False,
            task_id=uuid.uuid4(),
            due_date="2021-01-01",
            initiated_by=get_test_user(),
            requires_review=False,
            workflow=workflow,
        )

        response = self.client.get(url, {"district": district_name})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], case_user_task.id)

    def test_retrieve_tasks_filter_by_wijk(self):
        url = reverse("tasks-list")
        wijk_name = "Wijk B"
        wijk = baker.make(Wijk, name=wijk_name)
        baker.make(Wijk, name="Other name")
        homeowner_association = baker.make(
            HomeownerAssociation,
            number_of_appartments=13,
            wijk=wijk,
            name="ABC",
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        workflow = baker.make(
            CaseWorkflow, case=case, completed=False, workflow_type="sub_workflow"
        )

        case_user_task = baker.make(
            CaseUserTask,
            case=case,
            task_name="task1",
            completed=False,
            task_id=uuid.uuid4(),
            due_date="2021-01-01",
            initiated_by=get_test_user(),
            requires_review=False,
            workflow=workflow,
        )

        response = self.client.get(url, {"wijk": wijk_name})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], case_user_task.id)

    def test_retrieve_tasks_filter_by_neighborhood(self):
        url = reverse("tasks-list")
        neighborhood_name = "Buurt a"
        neighborhood = baker.make(Neighborhood, name=neighborhood_name)
        baker.make(Neighborhood, name="Other name")
        homeowner_association = baker.make(
            HomeownerAssociation,
            number_of_appartments=13,
            neighborhood=neighborhood,
            name="ABC",
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        workflow = baker.make(
            CaseWorkflow, case=case, completed=False, workflow_type="sub_workflow"
        )

        case_user_task = baker.make(
            CaseUserTask,
            case=case,
            task_name="task1",
            completed=False,
            task_id=uuid.uuid4(),
            due_date="2021-01-01",
            initiated_by=get_test_user(),
            requires_review=False,
            workflow=workflow,
        )

        response = self.client.get(url, {"neighborhood": neighborhood_name})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], case_user_task.id)

    def test_retrieve_tasks_filter_status(self):
        url = reverse("tasks-list")
        case_status = baker.make(CaseStatus, name="Closed")
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_appartments=13, name="ABC"
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
            status=case_status,
        )
        workflow = baker.make(
            CaseWorkflow, case=case, completed=False, workflow_type="sub_workflow"
        )

        case_user_task = baker.make(
            CaseUserTask,
            case=case,
            task_name="task1",
            completed=False,
            task_id=uuid.uuid4(),
            due_date="2021-01-01",
            initiated_by=get_test_user(),
            requires_review=False,
            workflow=workflow,
        )

        response = self.client.get(url, {"status": case_status})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], case_user_task.id)

    def test_search_task_by_homeowner_association(self):
        url = reverse("tasks-list")
        homeowner_association_name = "HOA for task test"
        homeowner_association = baker.make(
            HomeownerAssociation,
            number_of_appartments=13,
            name=homeowner_association_name,
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        workflow = baker.make(
            CaseWorkflow, case=case, completed=False, workflow_type="sub_workflow"
        )

        case_user_task = baker.make(
            CaseUserTask,
            case=case,
            task_name="task1",
            completed=False,
            task_id=uuid.uuid4(),
            due_date="2021-01-01",
            initiated_by=get_test_user(),
            requires_review=False,
            workflow=workflow,
        )

        homeowner_association_name_partial = homeowner_association_name[2:8]
        response = self.client.get(
            url, {"homeowner_association_name": homeowner_association_name_partial}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], case_user_task.id)

    @patch("apps.workflow.views.complete_generic_user_task_and_create_new_user_tasks")
    def test_complete_file_task(
        self, complete_generic_user_task_and_create_new_user_tasks
    ):
        complete_generic_user_task_and_create_new_user_tasks.return_value = (
            "task completed"
        )
        case, case_user_task = self._create_case_and_task()

        url = reverse("generictasks-complete-file-task")
        data = {
            "case_user_task_id": case_user_task.id,
            "case": case.id,
            "name": "test_document",
            "document": SimpleUploadedFile(
                "test_document.pdf", b"file_content", content_type="application/pdf"
            ),
        }
        response = self.client.post(url, data=data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            GenericCompletedTask.objects.filter(
                case_user_task_id=case_user_task.id
            ).exists()
        )
        self.assertTrue(CaseDocument.objects.filter(name="test_document").exists())

    @patch("apps.workflow.views.complete_generic_user_task_and_create_new_user_tasks")
    def test_complete_task(self, complete_generic_user_task_and_create_new_user_tasks):
        complete_generic_user_task_and_create_new_user_tasks.return_value = (
            "task completed"
        )
        case, case_user_task = self._create_case_and_task()

        url = reverse("generictasks-complete-task")
        data = {
            "case_user_task_id": case_user_task.id,
            "case": case.id,
            "variables": {"test": "test"},
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            GenericCompletedTask.objects.filter(
                case_user_task_id=case_user_task.id
            ).exists()
        )

    def test_get_case_user_tasks(self):
        _, _ = self._create_case_and_task()
        url = reverse("tasks-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_get_case_user_task_detail(self):
        _, case_user_task = self._create_case_and_task()
        url = reverse("tasks-detail", kwargs={"pk": case_user_task.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], case_user_task.id)

    def test_complete_task_invalid_id(self):
        url = reverse("generictasks-complete-task")
        data = {
            "case_user_task_id": uuid.uuid4(),
            "case": uuid.uuid4(),
            "variables": {"test": "test"},
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.workflow.views.complete_generic_user_task_and_create_new_user_tasks")
    def test_complete_task_with_requires_review(
        self, complete_generic_user_task_and_create_new_user_tasks
    ):
        complete_generic_user_task_and_create_new_user_tasks.return_value = (
            "task completed"
        )
        case = self._create_case()
        case = Case.objects.get(id=case)
        case_wf = CaseWorkflow.objects.create(
            case=case, completed=False, workflow_type="beoordeling"
        )
        user = get_test_user()
        case_user_task = CaseUserTask.objects.create(
            task_name="task1",
            completed=False,
            case=case,
            task_id=uuid.uuid4(),
            due_date="2021-01-01",
            workflow_id=case_wf.id,
            initiated_by=user,
            requires_review=True,
        )
        url = reverse("generictasks-complete-task")
        data = {
            "case_user_task_id": case_user_task.id,
            "case": case.id,
            "variables": {"test": "test"},
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_complete_file_task_missing_file(self):
        case, case_user_task = self._create_case_and_task()
        url = reverse("generictasks-complete-file-task")
        data = {
            "case_user_task_id": case_user_task.id,
            "case": case.id,
            "name": "test_document",
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def _create_case_and_task(self):
        case_id = self._create_case()
        case = Case.objects.get(id=case_id)
        case_wf = CaseWorkflow.objects.create(
            case=case, completed=False, workflow_type="beoordeling"
        )
        case_user_task = CaseUserTask.objects.create(
            task_name="task1",
            completed=False,
            case=case,
            task_id=uuid.uuid4(),
            due_date="2021-01-01",
            workflow_id=case_wf.id,
            initiated_by=get_test_user(),
            requires_review=False,
        )
        return case, case_user_task

    @patch("apps.cases.views.CaseViewSet.start_workflow")
    def _create_case(self, mock_start_workflow):
        hoa = HomeownerAssociation.objects.create(
            name="HOA", number_of_appartments=12, build_year=2010
        )
        mock_start_workflow.return_value = "task_start_workflow: completed"
        url = reverse("cases-list")
        data = {"description": "Test case description", "homeowner_association": hoa.id}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["id"]

import os
from django.db import models
from apps.cases.models import Case
from SpiffWorkflow.camunda.parser.CamundaParser import CamundaParser

class CaseWorkflow(models.Model):
    case = models.ForeignKey(
        to=Case,
        related_name="workflows",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    def get_workflow_spec(self, workflow_type):
        parser = CamundaParser()
        path = self.get_workflow_path(workflow_type)
        for f in self.get_workflow_spec_files(path):
            parser.add_bpmn_file(f)
        spec = parser.get_spec(workflow_type)
        print(spec.__dict__)
        # wf = BpmnWorkflow(workflow_spec)
        return spec


    def get_workflow_spec_files(self, path):
        return [
            os.path.join(path, f)
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and self.is_bpmn_file(f)
        ]

    def is_bpmn_file(self, file_name):
        return file_name.split(".")[-1] == "bpmn"
    

    def get_workflow_path(self, workflow_type, theme_name="default", workflow_version="7.1.0"):
        path = os.path.join(
            self.get_base_path(),
            "bpmn_files",
            theme_name.lower(),
            workflow_type.lower(),
            workflow_version.lower(),
        )
        return path


    def get_base_path(self):
        return os.path.dirname(os.path.realpath(__file__))
import datetime
import glob
import json
import os

from django.conf import settings


def get_bpmn_files():
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "bpmn_files")
    files = glob.glob(os.path.join(path, "**", "*.bpmn"), recursive=True)
    workflows = []

    if files:
        for file in files:
            # Split the file path to extract workflow type, version, and file name
            parts = file.split(os.sep)
            workflow_type = parts[-3]  # The folder name before the version folder
            version = parts[-2]  # The version folder name
            file_name = parts[-1]  # The actual file name

            # Append the JSON object to the list
            workflows.append(
                {
                    "workflow_type": workflow_type,
                    "version": version,
                    "file_name": file_name,
                }
            )

    return workflows


def get_bpmn_file(workflow_type, version, file_name):
    # Construct the file path based on the provided parameters
    path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "bpmn_files",
        "default",
        workflow_type,
        version,
        file_name,
    )

    # Check if the file exists
    if os.path.exists(path) and file_name.endswith(".bpmn"):
        # Read the file content
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
            return content


def map_variables_on_task_spec_form(variables, task_spec_form):
    # transforms form result data and adds labels for the frontend
    form = dict((f.get("name"), f) for f in task_spec_form)
    return dict(
        (
            k,
            {
                "label": form.get(k, {}).get("label", v.get("value")),
                "value": (
                    v.get("value")
                    if not form.get(k, {}).get("options")
                    else (
                        [
                            dict(
                                (o.get("value"), o)
                                for o in form.get(k, {}).get("options")
                            )
                            .get(vv, {})
                            .get("label", vv)
                            for vv in v.get("value")
                        ]
                        if isinstance(v.get("value"), list)
                        else dict(
                            (o.get("value"), o) for o in form.get(k, {}).get("options")
                        )
                        .get(v.get("value"), {})
                        .get("label", v.get("value"))
                    )
                ),
            },
        )
        for k, v in variables.items()
        if isinstance(v, dict)
    )


def get_initial_data_from_config(
    theme_name, workflow_type, workflow_version, message_name=None
):
    validated_workflow_spec_config = validate_workflow_spec(
        settings.WORKFLOW_SPEC_CONFIG
    )
    config = validated_workflow_spec_config.get(theme_name)
    if not config:
        theme_name = "default"
        config = validated_workflow_spec_config.get(theme_name, {})

    config = config.get(workflow_type, {})
    if not config:
        raise Exception(
            f"Workflow type '{workflow_type}', does not exist in this workflow_spec config"
        )
    initial_data = config.get("initial_data", {})

    version = config.get("versions", {}).get(workflow_version)
    if (
        message_name
        and version
        and version.get("messages", {}).get(message_name, {}).get("initial_data", {})
    ):
        initial_data = (
            version.get("messages", {}).get(message_name, {}).get("initial_data", {})
        )

    def pre_serialize_timedelta(value):
        if isinstance(value, datetime.timedelta):
            duration = settings.DEFAULT_WORKFLOW_TIMER_DURATIONS.get(
                settings.ENVIRONMENT
            )
            if duration:
                value = duration
            return json.loads(json.dumps(value, default=str))
        return value

    initial_data = dict(
        (k, pre_serialize_timedelta(v)) for k, v in initial_data.items()
    )
    return initial_data


def validate_workflow_spec(workflow_spec_config):
    from .serializers import WorkflowSpecConfigSerializer

    serializer = WorkflowSpecConfigSerializer(data=workflow_spec_config)
    if serializer.is_valid():
        pass
    else:
        raise Exception(
            {
                "message": "settings WORKFLOW_SPEC_CONFIG not valid",
                "details": serializer.errors,
            }
        )
    return serializer.data


def parse_task_spec_form(form):
    trans_types = {
        "enum": "select",
        "boolean": "checkbox",
        "string": "text",
        "long": "number",
    }
    fields = [
        {
            "label": f.label,
            "options": [
                {
                    "value": o.id,
                    "label": o.name,
                }
                for o in f.__dict__.get("options", [])
            ],
            "name": f.id,
            "type": (
                "multiselect"
                if bool([v.name for v in f.validation if v.name == "multiple"])
                else trans_types.get(f.type, "text")
            ),
            "required": not bool(
                [v.name for v in f.validation if v.name == "optional"]
            ),
            "tooltip": next(
                iter([v.value for v in f.properties if v.id == "tooltip"]), None
            ),
        }
        for f in form.fields
    ]
    return fields

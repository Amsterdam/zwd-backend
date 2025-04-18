import datetime
import glob
import json
import os
from django.conf import settings


def get_bpmn_models():
    path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "bpmn_files", "default"
    )
    # Ensure the path exists
    if not os.path.isdir(path):
        return []

    # Get all subdirectories in the specified path
    try:
        dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        dirs.sort()
        return dirs
    except Exception as e:
        # Handle exceptions (e.g., permission issues)
        return {"error": str(e)}


def get_bpmn_model_versions_and_files(model_name):
    base_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "bpmn_files", "default", model_name
    )

    if not os.path.isdir(base_path):
        return {"error": f"Model '{model_name}' not found"}, 404

    versions = []

    for version_dir in os.listdir(base_path):
        version_path = os.path.join(base_path, version_dir)
        if os.path.isdir(version_path):
            # Assuming there's only one .bpmn file per version
            bpmn_files = glob.glob(os.path.join(version_path, "*.bpmn"))
            if bpmn_files:
                version = version_dir
                bpmn_file_name = os.path.basename(
                    bpmn_files[0]
                )  # Get the first .bpmn file
                versions.append(
                    {
                        "version": version,
                        "file_name": bpmn_file_name,
                        "model": model_name,
                    }
                )

    # Sort versions by the 'version' key. Assuming versions are semver or can be lexicographically sorted
    versions.sort(key=lambda x: tuple(map(int, x["version"].split("."))))

    return versions


def get_bpmn_file(model_name, version):
    # Construct the file path based on the provided parameters
    path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "bpmn_files",
        "default",
        model_name,
        version,
        f"{model_name}.bpmn",
    )

    # Check if the file exists
    if os.path.exists(path):
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


def get_latest_version_from_config(workflow_type, director_version=None):
    def get_major(version):
        return int(version.split(".")[0])

    # Validate and retrieve the workflow spec configuration
    validated_workflow_spec_config = validate_workflow_spec(
        settings.WORKFLOW_SPEC_CONFIG
    )
    theme_name = "default"
    config = validated_workflow_spec_config.get(theme_name, {}).get(workflow_type, {})

    if not config:
        raise Exception(
            f"Workflow type '{workflow_type}' does not exist in the workflow spec config"
        )

    # Retrieve and sort workflow type versions
    workflow_type_versions = sorted(config.get("versions", {}).keys())
    if not workflow_type_versions:
        raise Exception(
            f"No versions found for workflow type '{workflow_type}' under theme '{theme_name}'"
        )

    if director_version:
        # Filter versions to ensure they are not higher than the director's major version
        workflow_type_versions = [
            version
            for version in workflow_type_versions
            if get_major(director_version) >= get_major(version)
        ]

    if not workflow_type_versions:
        raise Exception(
            f"No compatible versions found for workflow type '{workflow_type}' with director version '{director_version}'"
        )

    # Return the highest available version
    return workflow_type_versions[-1]

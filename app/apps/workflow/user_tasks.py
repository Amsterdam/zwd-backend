import logging
import sys

from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

DEFAULT_USER_TASK_DUE_DATE = relativedelta(weeks=1)


class BpmnField:
    def __init__(self, _user_task, **kwargs):
        args = ["label", "name", "options", "type", "required", "tooltip"]
        if not isinstance(_user_task, user_task) and not kwargs.keys() in args:
            raise Exception
        self.label = kwargs.get("label")
        self.options = kwargs.get("options")
        self.name = kwargs.get("name")
        self.type = kwargs.get("type")
        self.required = kwargs.get("required")
        self.tooltip = kwargs.get("tooltip")
        self.user_task = _user_task

    def get_value(self, k):
        return (
            getattr(self.user_task, f"field__{self.name}__{k}")
            if hasattr(self.user_task, f"field__{self.name}__{k}")
            else getattr(self, k)
        )

    @property
    def asdict(self):
        d = dict(
            (k, self.get_value(k))
            for k in ["label", "options", "type", "required", "tooltip"]
        )
        d.update({"name": self.name})
        return d


class BpmnForm:
    user_task = None

    def __init__(self, user_task_instance):
        if not isinstance(user_task_instance, user_task):
            raise Exception
        self.user_task = user_task_instance

    @property
    def form(self):
        form = self.user_task.case_user_task.form
        if hasattr(self.user_task, "form"):
            form = self.user_task.form
        elif form and isinstance(form, list):
            form = [
                BpmnField(_user_task=self.user_task, **field).asdict for field in form
            ]
        return form


def get_task_by_name(task_name):
    current_module = sys.modules[__name__]
    user_tasks = list(
        filter(lambda class_name: class_name[:5] == "task_", dir(current_module))
    )

    for ut in user_tasks:
        cls = getattr(current_module, ut)
        if cls.get_task_name() == task_name:
            return cls
    return user_task


class user_task:

    # It would be nice if all tasks implement their own due_date, but for
    # now we'll set a default as well.
    due_date = DEFAULT_USER_TASK_DUE_DATE
    case_user_task = None

    def __init__(self, case_user_task_instance):
        from .models import CaseUserTask

        if not isinstance(case_user_task_instance, CaseUserTask):
            raise Exception
        self.case_user_task = case_user_task_instance

    @classmethod
    def get_due_date(cls, case):
        return getattr(cls, "due_date")

    @classmethod
    def get_task_name(cls):
        return getattr(cls, "_task_name", cls.__name__)

    def get_form(self):
        return BpmnForm(self)

    def get_data(self):
        return {}

    def mapped_form_data(self, data):
        return {}

    def instance_created(self):
        return


# class task_vve_gezond(user_task):
#     _task_name = "task_vve_gezond"

# class task_duurzaam_mjop(user_task):
#     _task_name = "task_duurzaam_mjop"

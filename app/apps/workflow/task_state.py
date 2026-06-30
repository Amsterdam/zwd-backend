def get_current_task_specs(case_workflow) -> list[str]:
    return list(
        case_workflow.tasks.filter(completed=False).values_list("task_name", flat=True)
    )

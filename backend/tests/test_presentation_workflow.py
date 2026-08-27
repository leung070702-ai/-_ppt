"""Unit tests for the ordered presentation workflow foundation."""

from __future__ import annotations

import logging

from app.workflows.presentation_workflow import (
    NODE_ORDER,
    ApplyEditsResult,
    EditOperation,
    EditPlan,
    ExportResult,
    NodeStatus,
    PresentationSummary,
    PresentationWorkflow,
    QualityCheckResult,
    RubricResult,
    SlideAnalysis,
    StorylineAnalysis,
    UploadRequest,
    WorkflowStatus,
)


class RecordingNode:
    def __init__(self, name: str, output, calls: list[str]) -> None:
        self.name = name
        self.output = output
        self.calls = calls

    def run(self, input):
        self.calls.append(self.name)
        return self.output


def request() -> UploadRequest:
    return UploadRequest(
        file_path="storage/uploads/task/source.pptx",
        original_filename="source.pptx",
        file_size=10,
        modification_request="Improve the storyline",
    )


def all_success_nodes(calls: list[str]) -> dict[str, RecordingNode]:
    return {
        "parse_presentation": RecordingNode(
            "parse_presentation", PresentationSummary(slide_count=1), calls
        ),
        "parse_rubric": RecordingNode(
            "parse_rubric", RubricResult(criteria=["clarity"]), calls
        ),
        "analyze_storyline": RecordingNode(
            "analyze_storyline", StorylineAnalysis(summary="ok"), calls
        ),
        "analyze_slides": RecordingNode(
            "analyze_slides", SlideAnalysis(findings=[]), calls
        ),
        "create_edit_plan": RecordingNode(
            "create_edit_plan", EditPlan(operations=[]), calls
        ),
        "apply_edits": RecordingNode(
            "apply_edits", ApplyEditsResult(output_file="out.pptx"), calls
        ),
        "quality_check": RecordingNode(
            "quality_check", QualityCheckResult(passed=True), calls
        ),
        "export_result": RecordingNode(
            "export_result", ExportResult(output_file="out.pptx"), calls
        ),
    }


def test_workflow_runs_in_fixed_order_and_serializes() -> None:
    calls: list[str] = []
    state = PresentationWorkflow.new_state(request(), task_id="task-1")
    result = PresentationWorkflow(nodes=all_success_nodes(calls)).run(state)

    assert result.status is WorkflowStatus.SUCCEEDED
    assert calls == [
        name
        for name in NODE_ORDER
        if name not in {"validate_upload", "validate_edit_plan"}
    ]
    assert [record.node for record in result.node_records] == list(NODE_ORDER)
    assert all(record.status is NodeStatus.SUCCEEDED for record in result.node_records)
    assert result.to_json_dict()["task_id"] == "task-1"


def test_placeholder_failure_skips_all_dependent_nodes() -> None:
    state = PresentationWorkflow.new_state(request(), task_id="task-2")
    result = PresentationWorkflow().run(state)

    assert result.status is WorkflowStatus.FAILED
    assert result.errors[0].code == "NODE_NOT_IMPLEMENTED"
    assert result.node_records[0].status is NodeStatus.SUCCEEDED
    assert result.node_records[1].node == "parse_presentation"
    assert result.node_records[1].status is NodeStatus.FAILED
    assert all(
        record.status is NodeStatus.SKIPPED for record in result.node_records[2:]
    )


def test_invalid_edit_plan_prevents_apply_edits() -> None:
    calls: list[str] = []
    nodes = all_success_nodes(calls)
    nodes["create_edit_plan"] = RecordingNode(
        "create_edit_plan",
        EditPlan(operations=[EditOperation(operation="run_shell", slide_number=1)]),
        calls,
    )
    state = PresentationWorkflow.new_state(request(), task_id="task-3")
    result = PresentationWorkflow(nodes=nodes).run(state)

    assert result.status is WorkflowStatus.FAILED
    assert result.errors[-1].code == "EDIT_PLAN_INVALID"
    assert "apply_edits" not in calls
    apply_record = next(
        record for record in result.node_records if record.node == "apply_edits"
    )
    assert apply_record.status is NodeStatus.SKIPPED


def test_logging_contains_only_safe_workflow_metadata(caplog) -> None:
    caplog.set_level(logging.INFO)
    state = PresentationWorkflow.new_state(request(), task_id="task-4")
    PresentationWorkflow().run(state)

    assert any(
        getattr(record, "task_id", None) == "task-4" for record in caplog.records
    )
    text = " ".join(record.getMessage() for record in caplog.records)
    assert "source.pptx" not in text
    assert "Improve the storyline" not in text

"""Typed, ordered foundation for the presentation analysis workflow.

The module deliberately contains no PPT or LLM side effects.  Concrete parser,
LLM and editor implementations can be injected later through the node map.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import PurePath
from typing import Any, Generic, NoReturn, Protocol, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowNodeError(RuntimeError):
    """Expected, user-safe failure raised by a workflow node or guard."""

    code = "WORKFLOW_NODE_ERROR"


class UploadValidationError(WorkflowNodeError):
    code = "UPLOAD_INVALID"


class NodeNotImplementedError(WorkflowNodeError):
    code = "NODE_NOT_IMPLEMENTED"


class WorkflowDependencyError(WorkflowNodeError):
    code = "MISSING_NODE_DEPENDENCY"


class EditPlanValidationError(WorkflowNodeError):
    code = "EDIT_PLAN_INVALID"


class UploadRequest(BaseModel):
    """Input accepted by the workflow; no file contents are stored here."""

    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(min_length=1, max_length=1024)
    original_filename: str = Field(min_length=1, max_length=255)
    file_size: int = Field(default=0, ge=0)
    mime_type: str | None = Field(default=None, max_length=255)
    modification_request: str = Field(min_length=1, max_length=4000)
    rubric_text: str | None = Field(default=None, max_length=20_000)


class ValidatedUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: str
    original_filename: str
    file_size: int
    modification_request: str


class ParsePresentationInput(BaseModel):
    upload: ValidatedUpload


class PresentationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slide_count: int = Field(default=0, ge=0)
    slides: list[dict[str, Any]] = Field(default_factory=list)
    layout_metadata: dict[str, Any] = Field(default_factory=dict)


class ParseRubricInput(BaseModel):
    presentation: PresentationSummary
    rubric_text: str = ""


class RubricResult(BaseModel):
    criteria: list[str] = Field(default_factory=list)
    summary: str = ""


class AnalyzeStorylineInput(BaseModel):
    presentation: PresentationSummary
    rubric: RubricResult


class StorylineAnalysis(BaseModel):
    summary: str = ""
    sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnalyzeSlidesInput(BaseModel):
    presentation: PresentationSummary
    rubric: RubricResult
    storyline: StorylineAnalysis


class SlideAnalysis(BaseModel):
    findings: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CreateEditPlanInput(BaseModel):
    presentation: PresentationSummary
    rubric: RubricResult
    storyline: StorylineAnalysis
    slides: SlideAnalysis
    modification_request: str


ALLOWED_EDIT_OPERATIONS = frozenset(
    {"replace_text", "update_table_cell", "add_textbox", "delete_shape"}
)


class EditOperation(BaseModel):
    operation: str
    slide_number: int = Field(ge=1)
    element_id: int | None = Field(default=None, ge=1)
    content: str | None = Field(default=None, max_length=10_000)


class EditPlan(BaseModel):
    operations: list[EditOperation] = Field(default_factory=list)
    rationale: str = Field(default="", max_length=10_000)
    warnings: list[str] = Field(default_factory=list)


class ValidateEditPlanInput(BaseModel):
    edit_plan: EditPlan
    presentation: PresentationSummary


class ValidatedEditPlan(EditPlan):
    validated: bool = True
    validated_at: str


class ApplyEditsInput(BaseModel):
    """The only input accepted by a future PPT editor."""

    source_file: str
    output_file: str = ""
    edit_plan: ValidatedEditPlan


class ApplyEditsResult(BaseModel):
    output_file: str = ""
    applied_operations: int = Field(default=0, ge=0)
    changes: list[dict[str, Any]] = Field(default_factory=list)


class QualityCheckInput(BaseModel):
    apply_result: ApplyEditsResult
    edit_plan: ValidatedEditPlan


class QualityCheckResult(BaseModel):
    passed: bool
    warnings: list[str] = Field(default_factory=list)


class ExportResult(BaseModel):
    output_file: str
    download_id: str | None = None


class QualityCheckExportInput(BaseModel):
    quality: QualityCheckResult
    apply_result: ApplyEditsResult


class WorkflowError(BaseModel):
    node: str
    code: str
    message: str


class NodeExecutionRecord(BaseModel):
    node: str
    status: NodeStatus
    started_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None


class PresentationWorkflowState(BaseModel):
    """Complete, JSON-serializable workflow snapshot."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    request: UploadRequest
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_node: str | None = None
    node_records: list[NodeExecutionRecord] = Field(default_factory=list)
    errors: list[WorkflowError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    validated_upload: ValidatedUpload | None = None
    presentation: PresentationSummary | None = None
    rubric: RubricResult | None = None
    storyline: StorylineAnalysis | None = None
    slides: SlideAnalysis | None = None
    edit_plan: EditPlan | None = None
    validated_edit_plan: ValidatedEditPlan | None = None
    apply_result: ApplyEditsResult | None = None
    quality_result: QualityCheckResult | None = None
    export_result: ExportResult | None = None

    def to_json_dict(self) -> dict[str, Any]:
        """Return a persistence-safe representation without Python objects."""

        return self.model_dump(mode="json")


WorkflowState = PresentationWorkflowState
InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class WorkflowNode(Protocol, Generic[InputT, OutputT]):
    name: str

    def run(self, input: InputT) -> OutputT:
        """Run one node without changing workflow state or file storage."""


class ValidateUploadNode:
    name = "validate_upload"

    def run(self, input: UploadRequest) -> ValidatedUpload:
        suffix = PurePath(input.original_filename).suffix.lower()
        if suffix != ".pptx":
            raise UploadValidationError("Only .pptx uploads are supported")
        if input.file_size <= 0:
            raise UploadValidationError("Uploaded file must not be empty")
        if ".." in PurePath(input.file_path).parts:
            raise UploadValidationError(
                "Upload path must not contain traversal segments"
            )
        return ValidatedUpload(
            file_path=input.file_path,
            original_filename=input.original_filename,
            file_size=input.file_size,
            modification_request=input.modification_request,
        )


class ValidateEditPlanNode:
    name = "validate_edit_plan"

    def run(self, input: ValidateEditPlanInput) -> ValidatedEditPlan:
        for operation in input.edit_plan.operations:
            if operation.operation not in ALLOWED_EDIT_OPERATIONS:
                raise EditPlanValidationError(
                    f"Unsupported edit operation: {operation.operation}"
                )
            if operation.slide_number > input.presentation.slide_count:
                raise EditPlanValidationError(
                    f"Slide {operation.slide_number} is outside the presentation"
                )
        return ValidatedEditPlan(
            **input.edit_plan.model_dump(),
            validated_at=_utc_now(),
        )


class PlaceholderNode:
    """Explicit placeholder for a node whose implementation is not in scope."""

    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, input: BaseModel) -> NoReturn:
        raise NodeNotImplementedError(f"Node '{self.name}' is not implemented")


@dataclass(frozen=True)
class _NodeSpec:
    name: str
    input_type: type[BaseModel]
    output_type: type[BaseModel]
    build_input: Callable[[PresentationWorkflowState], BaseModel]
    apply_output: Callable[[PresentationWorkflowState, BaseModel], None]


NODE_ORDER: tuple[str, ...] = (
    "validate_upload",
    "parse_presentation",
    "parse_rubric",
    "analyze_storyline",
    "analyze_slides",
    "create_edit_plan",
    "validate_edit_plan",
    "apply_edits",
    "quality_check",
    "export_result",
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _required(value: Any, dependency: str) -> Any:
    if value is None:
        raise WorkflowDependencyError(f"Required dependency '{dependency}' is missing")
    return value


def _build_specs() -> dict[str, _NodeSpec]:
    return {
        "validate_upload": _NodeSpec(
            "validate_upload", UploadRequest, ValidatedUpload,
            lambda s: s.request, lambda s, o: setattr(s, "validated_upload", o)
        ),
        "parse_presentation": _NodeSpec(
            "parse_presentation", ParsePresentationInput, PresentationSummary,
            lambda s: ParsePresentationInput(
                upload=_required(s.validated_upload, "validate_upload")
            ),
            lambda s, o: setattr(s, "presentation", o),
        ),
        "parse_rubric": _NodeSpec(
            "parse_rubric", ParseRubricInput, RubricResult,
            lambda s: ParseRubricInput(
                presentation=_required(s.presentation, "parse_presentation"),
                rubric_text=s.request.rubric_text or "",
            ),
            lambda s, o: setattr(s, "rubric", o),
        ),
        "analyze_storyline": _NodeSpec(
            "analyze_storyline", AnalyzeStorylineInput, StorylineAnalysis,
            lambda s: AnalyzeStorylineInput(
                presentation=_required(s.presentation, "parse_presentation"),
                rubric=_required(s.rubric, "parse_rubric"),
            ),
            lambda s, o: setattr(s, "storyline", o),
        ),
        "analyze_slides": _NodeSpec(
            "analyze_slides", AnalyzeSlidesInput, SlideAnalysis,
            lambda s: AnalyzeSlidesInput(
                presentation=_required(s.presentation, "parse_presentation"),
                rubric=_required(s.rubric, "parse_rubric"),
                storyline=_required(s.storyline, "analyze_storyline"),
            ),
            lambda s, o: setattr(s, "slides", o),
        ),
        "create_edit_plan": _NodeSpec(
            "create_edit_plan", CreateEditPlanInput, EditPlan,
            lambda s: CreateEditPlanInput(
                presentation=_required(s.presentation, "parse_presentation"),
                rubric=_required(s.rubric, "parse_rubric"),
                storyline=_required(s.storyline, "analyze_storyline"),
                slides=_required(s.slides, "analyze_slides"),
                modification_request=s.request.modification_request,
            ),
            lambda s, o: setattr(s, "edit_plan", o),
        ),
        "validate_edit_plan": _NodeSpec(
            "validate_edit_plan", ValidateEditPlanInput, ValidatedEditPlan,
            lambda s: ValidateEditPlanInput(
                edit_plan=_required(s.edit_plan, "create_edit_plan"),
                presentation=_required(s.presentation, "parse_presentation"),
            ),
            lambda s, o: setattr(s, "validated_edit_plan", o),
        ),
        "apply_edits": _NodeSpec(
            "apply_edits", ApplyEditsInput, ApplyEditsResult,
            lambda s: ApplyEditsInput(
                source_file=_required(s.validated_upload, "validate_upload").file_path,
                edit_plan=_required(s.validated_edit_plan, "validate_edit_plan"),
            ),
            lambda s, o: setattr(s, "apply_result", o),
        ),
        "quality_check": _NodeSpec(
            "quality_check", QualityCheckInput, QualityCheckResult,
            lambda s: QualityCheckInput(
                apply_result=_required(s.apply_result, "apply_edits"),
                edit_plan=_required(s.validated_edit_plan, "validate_edit_plan"),
            ),
            lambda s, o: setattr(s, "quality_result", o),
        ),
        "export_result": _NodeSpec(
            "export_result", QualityCheckExportInput, ExportResult,
            lambda s: QualityCheckExportInput(
                quality=_required(s.quality_result, "quality_check"),
                apply_result=_required(s.apply_result, "apply_edits"),
            ),
            lambda s, o: setattr(s, "export_result", o),
        ),
    }


class PresentationWorkflow:
    """Single ordered orchestrator for all presentation workflow nodes."""

    node_order = NODE_ORDER

    def __init__(
        self,
        nodes: Mapping[str, WorkflowNode[Any, Any]] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        unknown = set(nodes or {}) - set(NODE_ORDER)
        if unknown:
            raise ValueError(f"Unknown workflow nodes: {sorted(unknown)}")
        defaults: dict[str, WorkflowNode[Any, Any]] = {
            "validate_upload": ValidateUploadNode(),
            "validate_edit_plan": ValidateEditPlanNode(),
        }
        defaults.update(
            {name: PlaceholderNode(name) for name in NODE_ORDER if name not in defaults}
        )
        if nodes:
            defaults.update(nodes)
        self._nodes = defaults
        self._specs = _build_specs()
        self._logger = logger or logging.getLogger(__name__)

    @staticmethod
    def new_state(
        request: UploadRequest, task_id: str | None = None
    ) -> PresentationWorkflowState:
        return PresentationWorkflowState(
            task_id=task_id or str(uuid4()), request=request
        )

    def run(self, state: PresentationWorkflowState) -> PresentationWorkflowState:
        if state.status not in {WorkflowStatus.PENDING, WorkflowStatus.RUNNING}:
            return state
        state.status = WorkflowStatus.RUNNING
        for index, name in enumerate(NODE_ORDER):
            if state.status == WorkflowStatus.FAILED:
                break
            spec = self._specs[name]
            record = NodeExecutionRecord(
                node=name, status=NodeStatus.RUNNING, started_at=_utc_now()
            )
            state.node_records.append(record)
            state.current_node = name
            self._logger.info(
                "workflow node started",
                extra={"task_id": state.task_id, "node": name},
            )
            try:
                node_input = spec.build_input(state)
                if not isinstance(node_input, spec.input_type):
                    raise TypeError(f"Node input contract violated for {name}")
                output = self._nodes[name].run(node_input)
                if not isinstance(output, spec.output_type):
                    raise TypeError(f"Node output contract violated for {name}")
                spec.apply_output(state, output)
            except Exception as exc:  # convert all node failures into a stable state
                code = getattr(exc, "code", "NODE_EXECUTION_FAILED")
                message = (
                    str(exc)
                    if isinstance(exc, WorkflowNodeError)
                    else "Node execution failed"
                )
                record.status = NodeStatus.FAILED
                record.error_code = code
                record.finished_at = _utc_now()
                state.errors.append(
                    WorkflowError(node=name, code=code, message=message)
                )
                state.status = WorkflowStatus.FAILED
                self._logger.error(
                    "workflow node failed",
                    extra={"task_id": state.task_id, "node": name, "error_code": code},
                )
                self._skip_remaining(state, index + 1)
                break
            else:
                record.status = NodeStatus.SUCCEEDED
                record.finished_at = _utc_now()
                self._logger.info(
                    "workflow node succeeded",
                    extra={"task_id": state.task_id, "node": name},
                )
        if state.status == WorkflowStatus.RUNNING:
            state.status = WorkflowStatus.SUCCEEDED
            state.current_node = None
        return state

    def _skip_remaining(self, state: PresentationWorkflowState, start: int) -> None:
        for name in NODE_ORDER[start:]:
            state.node_records.append(
                NodeExecutionRecord(
                    node=name,
                    status=NodeStatus.SKIPPED,
                    error_code="SKIPPED_DEPENDENCY",
                )
            )
            self._logger.info(
                "workflow node skipped",
                extra={
                    "task_id": state.task_id,
                    "node": name,
                    "error_code": "SKIPPED_DEPENDENCY",
                },
            )


__all__ = [
    "ALLOWED_EDIT_OPERATIONS",
    "ApplyEditsInput",
    "ApplyEditsResult",
    "AnalyzeSlidesInput",
    "AnalyzeStorylineInput",
    "CreateEditPlanInput",
    "EditOperation",
    "EditPlan",
    "EditPlanValidationError",
    "ExportResult",
    "NODE_ORDER",
    "NodeExecutionRecord",
    "NodeNotImplementedError",
    "NodeStatus",
    "ParsePresentationInput",
    "ParseRubricInput",
    "PlaceholderNode",
    "PresentationSummary",
    "PresentationWorkflow",
    "PresentationWorkflowState",
    "QualityCheckExportInput",
    "QualityCheckInput",
    "QualityCheckResult",
    "RubricResult",
    "SlideAnalysis",
    "StorylineAnalysis",
    "UploadRequest",
    "UploadValidationError",
    "ValidateEditPlanNode",
    "ValidateUploadNode",
    "ValidatedEditPlan",
    "ValidatedUpload",
    "ValidateEditPlanInput",
    "WorkflowError",
    "WorkflowDependencyError",
    "WorkflowNode",
    "WorkflowNodeError",
    "WorkflowState",
    "WorkflowStatus",
]

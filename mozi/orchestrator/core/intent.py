"""Intent recognition module for Mozi AI Coding Agent.

This module provides rule-based intent recognition to identify the type and scope
of user tasks from natural language input. It is the first step in the orchestrator's
task routing pipeline.

Examples
--------
Recognize intent from a user message:

    result = recognize_intent("Edit the function in src/main.py")
    print(result.task_type)  # IntentType.CODE_EDIT
    print(result.scope)       # IntentScope.FILE

Recognize intent from a complex task:

    result = recognize_intent(
        "Analyze the entire codebase and create a report"
    )
    print(result.task_type)  # IntentType.ANALYSIS
    print(result.scope)      # IntentScope.PROJECT
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from mozi.core.error import MoziError


class IntentType(Enum):
    """Enumeration of recognized task types.

    Attributes
    ----------
    CODE_EDIT : str
        Task involves modifying or writing code.
    CODE_READ : str
        Task involves reading or searching code.
    BASH : str
        Task involves executing shell commands.
    ANALYSIS : str
        Task involves analyzing or reasoning about code.
    UNKNOWN : str
        Task type could not be determined.
    """

    CODE_EDIT = "CODE_EDIT"
    CODE_READ = "CODE_READ"
    BASH = "BASH"
    ANALYSIS = "ANALYSIS"
    UNKNOWN = "UNKNOWN"


class IntentScope(Enum):
    """Enumeration of recognized task scopes.

    Attributes
    ----------
    FILE : str
        Task targets a single file.
    PROJECT : str
        Task targets an entire project or repository.
    MULTIPLE : str
        Task targets multiple files or projects.
    UNKNOWN : str
        Task scope could not be determined.
    """

    FILE = "FILE"
    PROJECT = "PROJECT"
    MULTIPLE = "MULTIPLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class IntentResult:
    """Result of intent recognition.

    This dataclass holds the recognized task type, scope, and confidence
    score from the intent recognition process.

    Attributes
    ----------
    task_type : IntentType
        The recognized type of task.
    scope : IntentScope
        The recognized scope of the task.
    confidence : float
        Confidence score between 0.0 and 1.0.
    keywords : list[str]
        Keywords that triggered the recognition.
    original_input : str
        The original user input string.

    Examples
    --------
    Create an intent result:

        result = IntentResult(
            task_type=IntentType.CODE_EDIT,
            scope=IntentScope.FILE,
            confidence=0.95,
            keywords=["edit", "file"],
            original_input="edit the main.py file",
        )
    """

    task_type: IntentType
    scope: IntentScope
    confidence: float
    keywords: list[str]
    original_input: str

    def to_dict(self) -> dict[str, Any]:
        """Convert intent result to dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the intent result.
        """
        return {
            "task_type": self.task_type.value,
            "scope": self.scope.value,
            "confidence": self.confidence,
            "keywords": self.keywords,
            "original_input": self.original_input,
        }


class IntentRecognitionError(MoziError):
    """Exception raised when intent recognition fails.

    This exception is raised when the intent recognition process
    encounters an error, such as invalid input or processing failure.

    Examples
    --------
    Raise when input is invalid:

        raise IntentRecognitionError("Input text cannot be empty")
    """

    pass


# Keyword patterns for task type recognition
_CODE_EDIT_KEYWORDS = [
    "edit",
    "modify",
    "change",
    "update",
    "write",
    "add",
    "remove",
    "delete",
    "replace",
    "fix",
    "implement",
    "create",
    "refactor",
    "transform",
]

_CODE_READ_KEYWORDS = [
    "read",
    "show",
    "display",
    "find",
    "search",
    "look",
    "list",
    "get",
    "retrieve",
    "check",
    "view",
    "examine",
    "inspect",
    "cat",
    "type",
]

_BASH_KEYWORDS = [
    "run",
    "execute",
    "command",
    "shell",
    "bash",
    "terminal",
    "console",
    "npm",
    "pip",
    "python",
    "node",
    "make",
    "build",
    "test",
    "compile",
    "deploy",
    "start",
    "stop",
    "restart",
    "install",
    "uninstall",
    "script",
]

_ANALYSIS_KEYWORDS = [
    "analyze",
    "analysis",
    "review",
    "understand",
    "explain",
    "compare",
    "evaluate",
    "assess",
    "report",
    "summary",
    "diagnose",
    "audit",
    "trace",
    "debug",
    "profile",
    "measure",
]


def _identify_scope(text: str) -> tuple[IntentScope, list[str]]:
    """Identify the scope of the task from input text.

    Parameters
    ----------
    text : str
        The input text to analyze.

    Returns
    -------
    tuple[IntentScope, list[str]]
        A tuple of (scope, keywords_found).
    """
    text_lower = text.lower()

    # Check for file path patterns (Unix-style, Windows-style, relative paths)
    # and file extensions (e.g., .py, .js, .ts)
    file_path_patterns = [
        r"/[\w\-./]+",  # Unix-style path
        r"\\[\\w\-.]+",  # Windows-style path
        r"\w:/[\w\-./]+",  # Windows drive path
        r"\.\/[\w\-./]+",  # Relative path
        r"\.\./[\w\-./]+",  # Relative parent path
    ]

    # File extension pattern: matches word followed by dot and extension
    # e.g., "main.py", "file1.py", "config.json"
    file_extension_pattern = r"\b\w+\.\w{1,10}\b"

    # Count actual file paths and extensions
    file_path_count = sum(
        1 for pattern in file_path_patterns if re.search(pattern, text_lower)
    )
    extension_matches = re.findall(file_extension_pattern, text_lower)
    extension_count = len(extension_matches)

    # Check for multiple project/file indicators
    multiple_indicators = [
        r"\b(all|every|each)\b",
        r"\bdirectori(es|ies)\b",
        r"\bmoudle[es]?\b",
        r"\bpackages?\b",
    ]

    # Check for project-level indicators
    project_indicators = [
        r"\bproject\b",
        r"\brepository\b",
        r"\brepo\b",
        r"\bcodebase\b",
        r"\bsource\b",
        r"\bentire\b",
        r"\bwhole\b",
        r"\bworkspace\b",
    ]

    # Check for "files" or "projects" explicitly (not just any word with extension)
    multiple_count = sum(
        1 for pattern in multiple_indicators if re.search(pattern, text_lower)
    )
    project_count = sum(
        1 for pattern in project_indicators if re.search(pattern, text_lower)
    )

    # Determine scope based on counts
    # Priority: MULTIPLE > PROJECT > FILE > UNKNOWN

    # MULTIPLE: multiple file paths/extensions OR explicit multiple indicators
    # with project/codebase indicators
    if (file_path_count >= 2 or extension_count >= 2):
        return IntentScope.MULTIPLE, ["multiple_scope"]

    if (multiple_count >= 1 and (project_count >= 1 or extension_count >= 2)):
        return IntentScope.MULTIPLE, ["multiple_scope"]

    # PROJECT: explicitly mentions project/repository/codebase/etc
    if project_count >= 1:
        return IntentScope.PROJECT, ["project_scope"]

    # FILE: single file path or extension
    if file_path_count >= 1 or extension_count >= 1:
        return IntentScope.FILE, ["file_scope"]

    # Check for generic "file" or "files" word (without extension)
    if re.search(r"\bfiles?\b", text_lower):
        return IntentScope.FILE, ["file_scope"]

    return IntentScope.UNKNOWN, []


def _find_matching_keywords(
    text: str, keyword_lists: dict[str, list[str]]
) -> tuple[str | None, list[str]]:
    """Find matching keywords from input text.

    Uses word boundary matching to ensure keywords match as complete words,
    not as substrings of other words.

    Parameters
    ----------
    text : str
        The input text to search.
    keyword_lists : dict[str, list[str]]
        Dictionary mapping category names to keyword lists.

    Returns
    -------
    tuple[str | None, list[str]]
        A tuple of (matched_category, list_of_matched_keywords).
    """
    text_lower = text.lower()
    best_match: str | None = None
    best_count: int = 0
    all_matches: list[str] = []

    for category, keywords in keyword_lists.items():
        matches = [
            kw for kw in keywords if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text_lower)
        ]
        all_matches.extend(matches)

        if len(matches) > best_count:
            best_count = len(matches)
            best_match = category

    return best_match, all_matches


def recognize_intent(input_text: str) -> IntentResult:
    """Recognize the intent from user input text.

    This function uses a simple rule-based approach with keyword matching
    to identify the task type and scope of the user's request.

    Parameters
    ----------
    input_text : str
        The user's natural language input text.

    Returns
    -------
    IntentResult
        The recognized intent containing task type, scope, and metadata.

    Raises
    ------
    IntentRecognitionError
        If the input text is empty or invalid.

    Examples
    --------
    Basic usage:

        result = recognize_intent("edit the main.py file")
        assert result.task_type == IntentType.CODE_EDIT
        assert result.scope == IntentScope.FILE

    Analysis task:

        result = recognize_intent("analyze the codebase structure")
        assert result.task_type == IntentType.ANALYSIS
    """
    if not input_text or not isinstance(input_text, str):
        raise IntentRecognitionError("Input text must be a non-empty string")

    text = input_text.strip()

    if not text:
        raise IntentRecognitionError("Input text cannot be empty after trimming")

    # Define keyword lists for each task type
    keyword_lists = {
        "CODE_EDIT": _CODE_EDIT_KEYWORDS,
        "CODE_READ": _CODE_READ_KEYWORDS,
        "BASH": _BASH_KEYWORDS,
        "ANALYSIS": _ANALYSIS_KEYWORDS,
    }

    # Find matching keywords
    matched_category, matched_keywords = _find_matching_keywords(text, keyword_lists)

    # Identify scope
    scope, scope_keywords = _identify_scope(text)

    # Determine task type with ANALYSIS priority
    # ANALYSIS keywords are more specific, so if ANALYSIS has any matches,
    # it takes precedence over CODE_EDIT when counts are equal
    analysis_matches = len(
        [
            kw
            for kw in _ANALYSIS_KEYWORDS
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text.lower())
        ]
    )
    code_edit_matches = len(
        [
            kw
            for kw in _CODE_EDIT_KEYWORDS
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text.lower())
        ]
    )

    if (
        analysis_matches > 0
        and matched_category == "CODE_EDIT"
        and code_edit_matches == analysis_matches
    ):
        matched_category = "ANALYSIS"

    # Determine task type
    if matched_category:
        try:
            task_type = IntentType[matched_category]
        except KeyError:
            task_type = IntentType.UNKNOWN
    else:
        task_type = IntentType.UNKNOWN

    # Calculate confidence based on keyword matches
    if matched_keywords:
        confidence = min(len(matched_keywords) / 3.0, 1.0)
    else:
        confidence = 0.0

    # Combine all keywords
    all_keywords = matched_keywords + scope_keywords

    return IntentResult(
        task_type=task_type,
        scope=scope,
        confidence=confidence,
        keywords=all_keywords,
        original_input=input_text,
    )

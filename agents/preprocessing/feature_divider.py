import json
import re
import uuid
from dataclasses import dataclass
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.preprocessing.diff_parser import ParsedDiff, FileDiff
from agents.preprocessing.description_analyzer import AnalyzedDescription
from output.models import FeaturePoint


@dataclass
class FeatureDivisionResult:
    feature_points: list[FeaturePoint]
    file_to_features: dict[str, list[str]]
    summary: str


class FeaturePointDivider:
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a code change analyzer. Given PR description analysis and diff information, 
identify distinct functional/feature points being modified.

A feature point is a logical unit of change that serves a specific purpose. 
Group related file changes together under the same feature point.

Respond in JSON format:
{{
    "feature_points": [
        {{
            "name": "short name for the feature",
            "description": "what this feature point does",
            "files": ["list of files involved"]
        }}
    ],
    "summary": "overall summary of changes"
}}"""),
            ("human", """PR Intent: {intent}
Feature Areas: {feature_areas}
Expected Changes: {expected_changes}

Files Changed:
{files_info}

Identify the distinct feature points in this PR."""),
        ])

    async def divide(
        self,
        parsed_diff: ParsedDiff,
        analyzed_description: AnalyzedDescription,
    ) -> FeatureDivisionResult:
        files_info = self._format_files_info(parsed_diff.files)

        chain = self.prompt | self.llm

        response = await chain.ainvoke({
            "intent": analyzed_description.intent,
            "feature_areas": ", ".join(analyzed_description.feature_areas),
            "expected_changes": ", ".join(analyzed_description.expected_changes),
            "files_info": files_info,
        })

        try:
            content = response.content
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(content)

            feature_points = []
            file_to_features = {}

            for fp_data in result.get("feature_points", []):
                fp_id = str(uuid.uuid4())[:8]
                fp = FeaturePoint(
                    id=fp_id,
                    name=fp_data.get("name", "Unknown"),
                    description=fp_data.get("description", ""),
                    files=fp_data.get("files", []),
                )
                feature_points.append(fp)

                for file in fp.files:
                    if file not in file_to_features:
                        file_to_features[file] = []
                    file_to_features[file].append(fp_id)

            return FeatureDivisionResult(
                feature_points=feature_points,
                file_to_features=file_to_features,
                summary=result.get("summary", ""),
            )

        except json.JSONDecodeError:
            return self._fallback_division(parsed_diff, analyzed_description)

    def _format_files_info(self, files: list[FileDiff]) -> str:
        lines = []
        for f in files:
            lines.append(f"- {f.filename} ({f.status}): +{f.additions}/-{f.deletions}")
            if f.hunks:
                changed_funcs = self._detect_functions_in_diff(f)
                if changed_funcs:
                    lines.append(f"  Functions: {', '.join(changed_funcs)}")
        return "\n".join(lines)

    def _detect_functions_in_diff(self, file_diff: FileDiff) -> list[str]:
        functions = set()
        patterns = [
            r"def\s+(\w+)\s*\(",
            r"class\s+(\w+)",
            r"function\s+(\w+)\s*\(",
            r"const\s+(\w+)\s*=\s*(?:async\s*)?\(",
            r"(\w+)\s*:\s*(?:async\s*)?\(",
        ]

        for hunk in file_diff.hunks:
            for _, line in hunk.added_lines:
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        functions.add(match.group(1))

        return list(functions)

    def _fallback_division(
        self,
        parsed_diff: ParsedDiff,
        analyzed_description: AnalyzedDescription,
    ) -> FeatureDivisionResult:
        file_groups = {}
        for file in parsed_diff.files:
            directory = file.filename.rsplit("/", 1)[0] if "/" in file.filename else "root"
            if directory not in file_groups:
                file_groups[directory] = []
            file_groups[directory].append(file.filename)

        feature_points = []
        file_to_features = {}

        for directory, files in file_groups.items():
            fp_id = str(uuid.uuid4())[:8]
            fp = FeaturePoint(
                id=fp_id,
                name=f"Changes in {directory}",
                description=f"Modifications to files in {directory}",
                files=files,
            )
            feature_points.append(fp)

            for file in files:
                if file not in file_to_features:
                    file_to_features[file] = []
                file_to_features[file].append(fp_id)

        return FeatureDivisionResult(
            feature_points=feature_points,
            file_to_features=file_to_features,
            summary=analyzed_description.intent,
        )

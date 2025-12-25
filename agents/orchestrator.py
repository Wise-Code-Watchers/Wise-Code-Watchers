import asyncio
import logging
import json
import os
from typing import Optional, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from config import Config
from agents.preprocessing.diff_parser import DiffParser
from agents.preprocessing.description_analyzer import DescriptionAnalyzer
from agents.preprocessing.feature_divider import FeaturePointDivider
from agents.syntax.structure_agent import SyntaxStructureAgent
from agents.syntax.memory_agent import MemoryAnalysisAgent
from agents.vulnerability.logic_agent import LogicAnalysisAgent
from agents.vulnerability.security_agent import SecurityAnalysisAgent
from agents.aggregator import ResultAggregator
from output.models import AnalysisReport

logger = logging.getLogger(__name__)


def _build_diff_ir_from_parsed(parsed_diff) -> dict:
    """Convert parsed_diff to diff_ir format for enhanced agents."""
    files = []
    for file_diff in parsed_diff.files:
        hunks = []
        for hunk in file_diff.hunks:
            lines = []
            for line_no, content in hunk.added_lines:
                lines.append({
                    "type": "add",
                    "content": content,
                    "old_lineno": None,
                    "new_lineno": line_no,
                })
            for line_no, content in hunk.removed_lines:
                lines.append({
                    "type": "del",
                    "content": content,
                    "old_lineno": line_no,
                    "new_lineno": None,
                })

            hunks.append({
                "old_start": hunk.old_start,
                "old_count": hunk.old_count,
                "new_start": hunk.new_start,
                "new_count": hunk.new_count,
                "header": hunk.header if hasattr(hunk, "header") else "",
                "lines": lines,
            })

        files.append({
            "file_path": file_diff.filename,
            "language": _detect_language(file_diff.filename),
            "change_type": file_diff.status,
            "is_binary": False,
            "hunks": hunks,
        })

    return {
        "files": files,
        "summary": {
            "files": parsed_diff.total_files,
            "total_additions": parsed_diff.total_additions,
            "total_deletions": parsed_diff.total_deletions,
        },
    }


def _detect_language(filename: str) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".rb": "ruby",
        ".php": "php",
    }
    for ext, lang in ext_map.items():
        if filename.endswith(ext):
            return lang
    return "unknown"


def _build_simple_risk_plan(parsed_diff, feature_points) -> dict:
    """Build a simple feature risk plan from parsed diff and feature points."""
    features = []

    for i, fp in enumerate(feature_points):
        hunks = []
        for file_diff in parsed_diff.files:
            if file_diff.filename in fp.files:
                for h_idx, hunk in enumerate(file_diff.hunks):
                    hunks.append({
                        "hunk_id": f"{i}:{h_idx}",
                        "file_path": file_diff.filename,
                        "risk_score": 50,
                        "severity": "medium",
                        "suggested_agents": ["logic_agent", "security_agent"],
                    })

        features.append({
            "feature_id": fp.id,
            "feature_name": fp.name,
            "summary": fp.description,
            "hunks": hunks,
            "risk_overview": {
                "max_risk_score": 50,
            },
        })

    return {
        "features": features,
        "top_focus": [],
        "summary": {
            "total_hunks": sum(len(f["hunks"]) for f in features),
        },
    }


def create_llm() -> BaseChatModel:
    """Create LLM instance using Anthropic (via ZhipuAI compatible endpoint)"""
    kwargs = {
        "model": Config.LLM_MODEL,
        "temperature": 0,
    }
    if Config.LLM_API_KEY:
        kwargs["api_key"] = Config.LLM_API_KEY
    if Config.LLM_BASE_URL:
        kwargs["base_url"] = Config.LLM_BASE_URL
    
    # Use ChatAnthropic with ZhipuAI's Anthropic-compatible endpoint
    return ChatAnthropic(**kwargs)


class ReviewOrchestrator:
    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        verbose: bool = False,
    ):
        self.llm = llm or create_llm()
        self.verbose = verbose

        self.diff_parser = DiffParser()
        self.description_analyzer = DescriptionAnalyzer(llm=self.llm)
        self.feature_divider = FeaturePointDivider(llm=self.llm)

        self.structure_agent = SyntaxStructureAgent(llm=self.llm, verbose=verbose)
        self.memory_agent = MemoryAnalysisAgent(llm=self.llm, verbose=verbose)
        self.logic_agent = LogicAnalysisAgent(llm=self.llm, verbose=verbose)
        self.security_agent = SecurityAnalysisAgent(llm=self.llm, verbose=verbose)

        # Aggregator with LLM scoring filter
        self.aggregator = ResultAggregator(
            llm=self.llm,
            relevance_threshold=0.5,
            severity_threshold=0.4,
        )

    async def run_review(
        self,
        pr_folder: str,
        codebase_path: str,
        pr_number: int,
        repo_full_name: str,
    ) -> AnalysisReport:
        logger.info(f"Starting review for PR #{pr_number} in {repo_full_name}")

        logger.info("Phase 1: Parsing diff and PR description")
        parsed_diff = self.diff_parser.parse_pr_folder(pr_folder)
        logger.info(f"Parsed {parsed_diff.total_files} files with {parsed_diff.total_additions} additions")

        pr_description = self.description_analyzer.load_from_pr_folder(pr_folder)
        analyzed_description = await self.description_analyzer.analyze(pr_description)
        logger.info(f"PR intent: {analyzed_description.intent[:100]}...")

        logger.info("Phase 2: Dividing into feature points")
        division_result = await self.feature_divider.divide(parsed_diff, analyzed_description)
        feature_points = division_result.feature_points
        logger.info(f"Identified {len(feature_points)} feature points")

        changed_files = [f.filename for f in parsed_diff.files]

        logger.info("Phase 3: Running parallel agent analysis")
        logger.info(f"Scoping analysis to {len(changed_files)} changed files")

        diff_ir = _build_diff_ir_from_parsed(parsed_diff)
        feature_risk_plan = _build_simple_risk_plan(parsed_diff, feature_points)
        logger.info(f"Built diff_ir with {len(diff_ir.get('files', []))} files")
        logger.info(f"Built feature_risk_plan with {len(feature_risk_plan.get('features', []))} features")

        structure_task = self.structure_agent.analyze(
            codebase_path=codebase_path,
            changed_files=changed_files,
        )
        memory_task = self.memory_agent.analyze(
            codebase_path=codebase_path,
            changed_files=changed_files,
        )
        logic_task = self.logic_agent.analyze(
            codebase_path=codebase_path,
            feature_points=feature_points,
            changed_files=changed_files,
            diff_ir=diff_ir,
            feature_risk_plan=feature_risk_plan,
            pr_dir=pr_folder,
        )
        security_task = self.security_agent.analyze(
            codebase_path=codebase_path,
            feature_points=feature_points,
            changed_files=changed_files,
            diff_ir=diff_ir,
            feature_risk_plan=feature_risk_plan,
            pr_dir=pr_folder,
        )

        results = await asyncio.gather(
            structure_task,
            memory_task,
            logic_task,
            security_task,
            return_exceptions=True,
        )

        structure_result, memory_result, logic_result, security_result = results

        for name, result in [
            ("structure", structure_result),
            ("memory", memory_result),
            ("logic", logic_result),
            ("security", security_result),
        ]:
            if isinstance(result, Exception):
                logger.error(f"{name} agent failed: {result}")
            elif result.success:
                logger.info(f"{name} agent found {len(result.issues)} issues")
            else:
                logger.warning(f"{name} agent failed: {result.error}")

        pr_metadata = self._load_pr_metadata(pr_folder)

        logger.info("Phase 4: Aggregating results with LLM scoring filter")
        report = await self.aggregator.aggregate(
            pr_number=pr_number,
            repo_full_name=repo_full_name,
            feature_points=feature_points,
            structure_result=structure_result if not isinstance(structure_result, Exception) else self._error_result("structure", structure_result),
            memory_result=memory_result if not isinstance(memory_result, Exception) else self._error_result("memory", memory_result),
            logic_result=logic_result if not isinstance(logic_result, Exception) else self._error_result("logic", logic_result),
            security_result=security_result if not isinstance(security_result, Exception) else self._error_result("security", security_result),
            pr_metadata=pr_metadata,
            parsed_diff=parsed_diff,
        )

        logger.info(f"Review complete. Found {report.bug_detection.total_count} total issues")

        return report

    def _load_pr_metadata(self, pr_folder: str) -> Optional[dict]:
        metadata_path = os.path.join(pr_folder, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                return json.load(f)
        return None

    def _error_result(self, agent_name: str, error: Exception):
        from agents.base import AgentResult
        return AgentResult(
            agent_name=agent_name,
            success=False,
            error=str(error),
        )


async def run_review_pipeline(
    pr_folder: str,
    codebase_path: str,
    pr_number: int,
    repo_full_name: str,
    llm: Optional[BaseChatModel] = None,
) -> AnalysisReport:
    orchestrator = ReviewOrchestrator(llm=llm)
    return await orchestrator.run_review(
        pr_folder=pr_folder,
        codebase_path=codebase_path,
        pr_number=pr_number,
        repo_full_name=repo_full_name,
    )

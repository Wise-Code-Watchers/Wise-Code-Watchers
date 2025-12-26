import json
import os
import re
from dataclasses import dataclass
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


@dataclass
class PRDescription:
    title: str
    body: str
    labels: list[str]
    author: str
    base_branch: str
    head_branch: str


@dataclass
class AnalyzedDescription:
    intent: str
    feature_areas: list[str]
    expected_changes: list[str]
    risk_indicators: list[str]
    keywords: list[str]


class DescriptionAnalyzer:
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a PR description analyzer. Analyze the given PR information and extract:
1. The main intent/purpose of the PR
2. Feature areas being modified (e.g., authentication, database, UI)
3. Expected types of changes (e.g., bug fix, new feature, refactoring)
4. Any risk indicators mentioned (e.g., breaking changes, security implications)
5. Key technical keywords

Respond in JSON format with keys: intent, feature_areas, expected_changes, risk_indicators, keywords"""),
            ("human", """PR Title: {title}

PR Description:
{body}

Labels: {labels}
Author: {author}
Base Branch: {base_branch}
Head Branch: {head_branch}

Analyze this PR and provide structured information."""),
        ])

    def load_from_pr_folder(self, pr_folder: str) -> PRDescription:
        metadata_path = os.path.join(pr_folder, "metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"metadata.json not found in {pr_folder}")

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        return PRDescription(
            title=metadata.get("title", ""),
            body=metadata.get("body", "") or "",
            labels=metadata.get("labels", []),
            author=metadata.get("author", ""),
            base_branch=metadata.get("base_branch", ""),
            head_branch=metadata.get("head_branch", ""),
        )

    async def analyze(self, pr_description: PRDescription) -> AnalyzedDescription:
        chain = self.prompt | self.llm

        response = await chain.ainvoke({
            "title": pr_description.title,
            "body": pr_description.body,
            "labels": ", ".join(pr_description.labels) if pr_description.labels else "None",
            "author": pr_description.author,
            "base_branch": pr_description.base_branch,
            "head_branch": pr_description.head_branch,
        })

        try:
            content = response.content
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(content)

            return AnalyzedDescription(
                intent=result.get("intent", ""),
                feature_areas=result.get("feature_areas", []),
                expected_changes=result.get("expected_changes", []),
                risk_indicators=result.get("risk_indicators", []),
                keywords=result.get("keywords", []),
            )
        except json.JSONDecodeError:
            return self._fallback_analysis(pr_description)

    def _fallback_analysis(self, pr_description: PRDescription) -> AnalyzedDescription:
        keywords = self._extract_keywords(pr_description.title + " " + pr_description.body)

        feature_areas = []
        change_types = []
        risk_indicators = []

        feature_keywords = {
            "auth": "authentication",
            "login": "authentication",
            "database": "database",
            "db": "database",
            "api": "api",
            "ui": "user interface",
            "frontend": "frontend",
            "backend": "backend",
            "test": "testing",
        }

        change_keywords = {
            "fix": "bug fix",
            "bug": "bug fix",
            "feature": "new feature",
            "add": "new feature",
            "refactor": "refactoring",
            "update": "update",
            "remove": "removal",
            "delete": "removal",
        }

        risk_keywords = ["breaking", "security", "critical", "urgent", "hotfix"]

        text_lower = (pr_description.title + " " + pr_description.body).lower()

        for keyword, area in feature_keywords.items():
            if keyword in text_lower and area not in feature_areas:
                feature_areas.append(area)

        for keyword, change in change_keywords.items():
            if keyword in text_lower and change not in change_types:
                change_types.append(change)

        for keyword in risk_keywords:
            if keyword in text_lower:
                risk_indicators.append(keyword)

        return AnalyzedDescription(
            intent=pr_description.title,
            feature_areas=feature_areas,
            expected_changes=change_types,
            risk_indicators=risk_indicators,
            keywords=keywords,
        )

    def _extract_keywords(self, text: str) -> list[str]:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        stopwords = {"the", "and", "for", "are", "this", "that", "with", "from", "have", "has"}
        keywords = [w for w in words if w not in stopwords]
        return list(set(keywords))[:20]

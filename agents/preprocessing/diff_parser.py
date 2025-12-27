import re
import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    content: str
    added_lines: list[tuple[int, str]] = field(default_factory=list)
    removed_lines: list[tuple[int, str]] = field(default_factory=list)


@dataclass
class FileDiff:
    filename: str
    status: str  # added, modified, deleted, renamed
    additions: int
    deletions: int
    hunks: list[DiffHunk] = field(default_factory=list)
    old_filename: Optional[str] = None


@dataclass
class ParsedDiff:
    files: list[FileDiff]
    total_additions: int
    total_deletions: int
    total_files: int


class DiffParser:
    HUNK_HEADER_PATTERN = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    def parse_pr_folder(self, pr_folder: str) -> ParsedDiff:
        files = []
        total_additions = 0
        total_deletions = 0

        files_changed_path = os.path.join(pr_folder, "files_changed.json")
        if os.path.exists(files_changed_path):
            with open(files_changed_path, "r") as f:
                files_changed = json.load(f)

            for file_info in files_changed:
                total_additions += file_info.get("additions", 0)
                total_deletions += file_info.get("deletions", 0)

        diff_path = os.path.join(pr_folder, "pr.diff")
        if os.path.exists(diff_path):
            with open(diff_path, "r") as f:
                diff_content = f.read()
            files = self.parse_unified_diff(diff_content)

        return ParsedDiff(
            files=files,
            total_additions=total_additions,
            total_deletions=total_deletions,
            total_files=len(files),
        )

    def parse_unified_diff(self, diff_text: str) -> list[FileDiff]:
        files = []
        current_file = None
        current_hunk = None
        new_line_num = 0

        lines = diff_text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            if line.startswith("diff --git"):
                if current_file:
                    if current_hunk:
                        current_file.hunks.append(current_hunk)
                    files.append(current_file)

                match = re.search(r"diff --git a/(.+) b/(.+)", line)
                if match:
                    filename = match.group(2)
                    current_file = FileDiff(
                        filename=filename,
                        status="modified",
                        additions=0,
                        deletions=0,
                    )
                current_hunk = None

            elif line.startswith("--- "):
                if current_file and line == "--- /dev/null":
                    current_file.status = "added"

            elif line.startswith("+++ "):
                if current_file and line == "+++ /dev/null":
                    current_file.status = "deleted"

            elif line.startswith("@@"):
                if current_file and current_hunk:
                    current_file.hunks.append(current_hunk)

                match = self.HUNK_HEADER_PATTERN.match(line)
                if match:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2)) if match.group(2) else 1
                    new_start = int(match.group(3))
                    new_count = int(match.group(4)) if match.group(4) else 1

                    current_hunk = DiffHunk(
                        old_start=old_start,
                        old_count=old_count,
                        new_start=new_start,
                        new_count=new_count,
                        content=line,
                    )
                    new_line_num = new_start

            elif current_hunk is not None:
                if line.startswith("+") and not line.startswith("+++"):
                    current_hunk.added_lines.append((new_line_num, line[1:]))
                    current_hunk.content += "\n" + line
                    if current_file:
                        current_file.additions += 1
                    new_line_num += 1
                elif line.startswith("-") and not line.startswith("---"):
                    current_hunk.removed_lines.append((new_line_num, line[1:]))
                    current_hunk.content += "\n" + line
                    if current_file:
                        current_file.deletions += 1
                else:
                    current_hunk.content += "\n" + line
                    if not line.startswith("\\"):
                        new_line_num += 1

            i += 1

        if current_file:
            if current_hunk:
                current_file.hunks.append(current_hunk)
            files.append(current_file)

        return files

    def get_changed_functions(self, file_diff: FileDiff) -> list[str]:
        functions = []
        func_pattern = re.compile(r"^[+-]\s*(def|class|function|async\s+def|async\s+function)\s+(\w+)")

        for hunk in file_diff.hunks:
            for _, line in hunk.added_lines + hunk.removed_lines:
                match = func_pattern.match("+" + line)
                if match:
                    functions.append(match.group(2))

        return list(set(functions))

# Multi-Agent PR Review System Architecture

## Flowchart

```mermaid
flowchart TB
    subgraph Input["1. Input Layer"]
        PR[PR Event] --> GH[GitHub App Webhook]
    end

    subgraph Export["2. PR Export"]
        EXP[PR Exporter] --> PRF[PR Folder]
    end

    subgraph Codebase["3. Codebase Preparation"]
        PULL[Pull Target Branch] --> CB[Codebase Folder]
    end

    subgraph Agents["4. LangChain Multi-Agent System"]
        direction TB
        
        subgraph FPM["Feature Point Division Module"]
            direction LR
            DIFF[Diff Parser] --> FPD[Feature Point Divider]
            DESC[PR Description Analyzer] --> FPD
            FPD --> FP[Feature Points]
        end
        
        subgraph AnalysisAgents["Analysis Agents"]
            direction LR
            subgraph SyntaxBranch["Syntax Branch"]
                direction TB
                SSA[Syntax Structure Agent]
                SPA[Memory Analysis Agent]
            end
            
            subgraph VulnBranch["Vulnerability Branch"]
                direction TB
                LA[Logic Analysis Agent]
                SA[Security Analysis Agent]
            end
        end
        
        subgraph Resources["Knowledge Bases & Tools"]
            direction LR
            subgraph KBs["Knowledge Bases"]
                KB1[Code Patterns KB]
                KB2[Vulnerability KB]
                KB3[Best Practices KB]
            end
            
            subgraph Tools["External Tools"]
                ET1[Static Analyzer]
                ET2[Linter]
                ET3[Security Scanner]
            end
        end
        
        AGG[Result Aggregator]
    end

    subgraph Output["5. Output Layer"]
        direction LR
        R1[PR Summary] --> REP[Analysis Report]
        R2[Bug Detection] --> REP
        R3[Line Comments] --> REP
    end

    subgraph Publish["6. Publish"]
        GHC[GitHub Client] --> CMT[Post PR Comment]
    end

    %% Main Flow
    GH --> EXP
    PRF --> PULL
    
    %% To Feature Point Division
    PRF --> DIFF
    PRF --> DESC
    CB --> FPM
    
    %% Feature Points to Vulnerability Branch
    FP --> LA
    FP --> SA
    
    %% Codebase to Syntax Branch
    CB --> SSA
    CB --> SPA
    
    %% Knowledge & Tools to Agents
    KB1 --> SSA
    KB3 --> SPA
    ET2 --> SSA
    ET2 --> SPA
    
    KB2 --> LA
    KB2 --> SA
    KB3 --> LA
    ET1 --> LA
    ET3 --> SA
    
    %% Agents to Aggregator
    SSA --> AGG
    SPA --> AGG
    LA --> AGG
    SA --> AGG
    
    %% Output Flow
    AGG --> R1
    AGG --> R2
    AGG --> R3
    REP --> GHC
```

## Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant GH as GitHub
    participant App as GitHub App
    participant Exp as PR Exporter
    participant Git as Git Client
    participant FPD as Feature Point Divider
    participant SSA as Syntax Structure Agent
    participant SPA as Memory Analysis Agent
    participant LA as Logic Analysis Agent
    participant SA as Security Analysis Agent
    participant KB as Knowledge Bases
    participant ET as External Tools
    participant AGG as Result Aggregator
    participant GHC as GitHub Client

    Note over GH,GHC: 1. PR Export Phase
    GH->>App: PR Webhook Event
    App->>Exp: Trigger Export
    Exp->>GH: Fetch PR Data
    GH-->>Exp: PR Metadata + Diff
    Exp->>Exp: Save to PR Folder

    Note over GH,GHC: 2. Codebase Preparation Phase
    Exp->>Git: Clone/Pull Target Branch
    Git->>Git: Checkout to Local Folder
    Git-->>Exp: Codebase Ready

    Note over GH,GHC: 3. Feature Point Division Phase
    Exp->>FPD: PR Folder (diff + description)
    FPD->>FPD: Parse Diff Changes
    FPD->>FPD: Analyze PR Description
    FPD->>FPD: Identify Modified Feature Points

    Note over GH,GHC: 4. Parallel Agent Analysis Phase
    par Syntax Structure Agent
        Exp->>SSA: Codebase
        SSA->>KB: Query Code Patterns KB
        KB-->>SSA: Pattern References
        SSA->>ET: Run Linter
        ET-->>SSA: Lint Results
        SSA->>SSA: Analyze Code Structure
        SSA-->>AGG: Structure Analysis Result
    and Memory Analysis Agent
        Exp->>SPA: Codebase
        SPA->>KB: Query Best Practices KB
        KB-->>SPA: Best Practices
        SPA->>ET: Run Linter
        ET-->>SPA: Style Results
        SPA->>SPA: Analyze Memory & Context
        SPA-->>AGG: Memory Analysis Result
    and Logic Analysis Agent
        FPD->>LA: Feature Points
        LA->>KB: Query Vulnerability KB
        KB-->>LA: Known Issues
        LA->>KB: Query Best Practices KB
        KB-->>LA: Best Practices
        LA->>ET: Run Static Analyzer
        ET-->>LA: Static Analysis Result
        LA->>LA: Analyze Logic per Feature Point
        LA-->>AGG: Logic Analysis Result
    and Security Analysis Agent
        FPD->>SA: Feature Points
        SA->>KB: Query Vulnerability KB
        KB-->>SA: Security Vulnerabilities
        SA->>ET: Run Security Scanner
        ET-->>SA: Security Scan Result
        SA->>SA: Analyze Security per Feature Point
        SA-->>AGG: Security Analysis Result
    end

    Note over GH,GHC: 5. Report Generation Phase
    AGG->>AGG: Merge All Analysis Results
    AGG->>AGG: Generate PR Summary
    AGG->>AGG: Compile Bug Detection Report
    AGG->>AGG: Create Line-Level Comments

    Note over GH,GHC: 6. Publish Phase
    AGG->>GHC: Submit Analysis Report
    GHC->>GH: POST /repos/{owner}/{repo}/pulls/{pr}/reviews
    GH-->>GHC: Review Created
    GHC-->>AGG: Success

    Note over GH,GHC: Complete
```

## Agent Responsibilities

| Component | Role | Input | Output |
|-----------|------|-------|--------|
| **Feature Point Divider** | Identifies modified functional points from PR | Diff files, PR description | Feature Points List |
| **Syntax Structure Agent** | Analyzes code structure, AST, and syntax correctness | Codebase, Code Patterns KB, Linter | Structure Analysis Result |
| **Memory Analysis Agent** | Analyzes code context, variable lifecycle, and memory patterns | Codebase, Best Practices KB, Linter | Memory Analysis Result |
| **Logic Analysis Agent** | Detects logic errors, edge cases, and algorithmic bugs | Feature Points, Vulnerability KB, Static Analyzer | Logic Analysis Result |
| **Security Analysis Agent** | Identifies security vulnerabilities and unsafe code | Feature Points, Vulnerability KB, Security Scanner | Security Analysis Result |
| **Result Aggregator** | Merges all agent outputs and generates final report | All 4 agent outputs | Final Analysis Report |

## Knowledge Bases & External Tools

| Type | Name | Purpose |
|------|------|---------|
| **Knowledge Base** | Code Patterns KB | Common coding patterns and anti-patterns |
| **Knowledge Base** | Vulnerability KB | Known vulnerabilities, CVEs, security issues |
| **Knowledge Base** | Best Practices KB | Language/framework best practices |
| **External Tool** | Static Analyzer | Deep code analysis (e.g., Semgrep, CodeQL) |
| **External Tool** | Linter | Syntax and style checking (e.g., ESLint, Pylint) |
| **External Tool** | Security Scanner | Security vulnerability scanning (e.g., Snyk, Bandit) |

## Report Structure

```json
{
  "pr_summary": {
    "title": "string",
    "description": "string",
    "files_changed": ["list"],
    "summary": "AI-generated summary"
  },
  "bug_detection": {
    "has_bugs": "boolean",
    "bugs": [
      {
        "severity": "high|medium|low",
        "type": "string",
        "description": "string",
        "file": "string",
        "line": "number"
      }
    ]
  },
  "line_comments": [
    {
      "path": "string",
      "line": "number",
      "body": "string",
      "side": "RIGHT"
    }
  ]
}
```

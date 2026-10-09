---
name: sonar-code-audit
description: "Check SonarLint, SonarQube, or SonarCloud diagnostics and quality findings using accessible editor diagnostics, local reports, scanner output, or repository configuration. Use when the user asks to inspect Sonar issues or an editor Problems panel; do not claim access to a live panel without a connector or supplied diagnostics."
metadata:
  short-description: "Check Sonar diagnostics and quality findings"
---

# Sonar Code Audit

Audit Sonar findings and configuration without changing code by default. This skill complements `$codebase-audit` and `$strict-code-quality`; it does not replace language-specific type checks or linters.

## Access boundary

1. Determine which evidence is actually available:
   - live editor diagnostics, only when a supported editor or app connector exposes them;
   - pasted or exported Problems-panel diagnostics;
   - local Sonar reports, scanner logs, `report-task.txt`, or `.scannerwork` metadata;
   - repository configuration such as `sonar-project.properties`, `.sonarcloud.properties`, CI scripts, and quality-gate settings.
2. If the live editor panel is not accessible, say so plainly. Do not invent findings or imply that the installed SonarLint extension was inspected. Ask the user to paste/export the diagnostics or authorize an appropriate local/remote scan.
3. Treat SonarLint editor findings and SonarQube/SonarCloud server findings as potentially different because rules, branches, connected mode, exclusions, and analyzer versions can differ.

## Safe workflow

- Inspect existing Sonar configuration, source/test exclusions, coverage paths, quality-gate references, and documented commands before running anything.
- Use check-only or report-reading commands when available. Do not run formatter, autofix, dependency upgrade, migration, or code-modification commands.
- Do not run a scanner that uploads analysis to SonarQube/SonarCloud unless the user explicitly asks for that scan. A scanner upload is an external side effect, even when the local code is unchanged.
- Never print, copy, or expose `SONAR_TOKEN`, API tokens, passwords, or other credentials. Use existing environment configuration only when the requested operation is authorized.
- Preserve scope: do not fix findings, alter `NOSONAR`/suppression settings, change exclusions, or modify quality gates unless explicitly requested.

## Normalize findings

For every accessible issue, capture:

- rule key and analyzer type;
- severity and status (`OPEN`, `CONFIRMED`, `RESOLVED`, `FALSE-POSITIVE`, or equivalent);
- file path and line or symbol;
- message and concise evidence;
- whether it is new code, legacy code, a vulnerability, a bug, a code smell, or a security hotspot;
- confidence and any dependency on Sonar configuration or branch context.

Deduplicate identical rule/location/message combinations. Preserve the original Sonar severity; if adding a prioritization, explain the reason rather than silently remapping it.

## Review dimensions

- Correctness: bugs, error handling, nullability, resource management, concurrency, and boundary behavior.
- Security: injection, authorization, secrets, unsafe deserialization, path/file handling, sensitive logging, and hotspots. Do not call something a vulnerability from a naming pattern alone; trace reachability and impact.
- Maintainability: duplication, complexity, dead code, magic literals, unclear ownership, and excessive suppression.
- Strictness: casts or assertions used to hide uncertainty, weak typing, missing type checks, and disagreement between Sonar rules and repository compiler/linter policy.
- Configuration: source/test classification, generated-code exclusions, coverage report paths, branch scope, analyzer/plugin availability, and quality-gate enforcement.

## Report format

Return:

1. **Evidence source:** editor panel, supplied export, local report, scanner output, or configuration-only review; include what was unavailable.
2. **Quality-gate status:** pass/fail/unknown, with the exact source.
3. **Finding summary:** counts by severity, type, status, and new-versus-legacy scope when available.
4. **Prioritized findings:** rule, severity, location, message, impact, confidence, and recommended next action.
5. **Configuration gaps:** missing or inconsistent scans, exclusions, coverage, or branch analysis.
6. **Next steps:** smallest safe remediation sequence. Keep it advisory unless the user explicitly requests fixes.

When the user supplies only a screenshot or copied panel text, preserve uncertainty for truncated paths, missing line numbers, and omitted rule metadata.

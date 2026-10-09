---
name: codebase-audit
description: "Perform an evidence-based, read-only audit of a codebase or workspace for correctness, strict typing, linting, code smells, architecture, tests, contracts, dependencies, and security. Use when the user asks to audit, assess, inspect, or review code broadly."
metadata:
  short-description: "Audit code quality, architecture, tests, and security"
---

# Codebase Audit

Produce a prioritized audit report by default. Do not modify source code, configuration, dependencies, generated artifacts, or documentation unless the user explicitly asks for remediation in the same request.

## Audit workflow

1. Establish scope: repository or workspace root, packages/apps, changed files or branch diff if provided, supported runtimes, and critical paths.
2. Map the codebase before judging it: entry points, package boundaries, dependency direction, public APIs, persistence and integration boundaries, compiler/type settings, lint/format settings, test configuration, CI checks, and security-sensitive areas.
3. Read repository guidance and use existing check commands in non-mutating/check-only modes. Prefer `rg` and targeted file inspection. Do not run formatters or automated fix commands that write files.
4. Inspect implementation and tests together. Trace important flows from input to validation, domain logic, side effects, persistence, external calls, and user-visible output.
5. Report only actionable findings supported by concrete evidence. Separate confirmed findings from hypotheses and record important areas that could not be verified.

## Audit dimensions

### Correctness and maintainability

- Look for broken invariants, incorrect branching, boundary-condition failures, error swallowing, race or ordering assumptions, resource leaks, unsafe retries, and regressions in changed code.
- Identify dead code, duplicated knowledge, magic values, long or deeply nested functions, unclear names, primitive obsession, god objects, feature envy, hidden mutable state, and leaky abstractions.
- Apply DRY to duplicated knowledge rather than superficial similarity. Prefer a small cohesive change over speculative abstraction.

### Type and lint strictness

- Check whether compiler/type-checker strictness is enabled and consistently enforced for production code. Flag new `any`, weak escape hatches, non-null assertions, unvalidated dynamic values, and unjustified suppression comments.
- Treat casts or type assertions as findings when they hide uncertainty. Recommend narrowing, type guards, discriminated unions, generics, overloads, or boundary validation first; accept a narrow cast only when its invariant is demonstrated.
- Check exhaustiveness for closed sets and whether invalid states are representable.
- Check repeated domain/status/event/route/key strings and magic numbers. Recommend named constants, enums, or language-appropriate typed values for stable closed sets, but do not force enums for free-form text, external values, URLs, regexes, SQL, or user-facing content.
- Do not treat a formatter preference as a defect unless it violates the repository's stated policy or hides a material problem.

### Design and architecture

- Evaluate cohesion, coupling, dependency direction, interface ownership, policy-versus-infrastructure separation, and testability.
- Apply SOLID pragmatically: single cohesive responsibility, consumer-focused interfaces, substitutable implementations, and dependency inversion at real boundaries.
- Recommend a design pattern only when a concrete recurring design pressure justifies its complexity; call out simpler alternatives.
- For monorepos, assess package boundaries, ownership, dependency constraints, shared tooling, build/test caching, CI cost, versioning, and release strategy. Do not recommend monorepo complexity merely as a preference.

### Tests and delivery safety

- Check coverage of normal, boundary, failure, authorization, persistence, integration, and compatibility behavior appropriate to the code.
- Flag tests that are nondeterministic, overly coupled to implementation details, over-mocked, missing assertions, or absent for high-risk paths.
- Inspect CI gates and determine whether type checks, linting, tests, migrations, API contract checks, security checks, and generated-code drift are enforced where relevant.

### Security, data, and contracts

- Inspect authentication and authorization boundaries, input validation, injection risks, secret handling, sensitive logging, unsafe deserialization, path/file operations, dependency risk, and error exposure.
- Check API request/response compatibility, versioning, schema validation, migration safety, rollback behavior, idempotency, and external-service failure handling.
- Do not claim a vulnerability solely from a naming pattern. Explain the reachable data flow and identify what evidence is still needed.

## Finding standard

Prioritize findings by impact and likelihood:

- **Critical:** likely severe security, data-loss, integrity, or production failure risk.
- **High:** material correctness, security, reliability, or compatibility risk on an important path.
- **Medium:** meaningful maintainability, test, architectural, or boundary risk with plausible impact.
- **Low:** localized improvement with limited immediate risk.

Every finding must include:

- stable ID and severity;
- category;
- exact file path and line or symbol when available;
- concise evidence and why it matters;
- recommended remediation;
- confidence level and any assumptions.

Do not inflate severity for style disagreement. If a concern is subjective, label it as a recommendation rather than a defect.

## Report format

Return:

1. **Scope and checks:** roots, packages, files, diff or baseline, commands run, and commands not run.
2. **Executive summary:** overall risk, strongest positive evidence, and the most important next action.
3. **Prioritized findings:** Critical/High/Medium/Low, with evidence-backed locations.
4. **Coverage gaps:** inaccessible files, untested paths, missing tooling, generated code, or unresolved assumptions.
5. **Remediation sequence:** smallest safe fixes first, then structural work, with validation gates and rollback considerations.

Keep the audit read-only unless the user explicitly changes the request to remediation. When remediation is requested, preserve strictness, avoid broad suppressions, run relevant checks, and report any remaining exceptions.

---
name: strict-code-quality
description: "Apply strict, maintainable coding standards during implementation, refactoring, and review: strict types, linting, code-smell detection, minimal casts, DRY/SOLID, justified design patterns, named constants or enums, and monorepo architecture when warranted."
metadata:
  short-description: "Enforce strict, maintainable code quality"
---

# Strict Code Quality

Use this skill for code changes, refactors, architecture decisions, and reviews when the user wants production-quality code. Apply it in a language-aware way and follow repository conventions where they are stricter or more specific.

## Workflow

1. Inspect the repository before changing code: language and runtime, compiler settings, package/workspace layout, formatter, linter, test commands, and CI checks.
2. Preserve or strengthen strictness. Never weaken compiler, type-checker, linter, test, or CI settings merely to make a change pass.
3. Make the smallest coherent change that improves the design. Avoid unrelated rewrites and speculative abstractions.
4. Validate with the repository's formatter, linter, type checker/compiler, and relevant tests. If a check cannot run, say why and identify the exact remaining risk.

## Scope discipline

- Treat the user's request as the change boundary. Define the in-scope behavior and files before editing, then keep the diff focused on that boundary.
- Do not make drive-by changes: no unrelated cleanup, opportunistic refactors, broad formatting, import rearrangement, dependency upgrades, public renames, framework migrations, documentation edits, or generated-file refreshes unless requested or strictly required for the requested change.
- If a related issue is discovered outside the requested scope, report it separately with its location and impact; do not fix it in the same change.
- If a collateral file must change for correctness (for example, a required lockfile or generated client), change only the required artifact and explain why.
- Do not “clean as you go.” In review or audit mode, do not modify files. Before completion, inspect the diff and call out any pre-existing changes without rewriting them.
- When scope is ambiguous, choose the narrower interpretation and ask before expanding it.

## Type safety

- Prefer the strictest supported type-checking mode and explicit null/error handling.
- Do not introduce `any`, weak escape hatches, non-null assertions, or untyped boundaries when a typed alternative is practical. Prefer `unknown` plus a validated type guard at dynamic boundaries.
- Do not use type assertions or casts to silence an error. First consider narrowing, discriminated unions, generics, overloads, schema validation, or correcting the underlying model. If a cast is genuinely necessary, keep it narrow, prove the invariant at the boundary, and explain the reason briefly.
- Preserve exhaustiveness for closed sets and make invalid states difficult to represent.

## Literals and duplication

- Remove repeated domain/status/event/route/key strings and magic numbers. Prefer a named constant, enum, or language-appropriate typed value; use enums for stable closed sets when the language and serialization boundary support them cleanly.
- Do not force enums for user-facing text, free-form data, URLs, regular expressions, SQL, or values owned by an external system. Keep external representations explicit and centralized.
- Apply DRY to duplicated knowledge, not merely similar-looking code. Keep abstractions local to the bounded context that owns them.

## Smells and design

Check for and address relevant smells, including long or deeply nested functions, duplication, dead code, magic values, primitive obsession, god objects, feature envy, leaky abstractions, hidden mutable state, and unclear names. Fix the cause rather than adding lint suppressions or comments that conceal it.

Apply SOLID pragmatically:

- Give modules and functions one cohesive reason to change.
- Prefer small interfaces owned by their consumers.
- Substitute implementations without weakening contracts.
- Depend on stable abstractions at genuine boundaries.
- Keep high-level policy independent from infrastructure details.

Use a design pattern only when it resolves a concrete recurring design pressure; state the pressure, why the pattern fits, and its cost. Prefer a simple composition or direct function when it is clearer. Keep boundaries explicit and make code easy to test.

## Monorepo decisions

Recommend or introduce a monorepo only when the repository has multiple deployables or packages that benefit from coordinated versioning, shared tooling, dependency constraints, or atomic changes. Before proposing one, inspect package boundaries, ownership, dependency direction, workspace tooling, build/test caching, CI impact, and release strategy. Do not add monorepo complexity as a default preference.

## Completion bar

Before declaring the work complete, confirm:

- strict type checks pass without unjustified escape hatches;
- lint and formatting checks pass without broad suppressions;
- relevant tests cover normal, boundary, and failure behavior;
- no obvious smell, duplication, or magic-literal regression was introduced;
- any design pattern, enum, abstraction, or architecture change has a concrete justification;
- the final response names the checks run and any deliberate exceptions.

---
name: deprecation-management
description: "Find deprecated APIs, symbols, configuration, dependencies, and patterns; identify or implement replacements; update callers and tests safely. Use when the user asks to find, add, replace, or update deprecated code. Do not re-export deprecated symbols or add compatibility aliases unless explicitly authorized."
metadata:
  short-description: "Find and migrate deprecated code safely"
---

# Deprecation Management

Find and migrate deprecated code with a focused, evidence-based change. Follow `$strict-code-quality` and its no-drive-by-change rule.

## Operating modes

- If the user asks to find or report deprecations, work read-only and return evidence-backed findings.
- If the user explicitly asks to replace, update, add, or migrate deprecated code, implement the smallest complete migration within the requested scope.
- If the request is ambiguous, report the affected surface and proposed replacement first; do not modify code merely because a deprecation is present.

## Workflow

1. Identify the language, framework, runtime, package manager, dependency versions, compiler/linter settings, generated-code boundaries, and public package APIs.
2. Locate candidates using compiler and linter diagnostics, Sonar findings, `rg` searches, dependency manifests and lockfiles, migration notes, and repository tests. A name match alone is not proof of deprecation.
3. Verify each candidate against authoritative versioned documentation, release notes, type declarations, or the project's deprecation annotation. Record the replacement, removal timeline, behavior differences, and version constraints.
4. Map the complete in-scope surface: definitions, callers, imports, barrel files, `__all__`, package exports, tests, fixtures, examples, configuration, and generated sources.
5. Choose the direct supported replacement. Preserve behavior, error semantics, performance expectations, type safety, and external contracts unless the user requests a behavior change.
6. If the replacement does not exist, add the smallest cohesive implementation in the module that owns the behavior. Add focused tests for normal, boundary, and failure behavior.
7. Update callers, tests, and required documentation or generated outputs only when they are part of the requested scope or strictly required for a valid build.
8. Verify the deprecated usage is gone from the in-scope production surface, run targeted formatter/lint/type/test checks, and inspect the final diff for unrelated changes.

## No re-export rule

- Never re-export a deprecated symbol from a barrel, `__init__`, `__all__`, package entry point, public index, or compatibility module.
- Never add an alias, wrapper, forwarding function, or compatibility shim under the deprecated name to preserve an old import path.
- Export the replacement through an existing intended public boundary only when the requested migration requires it. Do not expand a package's public API as a side effect.
- If removing an existing deprecated export may break external consumers, report the compatibility risk and ask for direction; do not create a new re-export automatically.
- Do not edit generated files by hand. Update their source or generator and regenerate only when explicitly requested or strictly required by the migration.

## Quality constraints

- Do not weaken strict compiler, type-checker, linter, or test settings to make the migration pass.
- Do not use casts, non-null assertions, `any`, or suppression comments to hide an incompatible replacement. Prefer narrowing, type guards, generics, overloads, schema validation, or correcting the model.
- Preserve stable external serialization explicitly. Use enums or named constants for closed domain values when appropriate, but do not force them onto free-form or externally owned values.
- Do not upgrade unrelated dependencies, reformat unrelated files, reorganize imports broadly, rename unrelated symbols, or clean up neighboring code.
- If an API is removed rather than replaced, add a clear migration note only when requested or required by the project's existing release process.

## Output

For a report, return:

- deprecated item and authoritative evidence;
- affected files, symbols, exports, and consumers;
- supported replacement and compatibility considerations;
- severity, confidence, and remaining unknowns;
- migration steps with validation checks.

For an implementation, return the same summary plus changed files, tests/checks run, confirmation that no deprecated symbol was newly re-exported, and any deliberate exception.

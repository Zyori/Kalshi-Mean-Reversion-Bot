"""Analyzers — small per-question modules that look at recently resolved
paper trades and emit Findings the operator approves or dismisses.

To add a new analyzer: write a file in this directory that exposes
`evaluate(ctx: AnalysisContext) -> list[Finding]`, then add it to
registry.py.
"""

"""Edges = named hypotheses about how a specific soccer event mispriced the
moneyline. One file per edge. The registry composes them in priority order.

To add a new edge: write a new file in this directory with a function that
takes EdgeContext and returns EdgeSignal | None, then add it to
soccer/registry.py.
"""

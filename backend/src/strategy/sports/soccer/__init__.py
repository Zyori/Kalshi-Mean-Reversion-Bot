"""Soccer strategy package.

Public surface is just SoccerClassifier so importers stay decoupled from
the internal layout. The edge registry, edge functions, and predicates
are all importable directly for testing, but the classifier is the
intended entry point.
"""

from src.strategy.sports.soccer.classifier import SoccerClassifier

__all__ = ["SoccerClassifier"]

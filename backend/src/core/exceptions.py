class BotError(Exception):
    pass


class IngestionError(BotError):
    pass


class StrategyError(BotError):
    pass


class TradingError(BotError):
    pass


class AuthenticationError(IngestionError):
    pass

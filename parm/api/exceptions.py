class PatternMismatchException(Exception):
    pass


class TooManyMatches(PatternMismatchException):
    pass


class NoMatches(PatternMismatchException):
    pass


class ExpectFailure(PatternMismatchException):
    pass


class CaptureCollision(PatternMismatchException):
    def __init__(self, name, exiting, updated):
        self.name = name
        self.existing = exiting
        self.updated = updated

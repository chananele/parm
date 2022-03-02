class PatternMismatchException(Exception):
    pass


class TooManyMatches(PatternMismatchException):
    def __init__(self, matches):
        self.matches = matches


class NoMatches(PatternMismatchException):
    pass


class ExpectFailure(PatternMismatchException):
    pass


class CaptureCollision(PatternMismatchException):
    def __init__(self, name, exiting, updated):
        self.name = name
        self.existing = exiting
        self.updated = updated

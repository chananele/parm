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


class PatternTypeMismatch(PatternMismatchException):
    def __init__(self, v1, v2):
        self.v1 = v1
        self.v2 = v2


class PatternValueMismatch(PatternMismatchException):
    def __init__(self, v1, v2):
        self.v1 = v1
        self.v2 = v2

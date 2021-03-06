class PatternMismatchException(Exception):
    pass


class TooManyMatches(PatternMismatchException):
    pass


class NoMatches(PatternMismatchException):
    pass


class ExpectFailure(PatternMismatchException):
    pass


class InvalidAccess(PatternMismatchException):
    def __init__(self, message):
        self.message = message


class PatternUsageException(PatternMismatchException):
    pass


class ReverseSearchUnsupported(PatternUsageException):
    pass


class ForwardSearchUnsupported(PatternUsageException):
    pass


class UnresolvedSymbolException(PatternMismatchException):
    def __init__(self, name):
        self.name = name


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

    def __str__(self):
        return f'{self.v1}, {self.v2}'


class NoMoreInstructions(PatternMismatchException):
    pass


class NotAllOperandsMatched(PatternMismatchException):
    def __init__(self, operands):
        self.operands = operands


class OperandsExhausted(PatternMismatchException):
    def __init__(self, pattern):
        self.pattern = pattern


class ConstructParsingException(PatternMismatchException):
    def __init__(self, construct_error):
        self.construct_error = construct_error

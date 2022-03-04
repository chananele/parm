from contextlib import contextmanager

from parm.api.chaining import ChainMap, ChainStack, ChainCounter


class TransactionError(Exception):
    pass


class TransactionCommitOrderViolation(TransactionError):
    def __init__(self, transaction, given, expected):
        self.transaction = transaction
        self.given = given
        self.expected = expected


class Transaction:
    def __init__(self, parent=None):
        self._parent = parent  # type: Transaction
        self._rollback_ops = []
        self._children = []

    def rollback(self):
        for op in reversed(self._rollback_ops):
            op()
        self._rollback_ops.clear()

    def __del__(self):
        if self._rollback_ops:
            raise TransactionError('Transaction not committed or rolled back!')

    def add_rollback_op(self, op):
        self._rollback_ops.append(op)

    def create_transaction(self):
        result = Transaction(self)
        self._children.append(result)
        return result

    def _inherit(
            self,
            child  # type: Transaction
    ):
        last = self._children.pop()
        if child is not last:
            raise TransactionCommitOrderViolation(self, child, last)
        self._rollback_ops.extend(child._rollback_ops)

    def commit(self):
        p = self._parent
        if p is not None:
            p._inherit(self)
        self._rollback_ops.clear()


class Transactable:
    def __init__(self, transaction=None):
        if transaction is None:
            transaction = Transaction()
        self._transaction_stack = [transaction]

    @property
    def _current_transaction(self):
        return self._transaction_stack[-1]

    @contextmanager
    def _new_transaction(self):
        self._transaction_stack.append(self._current_transaction.create_transaction())
        try:
            yield
        finally:
            self._transaction_stack.pop(-1)

    @contextmanager
    def transact(self):
        with self._new_transaction():
            try:
                yield
            except Exception:
                self._current_transaction.rollback()
                raise
            else:
                self._current_transaction.commit()

    def _add_rollback_op(self, op):
        self._current_transaction.add_rollback_op(op)

    def _track_chainmap(self, cm: ChainMap):
        m = cm.push_map()
        self._add_rollback_op(cm.pop_map(m))

    def _track_chainstack(self, cs: ChainStack):
        s = cs.push_stack()
        self._add_rollback_op(cs.pop_stack(s))
        return s

    def _track_chaincounter(self, cc: ChainCounter):
        ix = cc.push_counter()
        self._add_rollback_op(cc.pop_counter(ix))

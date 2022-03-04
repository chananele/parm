from typing import TypeVar, Reversible, Iterable, Protocol

_T_co = TypeVar("_T_co", covariant=True)


class ReversibleIterable(Reversible[_T_co], Iterable[_T_co], Protocol[_T_co]):
    pass

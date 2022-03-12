from chainmap import ChainMap as _ChainMap


class ChainMap(_ChainMap):
    def push_map(self, m=None):
        if m is None:
            m = {}
        self.maps.insert(0, m)
        return m

    def pop_map(self, m=None):
        result = self.maps.pop(0)
        if m is not None:
            assert result is m
        return result


class ChainStack:
    def __init__(self, *stacks):
        if not stacks:
            stacks = [[]]

        self._stacks = stacks

    def __len__(self):
        return sum(len(s) for s in self._stacks)

    def push(self, v):
        self._stacks[-1].append(v)

    def pop(self, index=-1):
        self._stacks[-1].pop(index)

    def peek(self, index=-1):
        for s in self._stacks:
            s_len = len(s)
            if s_len < -index:
                index += s_len
                continue
            return s[index]
        raise IndexError('')

    def new_child(self, lst=None):
        if lst is None:
            lst = []
        return ChainStack(*self._stacks, lst)

    def push_stack(self, lst=None):
        if lst is None:
            lst = []
        self._stacks.append(lst)
        return lst

    def pop_stack(self, lst=None):
        result = self._stacks.pop(-1)
        if lst is not None:
            assert result is lst
        return result

    def __contains__(self, item):
        return any(item in s for s in self._stacks)

    def __iter__(self):
        for s in self._stacks:
            yield from s

    def __reversed__(self):
        for s in reversed(self._stacks):
            yield from reversed(s)

    def __getitem__(self, item):
        for s in self._stacks:
            s_len = len(s)
            if s_len <= item:
                item -= s_len
                continue
            return s[item]
        raise IndexError(item)


class ChainCounter:
    def __init__(self, *counts):
        if not counts:
            counts = [0]
        else:
            counts = list(counts)
        self._counts = counts

    @property
    def value(self):
        return self._counts[-1]

    def inc(self, cnt=1):
        return self.set(self.value + cnt)

    def dec(self, cnt=1):
        return self.set(self.value - cnt)

    def set(self, cnt):
        self._counts[-1] = cnt
        return cnt

    def new_child(self, value=None):
        if value is None:
            value = self.value
        return ChainCounter(*self._counts, value)

    def push_counter(self, value=None):
        if value is None:
            value = self.value
        self._counts.append(value)
        return len(self._counts)

    def pop_counter(self, ix=None):
        if ix is not None:
            assert ix == len(self._counts)
        return self._counts.pop(-1)

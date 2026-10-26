def used():
    return 1


def unused_helper():
    return 2


class Orphan:
    pass


class Used:
    def method_called(self):
        return self

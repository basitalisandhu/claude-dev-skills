def simple(a):
    return a

def branchy(a, b):
    if a and b:
        for i in range(3):
            if i == 2:
                return i
    elif b:
        while a:
            a -= 1
    try:
        pass
    except ValueError:
        pass
    return [x for x in range(3) if x]

class K:
    def m(self, x):
        return x if x else None

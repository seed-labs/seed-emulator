from __future__ import annotations

class Vector:
    x:float
    y:float
    z:float

    def __init__(self, x, y, z) -> None:
        self.x = x
        self.y = y
        self.z = z

    def isMoved(self, vec:Vector)->bool:
        if self.x != vec.x:
            return True
        elif self.y != vec.y:
            return True
        elif self.z != vec.z:
            return True
        else:
            return False
from .Vector import Vector

class Box:
    x_min:float
    x_max:float
    y_min:float
    y_max:float
    z_min:float
    z_max:float

    def __init__(self, x_min, x_max, y_min, y_max, z_min, z_max) -> None:
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.z_min = z_min
        self.z_max = z_max
    
    def isInside(self, position:Vector):
        return position.x <= self.x_max and position.x >= self.x_min and\
                position.y <= self.y_max and position.y >= self.y_min and\
                position.z <= self.z_max and position.z >= self.z_max
    
    #To-do isIntersect
    #Cannot understand how it works (Math Problem)
    def isIntersect(self, positionA:Vector, positionB:Vector):
        if self.isInside(positionA) or self.isInside(positionB):
            return True
        
        boxSize = Vector(0.5 * (self.x_max - self.x_min),
                         0.5 * (self.y_max - self.y_min),
                         0.5 * (self.z_max - self.z_min))
        
        boxCenter = Vector(self.x_min + boxSize.x, 
                           self.y_min + boxSize.y, 
                           self.z_min + boxSize.z)
        
        # Put line-segment in box space
        aInBox = Vector(positionA.x - boxCenter.x,
                        positionA.y - boxCenter.y,
                        positionA.z - boxCenter.z)
        
        bInBox = Vector(positionB.x - boxCenter.x,
                        positionB.y - boxCenter.y,
                        positionB.z - boxCenter.z)
        
        # Get line-segment midpoint and extent
        lMid = Vector(0.5 * (aInBox.x + bInBox.x),
                      0.5 * (aInBox.y + bInBox.y),
                      0.5 * (aInBox.z + bInBox.z))
        
        l = Vector(aInBox.x - lMid.x,
                   aInBox.y - lMid.y,
                   aInBox.z - lMid.z)
        
        lExt = Vector(abs(l.x),
                      abs(l.y),
                      abs(l.z))
        
        # Use Separating Axis Test
        # Separation vector from box center to line-segment center is lMid, since the
        # line is in box space, if any dimension of the line-segment did not intersect
        # the box, return false, which means the whole line-segment didn't
        # intersect the box.
        
        if (abs(lMid.x) > boxSize.x + lExt.x):
            return False
        if (abs(lMid.y) > boxSize.y + lExt.y):
            return False
        if (abs(lMid.z) > boxSize.z + lExt.z):
            return False
        
        # Cross-products of line and each axis

        if (abs(lMid.y * l.z - lMid.z * l.y)>(boxSize.y * lExt.z + boxSize.z * lExt.y)):
            return False
        if (abs(lMid.x * l.z - lMid.z * l.x)>(boxSize.x * lExt.z + boxSize.z * lExt.x)):
            return False
        if (abs(lMid.x * l.y - lMid.y * l.x)>(boxSize.x * lExt.y + boxSize.y * lExt.x)):
            return False
        
        return True
    

        

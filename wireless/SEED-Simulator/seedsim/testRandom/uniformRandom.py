import os

PATH = os.path.dirname(__file__)

class uniformRandom(object):
    # Open the file in read mode
    with open(os.path.join(PATH, 'pRef.txt'), 'r') as file:
            # Read all the lines of the file into a list
            random = file.readlines()
    line = 0
    
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(uniformRandom, cls).__new__(cls)
        return cls.instance
    
    # allow access to class methods on the class without creating an instance.
    @classmethod
    def getRandom(cls):
        random = float(cls.random[cls.line])
        cls.line += 1
        return random
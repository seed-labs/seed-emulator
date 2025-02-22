from enum import Flag, auto

class OptionMode(Flag):
    BUILD_TIME = auto() # static/hardcoded (required re-compile to change)
    RUN_TIME = auto() # i.e. envsubst (required only docker compose stop/start )
    

# TODO: make option values typed ! i.e if option is 'bool' and you try to set it to a 'str' value -> exception
class BaseOption:
    """! a base class for KEY-VALUE pairs representing Settings,Parameters or Feature Flags
    """

    def __eq__(self, other):
        if not other: return False
        
        if issubclass(other, BaseOption):
            return self.name==other.name
        else:
            raise NotImplementedError
        
    @property
    def name(self) -> str:
        """Should return the name of the option."""
        pass

    @property
    def value(self) -> str:
        """Should return the value of the option."""
        pass

    @value.setter
    def value(self, new_value: str):
        """Should allow setting a new value."""
        pass

    @property
    def mode(self)->OptionMode:
        """Should return the mode of the option."""
        pass
    @mode.setter
    def mode(self, new_mode: OptionMode):
        pass
    
    # def defaultValue(self)
    
    def supportedModes(self)->OptionMode:
        pass
    # def __eq__(self, other: Option):

    #TODO: add description(self)->str: here


#class ScopedOption:
# wrapper around List[Tuple[ BaseOption, Scope ] ]
#  that is an option, that is aware, that it has different values in different scopes

from enum import Flag, auto
from typing import List, Optional, Type, Any



class AutoRegister():
    """!@brief metaclass to automatically register
            option types with the option-registry
    """
    def __init_subclass__(cls, **kwargs):
        """Automatically register all subclasses upon definition."""

        from .OptionRegistry import OptionRegistry
        super().__init_subclass__(**kwargs)
        #  Auto-register & create factory method
        OptionRegistry().register(cls)
        '''
        if issubclass(cls, BaseComponent):
            if (children := cls.components()) != None:
                for c in children:
                    OptionRegistry.register(c.name(), cls.name() )
        '''

# makes @property work with @classmethod
class ClassProperty:
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func(owner)

class BaseComponent(): # metaclass=OptionGroupMeta
    """!@note options implement the 'composite' pattern
            and can be aggregated into groups/composites.
            i.e. all options that logically belong to BGP or SCION
    """
    @classmethod
    def prefix(cls) -> Optional[str]:
        """!@brief prefix of the 'composite' (aggregate of multiple options)
        """
        if hasattr(cls, '__prefix'):
           # return cls.__prefix
           return cls.__dict__['__prefix']
        else:
            return None

    @classmethod
    def fullname(cls) -> str:
        return f'{cls.prefix()}_{cls.getName()}'

    @ClassProperty
    def name(cls) -> str:
        return cls.__name__.lower()

    @classmethod
    def getName(cls) -> str:
        return cls.__name__.lower()

    @classmethod
    def components(cls) -> Optional[List['BaseComponent']]:
        return None

    @classmethod
    def components_recursive(cls, prefix: str = None) -> Optional[List['BaseComponent']]:
        """
        !@brief flattens child components recursively
        """
        opts = []

        for c in cls.components():
            if c.components() == None:
                opts.append(c)
            else:
                opts.extend(c.components_recursive(prefix = f'{cls.getName()}_{c.getName()}'))
        return opts

class OptionMode(Flag):
    """!@brief characteristics of an option,
        during which time it might be changed or set
    """
    # static/hardcoded (require re-compile + image-rebuild to change)
    BUILD_TIME = auto()
    # i.e. envsubst (require only docker compose stop/start )
    RUN_TIME = auto()



class OptionGroupMeta(type): # or BaseComponentMeta ..
    """Metaclass to auto-register nested options within a group."""

    def __new__(cls, name, bases, class_dict):

        if name.lower() == 'scionstackopts':
            name = 'scion'
        if name.lower() == 'sysctlopts':
            name = 'sysctl'

        from .OptionRegistry import OptionRegistry

        new_cls = super().__new__(cls, name, bases, class_dict)
        # if (cls == OptionGroupMeta): return new_cls
        qname = class_dict['__qualname__']
        if name in ['Option', 'BaseOption', 'BaseOptionGroup']: return new_cls
        if BaseComponent in bases or any([ issubclass(b, BaseComponent) for b in bases]):
            new_cls._children = {}

            # Auto-register (nested) Option classes
            for attr_name, attr_value in class_dict.items():
                if issubclass(type(attr_value), OptionGroupMeta):
                    # prefixed_name = f"{name}_{attr_value.name()}"
                    # better call new_cls.add() # here
                    new_cls._children[attr_value.name] = attr_value
            # don't register nested options twice (but only once as child of the parent 'composite')
            if '.' not in qname or qname.startswith('SEEDEmuOptionSystemTestCase'):
                OptionRegistry().register(new_cls)
        return new_cls

# Actually duplicated with 'Option'
class BaseOption(BaseComponent, metaclass=OptionGroupMeta):
    """! a base class for KEY-VALUE pairs representing Settings, Parameters or Feature Flags"""

    def __eq__(self, other):
        if not other: return False

        if issubclass(other, BaseOption):
            return self.name==other.name
        else:
            raise NotImplementedError

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

    @classmethod
    def supportedModes(cls) -> OptionMode:
        pass
    # def __eq__(self, other: Option):

# simple option
class Option(BaseOption):
    """!@brief simple base class for all user defined options.

        @note Rarely should users require any more functionality
            and be compelled to implement their own option base class.
    """
    # Immutable class variable to be defined in subclasses
    value_type: Type[Any]

    def __init__(self, value: Optional[Any] = None, mode: OptionMode = None):
        cls = self.__class__
        key = cls.getName().lower()
        # TODO: ONLY REGISTRY IS ALLOWED TO INSTANTIATE ME !!
        import inspect
        caller_frame = inspect.stack()[1]
        caller_name = caller_frame.function
        #if cls.__name__ not in caller_name:
        if caller_name != 'create_option':
            raise AssertionError('constructor of Option is private - use the respective OptionRegistry factory method insted')


        # Ensure default matches the class-level type
        if value is not None and not isinstance(value, self.value_type):
            raise TypeError(f"Expected {self.value_type.__name__} for '{self.name}', got {type(value).__name__}")

        self._mutable_value = value if value != None else cls.default()
        self._mutable_mode = None
        if not mode in [ OptionMode.BUILD_TIME, None]:
            assert mode in self.supportedModes(), f'unsupported mode for option {key.upper()}'
            self._mutable_mode = mode

    def __repr__(self):
        return f"Option(key={self.name()}, value={self._mutable_value})"
    
    def repr_runtime(self) -> str:
        return None
    
    def repr_build_time(self) -> str:
        return None

    @classmethod
    def getType(cls) -> Type:
        """return this option's value type"""
        return cls.value_type

    @property
    def value(self) -> str:
        """!@brief get the current value of the setting/parameter
            represented by this option
        """
        if (val := self._mutable_value) != None:
            return val
        else:
            return self.default()

    @classmethod
    def default(cls):
        """ default option value if unspecified by user"""
        return None

    @classmethod
    def defaultMode(cls):
        """ default mode if unspecified by user"""
        return OptionMode.BUILD_TIME

    @value.setter
    def value(self, new_value: Any):
        """!@brief Allow updating the option's value.
            Trying to set of value of type other than this option's value_type
            throws a TypeError
        """
        if not isinstance(new_value, self.value_type):
            raise TypeError(f"Expected {self.value_type.__name__} for '{self.name}', got {type(new_value).__name__}")
        assert new_value != None, 'Logic Error - option value cannot be None!'
        self._mutable_value = new_value

    @property
    def mode(self):
        if (mode := self._mutable_mode) != None:
            return mode
        else:
            return self.defaultMode()

    @mode.setter
    def mode(self, new_mode):
        self._mutable_mode = new_mode

    @classmethod
    def description(cls) -> str:
        """!@brief a short description of what this option is for
            and its allowed values
        """
        return cls.__doc__ or "No documentation available."


#class ScopedOption:
# wrapper around List[Tuple[ BaseOption, Scope ] ]
#  that is an option, that is aware, that it has different values in different scopes




class BaseOptionGroup(BaseComponent , metaclass=OptionGroupMeta):
    _children = {}


    def describe(self) -> str:
        return f"OptionGroup {self.__class__.__name__}:\n" + "\n".join(
            #[f"  - {opt.name}" for opt in self._children]
            [f"  - {name}" for name,_ in self._children.items()]
            )
    '''
    def add(self, option: BaseComponent):
        #self._children.append( option )
        self._children[option.name] = [f"  - {opt.name}" for opt in self._children]

    def get(self, option_name: str) -> Optional[BaseComponent]:
       return self._children.get(option_name, None)
    '''

    @classmethod
    def components(cls):
        return [v for _, v in cls._children.items()]
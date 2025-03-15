from typing import Dict, Type


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class OptionRegistry(metaclass=SingletonMeta):
    _options: Dict[str, Type['Option']]  = {}


    @classmethod
    def register(cls, option: Type['BaseComponent'], prefix: str = None):
        """Registers an option by name and creates a factory method for it."""

        # if issubclass(option, BaseOptionGroup): return ?!

        opt_name = option.__name__
        if opt_name in ['BaseOption', 'Option', 'BaseComponent', 'BaseOptionGroup'] : return
        opt_name = opt_name.lower()
        register_name = opt_name
        if prefix != None:
            register_name = f'{prefix}_' + opt_name
            setattr(option, '__prefix', prefix)

        cls._options[register_name] = option

        if prefix != None: prefix += '_'
        else: prefix = ''
        # Dynamically add a factory method to the registry class
        factory_name = f"{prefix}{opt_name}"
        if not hasattr(cls, factory_name):
            setattr(cls, factory_name, lambda *args, **kwargs: cls.create_option(factory_name, *args, **kwargs))

        # also register any children
        if (components := option.components()) != None:
            for c in components:
                cls.register(c, prefix + option.getName().lower())

    @classmethod
    def create_option(cls, name: str, *args, **kwargs) -> 'Option':
        """Creates an option instance if it's registered."""
        option_cls = cls._options.get(name)
        if not option_cls:
            raise ValueError(f"Option '{name}' is not registered.")
        # Instantiate with given arguments
        return option_cls(*args[1:], **kwargs)


    @classmethod
    def getType(cls, name: str, prefix: str = None) -> Type['BaseComponent']:
        """Retrieves a registered option type"""
        if prefix != None:
            name = prefix + '_' + name

        return cls._options.get(name)

    @classmethod
    def getOption(cls, name: str, *args, prefix: str = None, **kwargs) -> 'BaseComponent':
        """Retrieves a registered option instance
            constructed with the given arguments
        """
        if prefix != None:
            name = prefix + '_' + name

        return cls.create_option(name, *args, **kwargs)


    @classmethod
    def list_options(cls):
        """Lists all registered options."""
        return list(cls._options.keys())

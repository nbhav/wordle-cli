import inspect



def check_not_none(*param_names):
    """
        Function to be used as decrator to avoid Null explicit Null checks
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            sig = inspect.signature(func)
            bound = sig.bind(self, *args, **kwargs)
            for name in param_names:
                if bound.arguments.get(name) is None:
                    raise TypeError(f"{name} cannot be None")
            return func(self, *args, **kwargs)
        return wrapper
    return decorator
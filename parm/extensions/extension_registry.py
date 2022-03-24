import inspect


class ExtensionRegistryFactory:
    def __init__(self, extension_type_registry=None):
        if extension_type_registry is None:
            extension_type_registry = []
        self._extension_type_registry = extension_type_registry

    def clone(self):
        return ExtensionRegistryFactory(self._extension_type_registry)

    def register_extension_type(self, ext_type):
        self._extension_type_registry.append(ext_type)

    def create_registry(self, *args, **kwargs):
        return ExtensionRegistry(self._extension_type_registry, args, kwargs)


class ExtensionRegistry:
    def __init__(self, extension_type_registry=None, ext_args=None, ext_kwargs=None):
        if extension_type_registry is None:
            extension_type_registry = []
        if ext_args is None:
            ext_args = ()
        if ext_kwargs is None:
            ext_kwargs = {}

        self._extension_type_registry = extension_type_registry
        self._loaded_extensions = {}
        self._ext_args = ext_args
        self._ext_kwargs = ext_kwargs

        self._loading_extensions = set()

    @property
    def ext_args(self):
        return self._ext_args

    @property
    def ext_kwargs(self):
        return self._ext_kwargs

    def _get_derived_extension_type(self, ext_type):
        derived_types = []
        for _type in self._extension_type_registry:
            for _t in inspect.getmro(_type):
                if _t is ext_type:
                    derived_types.append(_type)
                    break
        if not derived_types:
            raise TypeError(f'No extension of type "{ext_type}" found')
        if len(derived_types) > 1:
            raise TypeError(f'Multiple extension of type "{ext_type}" found')
        return derived_types[0]

    def _init_ext_type(self, ext_type):
        return ext_type(self, *self.ext_args, **self.ext_kwargs)

    def load_extension(self, ext_type):
        derived_type = self._get_derived_extension_type(ext_type)

        try:
            return self._loaded_extensions[derived_type]
        except KeyError:
            pass

        if derived_type in self._loading_extensions:
            raise TypeError(f'Recursive dependency when loading "{derived_type}"')
        self._loading_extensions.add(derived_type)

        ext = self._init_ext_type(derived_type)
        self._loaded_extensions[derived_type] = ext
        return ext

    def load_extensions(self):
        for t in self._extension_type_registry:
            self.load_extension(t)

import ctypes
import ctypes.util
import threading
from typing import NamedTuple, List, Any


class MagicDLLDefinition(NamedTuple):
    restype: Any = None
    argtypes: List[Any] = []


magic_t = ctypes.c_void_p


class MagicDLL:
    """
    Raw libmagic interface
    """
    _methods = {
        "magic_open": MagicDLLDefinition(
            restype=magic_t,
            argtypes=[ctypes.c_int]
        ),
        "magic_close": MagicDLLDefinition(
            argtypes=[magic_t]
        ),
        "magic_error": MagicDLLDefinition(
            restype=ctypes.c_char_p,
            argtypes=[magic_t]
        ),
        "magic_errno": MagicDLLDefinition(
            restype=ctypes.c_int,
            argtypes=[magic_t]
        ),
        "magic_descriptor": MagicDLLDefinition(
            restype=ctypes.c_char_p,
            argtypes=[magic_t, ctypes.c_int]
        ),
        "magic_file": MagicDLLDefinition(
            restype=ctypes.c_char_p,
            argtypes=[magic_t, ctypes.c_char_p]
        ),
        "magic_buffer": MagicDLLDefinition(
            restype=ctypes.c_char_p,
            argtypes=[magic_t, ctypes.c_void_p, ctypes.c_size_t]
        ),
        "magic_getflags": MagicDLLDefinition(
            restype=ctypes.c_int,
            argtypes=[magic_t]
        ),
        "magic_setflags": MagicDLLDefinition(
            restype=ctypes.c_int,
            argtypes=[magic_t, ctypes.c_int]
        ),
        "magic_check": MagicDLLDefinition(
            restype=ctypes.c_int,
            argtypes=[magic_t, ctypes.c_char_p]
        ),
        "magic_compile": MagicDLLDefinition(
            restype=ctypes.c_int,
            argtypes=[magic_t, ctypes.c_char_p]
        ),
        "magic_list": MagicDLLDefinition(
            restype=ctypes.c_int,
            argtypes=[magic_t, ctypes.c_char_p]
        ),
        "magic_load": MagicDLLDefinition(
            restype=ctypes.c_int,
            argtypes=[magic_t, ctypes.c_char_p]
        ),
        "magic_load_buffers": MagicDLLDefinition(
            restype=ctypes.c_int,
            argtypes=[magic_t, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_size_t), ctypes.c_size_t]
        ),
        "magic_getparam": MagicDLLDefinition(
            restype=ctypes.c_int,
            argtypes=[magic_t, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
        ),
        "magic_setparam": MagicDLLDefinition(
            restype=ctypes.c_int,
            argtypes=[magic_t, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
        ),
        "magic_version": MagicDLLDefinition(
            restype=ctypes.c_int
        )
    }

    def _load_library(self):
        return ctypes.cdll.LoadLibrary(ctypes.util.find_library("magic"))

    def __init__(self):
        self.libmagic = self._load_library()

    def __getattr__(self, item):
        if not item.startswith("magic_") or item not in self._methods:
            raise AttributeError(f"LibmagicDLL object has no attribute {item}")
        if not hasattr(self.libmagic, item):
            raise NotImplementedError(f"Installed version of libmagic doesn't implement {item}")

        libmagic_definition = self._methods[item]
        libmagic_method = getattr(self.libmagic, item)
        libmagic_method.restype = libmagic_definition.restype
        libmagic_method.argtypes = libmagic_definition.argtypes
        return libmagic_method


class MagicException(RuntimeError):
    def __init__(self, message, errno):
        self.errno = errno
        super().__init__(message)


class Magic:
    def __init__(self, flags=0, database_filename=None):
        self.dll = MagicDLL()
        self.flags = flags
        self.cookie = self.dll.magic_open(self.flags)
        # Libmagic methods are not thread-safe within the same cookie
        self.lock = threading.Lock()
        self.load(database_filename)

    def _check_error(self, result, error_value=None):
        if result == error_value:
            message = self.dll.magic_error(self.cookie)
            errno = self.dll.magic_errno(self.cookie)
            raise MagicException(message, errno)

    def from_descriptor(self, fd):
        with self.lock:
            result = self.dll.magic_descriptor(self.cookie, fd)
            self._check_error(result)
            return result

    def from_file(self, filename):
        with self.lock:
            result = self.dll.magic_file(self.cookie, coerce_filename(filename))
            self._check_error(result)
            return result

    def from_buffer(self, buffer):
        if not isinstance(buffer, bytes):
            raise TypeError(f"Expected bytes, not {type(buffer)}")
        with self.lock:
            result = self.dll.magic_buffer(self.cookie, buffer, len(buffer))
            self._check_error(result)
            return result

    def get_flags(self):
        with self.lock:
            return self.dll.magic_getflags(self.cookie)

    def set_flags(self, flags):
        with self.lock:
            result = self.dll.magic_setflags(self.cookie, flags)
            self._check_error(result, error_value=-1)
            self.flags = flags

    def check(self, database_filename):
        with self.lock:
            result = self.dll.magic_check(self.cookie, coerce_filename(database_filename))
            self._check_error(result, error_value=-1)

    def compile(self, database_filename):
        with self.lock:
            result = self.dll.magic_compile(self.cookie, coerce_filename(database_filename))
            self._check_error(result, error_value=-1)

    def list(self, database_filename):
        with self.lock:
            result = self.dll.magic_list(self.cookie, coerce_filename(database_filename))
            self._check_error(result, error_value=-1)

    def load(self, database_filename):
        with self.lock:
            result = self.dll.magic_load(self.cookie, coerce_filename(database_filename))
            self._check_error(result, error_value=-1)

    def get_param(self, param):
        with self.lock:
            val = ctypes.c_size_t()
            result = self.dll.magic_getparam(self.cookie, param, ctypes.byref(val))
            self._check_error(result, error_value=-1)
            return val.value

    def set_param(self, param, value):
        with self.lock:
            val = ctypes.c_size_t(value)
            result = self.dll.magic_setparam(self.cookie, param, ctypes.byref(val))
            self._check_error(result, error_value=-1)

    def get_version(self):
        return self.dll.magic_version()

    def __del__(self):
        if getattr(self, "dll", None) and getattr(self, "cookie", None):
            self.dll.magic_close(self.cookie)
            self.cookie = None


def coerce_filename(filename):
    if filename is None:
        return None
    # ctypes will implicitly convert unicode strings to bytes with
    # .encode('ascii').  If you use the filesystem encoding
    # then you'll get inconsistent behavior (crashes) depending on the user's
    # LANG environment variable
    if isinstance(filename, str):
        return filename.encode('utf-8', 'surrogateescape')
    else:
        return filename

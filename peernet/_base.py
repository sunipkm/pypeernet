from __future__ import annotations
from ctypes import CFUNCTYPE, POINTER, byref, cast, c_void_p, c_char_p, c_int, c_size_t, c_bool, cdll

import platform

os_type = platform.system()

ext = ''
if os_type.lower() == 'linux':
    ext = '.so'
elif os_type.lower() == 'darwin':
    ext = '.dylib'
else:
    raise RuntimeError('Platform %s not known.'%(os_type))

lib = cdll.LoadLibrary('libpeer' + ext)

# Internal things

LIBPEER_CALLBACK_FUNC_TYPE = CFUNCTYPE(None, c_void_p, c_char_p, c_size_t, c_char_p, c_size_t, c_void_p, c_size_t) # return: None, args: self, message_type, len(message_type), remote_peer, len(remote_peer), remote_data, len(remote_data)

# For the remote data, use use uptr = cast(ptr, c_uint8_t), then get the value into a bytes array (uptr.value)

lib.peer_py_list_connected.argtypes = c_void_p,
lib.peer_py_list_connected.restype = c_void_p

lib.peer_py_on_connect.argtypes = c_void_p, c_char_p, LIBPEER_CALLBACK_FUNC_TYPE # self, peer, callback
lib.peer_py_on_connect.restype = c_int

lib.peer_py_on_disconnect.argtypes = c_void_p, c_char_p, LIBPEER_CALLBACK_FUNC_TYPE
lib.peer_py_on_disconnect.restype = c_int

lib.peer_py_on_evasive.argtypes = c_void_p, c_char_p, LIBPEER_CALLBACK_FUNC_TYPE
lib.peer_py_on_evasive.restype = c_int

lib.peer_py_on_silent.argtypes = c_void_p, c_char_p, LIBPEER_CALLBACK_FUNC_TYPE
lib.peer_py_on_silent.restype = c_int

lib.peer_py_on_message.argtypes = c_void_p, c_char_p, c_char_p, LIBPEER_CALLBACK_FUNC_TYPE # self, message_type, peer, callback
lib.peer_py_on_message.restype = c_int

lib.peer_py_disable_on_connect.argtypes = c_void_p, c_char_p # self, peer
lib.peer_py_disable_on_connect.restype = c_int

lib.peer_py_disable_on_disconnect.argtypes = c_void_p, c_char_p # self, peer
lib.peer_py_disable_on_disconnect.restype = c_int

lib.peer_py_disable_on_evasive.argtypes = c_void_p, c_char_p # self, peer
lib.peer_py_disable_on_evasive.restype = c_int

lib.peer_py_disable_on_silent.argtypes = c_void_p, c_char_p # self, peer
lib.peer_py_disable_on_silent.restype = c_int

lib.peer_py_disable_on_message.argtypes = c_void_p, c_char_p, c_char_p # self, message_type, peer
lib.peer_py_disable_on_message.restype = c_int

lib.peer_py_errno.argtypes = c_void_p,
lib.peer_py_errno.restype = c_int

lib.peer_py_validate_name.argtypes = c_char_p,
lib.peer_py_validate_name.restype = int

lib.peer_py_validate_message_type.argtypes = c_char_p,
lib.peer_py_validate_message_type.restype = int

# public methods

lib.peer_new.argtypes = c_char_p, c_char_p, c_char_p, c_bool
lib.peer_new.restype = c_void_p

lib.peer_name.restype = c_char_p

# lib.peer_set_verbose.argtypes = None
# lib.peer_set_verbose.restype = None

# lib.peer_start.argtypes = c_void_p,
# lib.peer_start.restype = c_int

# lib.peer_python_destroy.argtypes = POINTER(c_void_p),
# lib.peer_python_destroy.restype = None
from __future__ import annotations
from ctypes import CFUNCTYPE
from ctypes import c_void_p
from ctypes import c_char_p
from ctypes import POINTER
from ctypes import c_int
from ctypes import c_size_t
from ctypes import c_bool
from ctypes import byref
from ctypes import cdll
from ctypes import c_int
from ctypes import cast
import time
import sys

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
# LIBPEER_CALLBACK_FUNC_TYPE = CFUNCTYPE(None, c_char_p, c_size_t, c_char_p, c_size_t, c_void_p, c_size_t)
LIBPEER_CALLBACK_FUNC_TYPE = CFUNCTYPE(None, c_char_p, c_size_t)

lib.peer_new.argtypes = c_char_p, c_char_p, c_char_p, c_bool
lib.peer_new.restype = c_void_p

lib.peer_py_list_connected.argtypes = c_void_p,
lib.peer_py_list_connected.restype = c_char_p

lib.peer_py_on_connect.argtypes = c_void_p, c_char_p, LIBPEER_CALLBACK_FUNC_TYPE
lib.peer_py_on_connect.restype = c_int

lib.peer_name.restype = c_char_p
lib.peer_start.restype = int

# lib.peer_set_verbose.argtypes = None
# lib.peer_set_verbose.restype = None

# lib.peer_start.argtypes = c_void_p,
# lib.peer_start.restype = c_int

# lib.peer_python_destroy.argtypes = POINTER(c_void_p),
# lib.peer_python_destroy.restype = None

class peer:
    def __init__(self, name: str, group: str | None, password: str, encryption: bool = True):
        if isinstance(group, str):
            _group = group.encode('utf-8')
        elif group is None:
            _group = c_char_p(0)
        self._peer_t = lib.peer_new(name.encode('utf-8'), _group, password.encode('utf-8'), encryption)
        self._callback_on_connect = {}
        print(self._peer_t)
        self._peer_t = cast(self._peer_t, POINTER(c_void_p))
        print(self.name())

    def name(self):
        _name = lib.peer_name(self._peer_t)
        name = _name.decode('utf-8')
        return name
    
    def set_verbose(self):
        lib.peer_set_verbose(self._peer_t)

    def start(self) -> int:
        return lib.peer_start(self._peer_t)

    def list_connected(self) -> dict:
        out = lib.peer_py_list_connected(self._peer_t)
        # out = cast(void_ptr, c_char_p)
        out = out.decode('utf-8')
        outmap = {}
        ufouts = out.split(',')
        for uf in ufouts:
            ws = uf.split(':')
            outmap[ws[0]] = ws[1]
        return outmap

    def errno(self) -> int:
        return lib.peer_py_errno(self._peer_t)

    def on_connect(self, name: str | None, fcn) -> int:
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            key = _peer
        elif name is None:
            _peer = c_char_p(0)
            key = "ALL"
        py_fcn = LIBPEER_CALLBACK_FUNC_TYPE(fcn)
        self._callback_on_connect[key] = py_fcn
        return lib.peer_py_on_connect(self._peer_t, _peer, py_fcn)

    def __del__(self):
        lib.peer_py_destroy(byref(self._peer_t))

def on_connect_cb(remote_name, remote_name_len):
    print('\n\n\n\n\nIn python: callback executed: %s.\n\n\n\n\n'%(remote_name))

pa = peer('peer_a', None, 'hello')
pb = peer('peer_a', None, 'hello')
print("Peer created")
pa.set_verbose()
pb.set_verbose()
time.sleep(1)
# pa.on_connect(None, on_connect_cb)
# pb.on_connect(None, on_connect_cb)
print('On connect error: %d'%(pa.errno()))
print('Set verbose')
print('\n\nPA start: %d\n\n'%(pa.start()))
time.sleep(0.1)
print('\n\nPB start: %d\n\n'%(pb.start()))
print('Start')
print(pa.list_connected())
time.sleep(4)
print('Destroy')
del pa
del pb

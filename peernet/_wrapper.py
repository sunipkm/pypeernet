from __future__ import annotations
from ctypes import c_char
from ._base import *

class peer:
    _lib = lib # ctypes lib
    _peer_by_handle = {}
    def __init__(self, name: str, group: str | None, password: str, encryption: bool = True):
        # validate name, group, password here
        if isinstance(group, str):
            _group = group.encode('utf-8')
        elif group is None:
            _group = c_char_p(0)
        self._peer_ptr = peer._lib.peer_new(name.encode('utf-8'), _group, password.encode('utf-8'), encryption)
        if (self._peer_ptr is None or self._peer_ptr == 0):
            raise RuntimeError("Could not create an instance of peer")
        self._handle = cast(self._peer_ptr, POINTER(c_void_p))
        peer._peer_by_handle[self._peer_ptr] = self
        self._on_connect_cbs = {}
        self._on_exit_cbs = {}
        self._on_evasive_cbs = {}
        self._on_silent_cbs = {}
        self._on_message_cbs = {}
    
    def set_verbose(self):
        peer._lib.peer_set_verbose(self._handle)

    def start(self) -> int:
        peer._lib.peer_start(self._handle)

    def list_connected(self) -> dict:
        void_ptr = peer._lib.peer_py_list_connected(self._handle)
        out = cast(void_ptr, c_char_p)
        out = out.value.decode('utf-8')
        outmap = {}
        ufouts = out.split(',')
        for uf in ufouts:
            ws = uf.split(':')
            outmap[ws[0]] = ws[1]
        return outmap

    def errno(self) -> int:
        return peer._lib.peer_py_errno(self._handle)

    def on_connect(self, name: str | None, fcn) -> int:
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            key = _peer
        elif name is None:
            key = "ALL"
            _peer = c_char_p(0)
        py_fcn = LIBPEER_CALLBACK_FUNC_TYPE(fcn)
        self._on_connect_cbs[key] = py_fcn
        ret = peer._lib.peer_py_on_connect(self._handle, _peer, py_fcn)
        return ret

    def disable_on_connect(self, name: str | None) -> int:
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            key = _peer
        elif name is None:
            key = "ALL"
            _peer = c_char_p(0)
        ret = peer._lib.peer_py_disable_on_connect(self._handle, _peer)
        if key in self._on_connect_cbs.keys():
            del self._on_connect_cbs[key]
        return ret # raise RTE?

    def __del__(self):
        peer._lib.peer_py_destroy(byref(self._handle))
        del peer._peer_by_handle[self._peer_ptr]
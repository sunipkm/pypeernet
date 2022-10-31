from __future__ import annotations
from ctypes import c_char, c_uint8
from ._base import *
from weakref import ProxyType, proxy

class peer:
    """Python wrapper around PeerNet::peer class.

    Provides local P2P networking between uniquely named peers,
    using a callback-based interface.
    
    """
    _peer_by_handle = {}

    @staticmethod
    def apiversion()->str:
        """Get version of PeerNet backend.

        Returns:
            str: Version in major.minor.patch format.
        """
        ver_num = lib.peer_version()
        patch = ver_num % 100
        ver_num = ver_num // 100
        minor = ver_num % 100
        major = ver_num // 100
        return '%d.%d.%d'%(major, minor, patch)

    @staticmethod
    def version(api='c')->str:
        """Get version of PyPeerNet or PeerNet backend.

        Args:
            api (str, optional): API of which version is requested. Can be 'py' or 'c'. Defaults to 'c'.

        Raises:
            RuntimeError: Invalid query string.

        Returns:
            str: Version string in major.minor.patch format.
        """
        if api not in ['py', 'c']:
            raise RuntimeError('%s is not a valid query string.'%(api))
        if api == 'py':
            return '2.0.0'
        elif api == 'c':
            return peer.apiversion()

    @staticmethod
    def voidptr_to_str(ptr: int | None)->str:
        """Get string from a void pointer.

        Args:
            ptr (int | None): Void pointer

        Raises:
            RuntimeError: Typecast failed.

        Returns:
            str: String at pointer.
        """
        if ptr is None:
            return ''
        elif isinstance(ptr, int):
            if ptr == 0:
                return ''
            out = cast(ptr, c_char_p)
            out = out.value.decode('utf-8')
            return out
        else:
            raise RuntimeError('Unknown ptr: %s'%(str(ptr)))

    @staticmethod
    def from_handle(ptr: int)->ProxyType:
        """Return weakref proxy to peer object from handle.

        Args:
            ptr (int): Handle to internal peer object

        Returns:
            ProxyType: weakref proxy to peer object.
        """
        if ptr not in peer._peer_by_handle.keys():
            return None
        else:
            return proxy(peer._peer_by_handle[ptr])

    def __init__(self, name: str, group: str | None, password: str, encryption: bool = True):
        """Create a new instance of a peer.

        Args:
            name (str): Peer unique name.
            group (str | None): Peer group. None for default group.
            password (str): Password string that every peer in this group authenticates to.
            encryption (bool, optional): Enable encryption. Defaults to True.

        Raises:
            RuntimeError: Invalid name.
            RuntimeError: Invalid group.
            RuntimeError: Failed to create peer instance.
        """
        self._name = None # this is here to prevent calling the C function many times
        # validate name, group, password here
        rc = lib.peer_py_validate_name(name.encode('utf-8'))
        if rc:
            raise RuntimeError('%s is not a valid name: %s (%d)'%(name, self.strerror(rc)), -rc)
        if isinstance(group, str):
            _group = group.encode('utf-8')
            rc = lib.peer_py_validate_group(_group)
            if rc:
                raise RuntimeError('%s is not a group: % (%d)'%(str(group), self.strerror(rc), -rc))
        elif group is None:
            _group = c_char_p(0)
        # create C instance of peer
        self._peer_ptr = lib.peer_new(name.encode('utf-8'), _group, password.encode('utf-8'), encryption)
        if (self._peer_ptr is None or self._peer_ptr == 0):
            raise RuntimeError("Could not create an instance of peer.")
        # create handle to pass to functions
        self._handle = cast(self._peer_ptr, POINTER(c_void_p))
        # create self ref by handle ptr
        peer._peer_by_handle[self._peer_ptr] = self
        self._name = self.name()
        # map of registered callbacks in order to prevent objects from being garbage collected.
        self._on_connect_cbs = {}
        self._on_exit_cbs = {}
        self._on_evasive_cbs = {}
        self._on_silent_cbs = {}
        self._on_message_cbs = {}

    def __del__(self):
        lib.peer_py_destroy(byref(self._handle))
        del peer._peer_by_handle[self._peer_ptr]
        del self._on_connect_cbs
        del self._on_exit_cbs
        del self._on_evasive_cbs
        del self._on_silent_cbs
        del self._on_message_cbs 

    def strerror(self, status: int) -> str:
        """Get error string corresponding to peer status code.

        Args:
            status (int): Status code.

        Returns:
            str: Status description.
        """
        out = lib.peer_strerror(status).decode('utf-8')
        return out
    
    def set_verbose(self):
        """Enable verbose mode for the peer.

        Raises:
            RuntimeError: Invalid handle.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        lib.peer_set_verbose(self._handle)

    def name(self)->str:
        """Return name of this peer.

        Raises:
            RuntimeError: Invalid handle.

        Returns:
            str: Name of the peer.
        """
        if self._name is not None:
            return self._name
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        self._name = lib.peer_name(self._handle).decode('utf-8')
        return self._name
        
    def start(self):
        """Start the peer.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Failed to start peer.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        rc = lib.peer_start(self._handle)
        if rc:
            raise RuntimeError('Could not start peer %s: Error %s (%d)'%(self.name(), self.strerror(rc), -rc))
        
    def list_connected(self) -> dict:
        """Get list of all connected peers.

        Raises:
            RuntimeError: Invalid handle.

        Returns:
            dict: name:uuid map of connected peers.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        ptr = lib.peer_py_list_connected(self._handle)
        out = peer.voidptr_to_str(ptr)
        outmap = {}
        ufouts = out.split(',')
        for uf in ufouts:
            ws = uf.split(':')
            outmap[ws[0]] = ws[1]
        return outmap

    def errno(self) -> int:
        """Get internal error status from peer.

        Raises:
            RuntimeError: Invalid handle.

        Returns:
            int: Status code.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        return lib.peer_py_errno(self._handle)

    def on_connect(self, name: str | None, fcn : function | LIBPEER_CALLBACK_FUNC_TYPE):
        """Register callback function to execute when remote peer connects.

        Args:
            name (str | None): Peer name, or None for all peers.
            fcn (function | LIBPEER_CALLBACK_FUNC_TYPE): Callback function of with argtype: handle, c_char_p (message_type), c_size_t (message_type_len), c_char_p (remote_name), c_size_t (remote_name_len), c_void_p (remote_data), c_size_t (remote_data_len) 

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid remote peer name.
            RuntimeError: Could not register callback.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not register on connect callback for %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
            key = name.upper()
        elif name is None:
            key = "ALL"
            _peer = c_char_p(0)
        else:
            raise RuntimeError('Invalid type for name.')
        py_fcn = LIBPEER_CALLBACK_FUNC_TYPE(fcn)
        ret = lib.peer_py_on_connect(self._handle, _peer, py_fcn)
        if ret:
            errno = self.errno()
            raise RuntimeError('%s> Could not register on connect callback for %s: Error %s (%d)'%(self.name(), key, self.strerror(errno), -errno))
        self._on_connect_cbs[key] = py_fcn

    def disable_on_connect(self, name: str | None):
        """Deregister callback function executed when remote peer connects.

        Args:
            name (str | None): Peer name, or None for all peers.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid remote peer name.
            RuntimeError: Could not deregister callback.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not deregister on connect callback for %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
            key = name.upper()
        elif name is None:
            key = "ALL"
            _peer = c_char_p(0)
        else:
            raise RuntimeError('Invalid type for name.')
        ret = lib.peer_py_disable_on_connect(self._handle, _peer)
        if ret:
            errno = self.errno()
            raise RuntimeError('%s> Could not deregister on connect callback for %s: Error %s (%d)'%(self.name(), key, self.strerror(errno), -errno))
        if key in self._on_connect_cbs.keys():
            del self._on_connect_cbs[key]

    def on_disconnect(self, name: str | None, fcn):
        """Register callback function to execute when remote peer disconnects.

        Args:
            name (str | None): Peer name, or None for all peers.
            fcn (function | LIBPEER_CALLBACK_FUNC_TYPE): Callback function of with argtype: handle, c_char_p (message_type), c_size_t (message_type_len), c_char_p (remote_name), c_size_t (remote_name_len), c_void_p (remote_data), c_size_t (remote_data_len) 

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid remote peer name.
            RuntimeError: Could not register callback.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not register on disconnect callback for %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
            key = name.upper()
        elif name is None:
            key = "ALL"
            _peer = c_char_p(0)
        else:
            raise RuntimeError('Invalid type for name.')
        py_fcn = LIBPEER_CALLBACK_FUNC_TYPE(fcn)
        ret = lib.peer_py_on_disconnect(self._handle, _peer, py_fcn)
        if ret:
            errno = self.errno()
            raise RuntimeError('%s> Could not register on disconnect callback for %s: Error %s (%d)'%(self.name(), key, self.strerror(errno), -errno))
        self._on_exit_cbs[key] = py_fcn

    def disable_on_connect(self, name: str | None):
        """Deregister callback function executed when remote peer disconnects.

        Args:
            name (str | None): Peer name, or None for all peers.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid remote peer name.
            RuntimeError: Could not deregister callback.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not deregister on disconnect callback for %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
            key = name.upper()
        elif name is None:
            key = "ALL"
            _peer = c_char_p(0)
        else:
            raise RuntimeError('Invalid type for name.')
        ret = lib.peer_py_disable_on_disconnect(self._handle, _peer)
        if ret:
            errno = self.errno()
            raise RuntimeError('%s> Could not deregister on disconnect callback for %s: Error %s (%d)'%(self.name(), key, self.strerror(errno), -errno))
        if key in self._on_exit_cbs.keys():
            del self._on_exit_cbs[key]

    def on_evasive(self, name: str | None, fcn):
        """Register callback function to execute when remote peer is evasive.

        Args:
            name (str | None): Peer name, or None for all peers.
            fcn (function | LIBPEER_CALLBACK_FUNC_TYPE): Callback function of with argtype: handle, c_char_p (message_type), c_size_t (message_type_len), c_char_p (remote_name), c_size_t (remote_name_len), c_void_p (remote_data), c_size_t (remote_data_len) 

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid remote peer name.
            RuntimeError: Could not register callback.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not register on evasive callback for %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
            key = name.upper()
        elif name is None:
            key = "ALL"
            _peer = c_char_p(0)
        else:
            raise RuntimeError('Invalid type for name.')
        py_fcn = LIBPEER_CALLBACK_FUNC_TYPE(fcn)
        ret = lib.peer_py_on_connect(self._handle, _peer, py_fcn)
        if ret:
            errno = self.errno()
            raise RuntimeError('%s> Could not register on evasive callback for %s: Error %s (%d)'%(self.name(), key, self.strerror(errno), -errno))
        self._on_evasive_cbs[key] = py_fcn

    def disable_on_evasive(self, name: str | None):
        """Deregister callback function executed when remote peer is evasive.

        Args:
            name (str | None): Peer name, or None for all peers.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid remote peer name.
            RuntimeError: Could not deregister callback.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not deregister on evasive callback for %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
            key = name.upper()
        elif name is None:
            key = "ALL"
            _peer = c_char_p(0)
        else:
            raise RuntimeError('Invalid type for name.')
        ret = lib.peer_py_disable_on_connect(self._handle, _peer)
        if ret:
            errno = self.errno()
            raise RuntimeError('%s> Could not deregister on evasive callback for %s: Error %s (%d)'%(self.name(), key, self.strerror(errno), -errno))
        if key in self._on_evasive_cbs.keys():
            del self._on_evasive_cbs[key]

    def on_silent(self, name: str | None, fcn):
        """Register callback function to execute when remote peer is silent.

        Args:
            name (str | None): Peer name, or None for all peers.
            fcn (function | LIBPEER_CALLBACK_FUNC_TYPE): Callback function of with argtype: handle, c_char_p (message_type), c_size_t (message_type_len), c_char_p (remote_name), c_size_t (remote_name_len), c_void_p (remote_data), c_size_t (remote_data_len) 

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid remote peer name.
            RuntimeError: Could not register callback.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not register on silent callback for %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
            key = name.upper()
        elif name is None:
            key = "ALL"
            _peer = c_char_p(0)
        else:
            raise RuntimeError('Invalid type for name.')
        py_fcn = LIBPEER_CALLBACK_FUNC_TYPE(fcn)
        ret = lib.peer_py_on_connect(self._handle, _peer, py_fcn)
        if ret:
            errno = self.errno()
            raise RuntimeError('%s> Could not register on silent callback for %s: Error %s (%d)'%(self.name(), key, self.strerror(errno), -errno))
        self._on_silent_cbs[key] = py_fcn

    def disable_on_silent(self, name: str | None):
        """Deregister callback function executed when remote peer is silent.

        Args:
            name (str | None): Peer name, or None for all peers.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid remote peer name.
            RuntimeError: Could not deregister callback.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not deregister on silent callback for %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
            key = name.upper()
        elif name is None:
            key = "ALL"
            _peer = c_char_p(0)
        else:
            raise RuntimeError('Invalid type for name.')
        ret = lib.peer_py_disable_on_connect(self._handle, _peer)
        if ret:
            errno = self.errno()
            raise RuntimeError('%s> Could not deregister on silent callback for %s: Error %s (%d)'%(self.name(), key, self.strerror(errno), -errno))
        if key in self._on_silent_cbs.keys():
            del self._on_silent_cbs[key]

    def on_message(self, name: str, message_type: str, fcn):
        """Register callback function to execute when remote peer connects.

        Args:
            name (str): Peer name.
            message_type (str): Message type from peer.
            fcn (function | LIBPEER_CALLBACK_FUNC_TYPE): Callback function of with argtype: handle, c_char_p (message_type), c_size_t (message_type_len), c_char_p (remote_name), c_size_t (remote_name_len), c_void_p (remote_data), c_size_t (remote_data_len) 

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid remote peer name.
            RuntimeError: Invalid message type.
            RuntimeError: Could not register callback.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not register on message callback for %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
            key_name = name.upper()
        else:
            raise RuntimeError('Invalid type for name.')
        if isinstance(message_type, str):
            _message_type = message_type.encode('utf-8')
            rc = lib.peer_py_validate_message_type(_message_type)
            if rc:
                raise RuntimeError('%s> Could not register on message callback for %s: Error %s (%d)'%(self.name(), message_type, self.strerror(rc), -rc))
            key_message = message_type.upper()
        else:
            raise RuntimeError('Invalid type for message type.')

        py_fcn = LIBPEER_CALLBACK_FUNC_TYPE(fcn)
        self._on_message_cbs['%s.%s'%(key_message, key_name)] = py_fcn
        ret = lib.peer_py_on_message(self._handle, _peer, _message_type, py_fcn)
        if ret:
            errno = self.errno()
            raise RuntimeError('%s> Could not register on connect callback for %s: Error %s (%d)'%(self.name(), key_name, self.strerror(errno), -errno))

    def disable_on_message(self, name: str, message_type: str):
        """Deregister callback function executed when remote peer connects.

        Args:
            name (str | None): Peer name, or None for all peers.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid remote peer name.
            RuntimeError: Could not deregister callback.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not register on message callback for %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
            key_name = name.upper()
        else:
            raise RuntimeError('Invalid type for name.')
        if isinstance(message_type, str):
            _message_type = message_type.encode('utf-8')
            rc = lib.peer_py_validate_message_type(_message_type)
            if rc:
                raise RuntimeError('%s> Could not register on message callback for %s: Error %s (%d)'%(self.name(), message_type, self.strerror(rc), -rc))
            key_message = message_type.upper()
        else:
            raise RuntimeError('Invalid type for message type.')
        ret = lib.peer_py_disable_on_message(self._handle, _peer, _message_type)
        if ret:
            errno = self.errno()
            raise RuntimeError('%s> Could not deregister on connect callback for %s: Error %s (%d)'%(self.name(), key_name, self.strerror(errno), -errno))
        final_key = '%s.%s'%(key_message, key_name)
        if final_key in self._on_connect_cbs.keys():
            del self._on_connect_cbs[final_key]

    def silent_eviction_enabled(self)->bool:
        """Check if this peer requests silent peers to leave the network.

        Raises:
            RuntimeError: Invalid handle.

        Returns:
            bool: Enable status.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        ret = lib.peer_silent_eviction_enabled(self._handle)
        return ret

    def set_silent_eviction(self, enable: bool):
        """Enable/disable silent eviction.

        Args:
            enable (bool): True to enable, False to disable.

        Raises:
            RuntimeError: Invalid handle.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        lib.peer_set_silent_eviction(self._handle, enable)

    def get_receiver_status(self, timeout_ms: int)->int:
        """Get message from internal receiver.

        Args:
            timeout_ms (int): Time to block until a message appears. Set to -1 to block forever.

        Raises:
            RuntimeError: Invalid handle.

        Returns:
            int: Status code.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        rc = lib.peer_get_receiver_messages(self._handle, timeout_ms)
        return rc

    def exists(self, name: str)->bool:
        """Check if remote peer is connected.

        Args:
            name (str): Remote peer name.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid name.

        Returns:
            bool: True if connected, else False.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Invalid name %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
        else:
            raise RuntimeError('Invalid type for name.')
        rc = lib.peer_exists(self._handle, _peer)
        return rc

    def set_port(self, port: int):
        """Set network discovery port for the peer (hence the group.)

        Args:
            port (int): Peer port, between 1000 and 65535.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid port.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        rc = lib.peer_set_port(self._handle, port)
        if rc:
            raise RuntimeError('%s> Could not set port %d: Error %s (%d)'%(self.name(), port, self.strerror(rc), -rc))

    def set_evasive_retry_count(self, retry_count: int):
        """Set connection retry count for evasive peers before they are requested to exit.

        Args:
            retry_count (int): -1 to disable.

        Raises:
            RuntimeError: Invalid handle.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        lib.peer_set_evasive_retry_count(self._handle, retry_count)

    def set_interface(self, iface: str):
        """Set the network interface for UDP beacons. If you do not set this, CZMQ will choose an interface for you. On boxes with several interfaces, the interface should be specified or connection issues may occur. The interface may be specified either by the interface name (e.g. "eth0") or an IP address associated with the interface (e.g. "192.168.0.1").

        Args:
            iface (str): Interface name or local IP address on the interface.

        Raises:
            RuntimeError: Invalid handle.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        lib.peer_set_interface(self._handle, iface.encode('utf-8'))

    def set_interval(self, interval_ms: int):
        """Set UDP beacon discovery interval, in milliseconds. Default is instant beacon exploration followed by pinging every 1,000 ms.

        Args:
            interval_ms (int): Beacon discovery timeout in milliseconds.

        Raises:
            RuntimeError: Invalid handle.
            ValueError: Interval can not be negative.
            ValueError: Could not set port.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if interval_ms < 0:
            raise ValueError('Interval can not be negative.')
        rc = lib.peer_set_interval(self._handle, interval_ms)
        if rc:
            raise ValueError('%s> Could not set port %d: Error %s (%d)'%(self.name(), interval_ms, self.strerror(rc), -rc))

    def whisper(self, message_type: str, name: str, data: bytearray):
        """Whisper a raw message of message_type to remote peer.

        Args:
            message_type (str): Message type.
            name (str): Remote peer name.
            data (bytearray): Bytearray of data.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid name.
            RuntimeError: Invalid message type.
            RuntimeError: Whisper error.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not send message to %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
        else:
            raise RuntimeError('Invalid type for name.')
        if isinstance(message_type, str):
            _message_type = message_type.encode('utf-8')
            rc = lib.peer_py_validate_message_type(_message_type)
            if rc:
                raise RuntimeError('%s> Could not send message to %s: Error %s (%d)'%(self.name(), message_type, self.strerror(rc), -rc))
        else:
            raise RuntimeError('Invalid type for message type.')
        if data is None:
            _data = c_void_p(0)
            _datalen = 0
        else:
            rdata = c_uint8 * len(data)
            _data = rdata.from_buffer(data)
            _datalen = len(data)
        
        rc = lib.peer_whisper(self._handle, _peer, _message_type, _data, _datalen)
        if rc:
            raise RuntimeError('%s> Could not send message (%s) to %s: Error %s (%d)'%(self.name(), message_type, name, self.strerror(self.errno()), -self.errno()))

    def whispers(self, message_type: str, name: str, data: str):
        """Whisper a string message of message_type to remote peer.

        Args:
            message_type (str): Message type.
            name (str): Remote peer name.
            data (bytearray): Bytearray of data.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid name.
            RuntimeError: Invalid message type.
            RuntimeError: Whisper error.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not send message to %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
        else:
            raise RuntimeError('Invalid type for name.')
        if isinstance(message_type, str):
            _message_type = message_type.encode('utf-8')
            rc = lib.peer_py_validate_message_type(_message_type)
            if rc:
                raise RuntimeError('%s> Could not send message to %s: Error %s (%d)'%(self.name(), message_type, self.strerror(rc), -rc))
        else:
            raise RuntimeError('Invalid type for message type.')

        if len(data) == 0:
            raise RuntimeError('Empty message string.')
        
        rc = lib.peer_whispers(self._handle, _peer, _message_type, data.encode('utf-8'))
        if rc:
            raise RuntimeError('%s> Could not send message (%s) to %s: Error %s (%d)'%(self.name(), message_type, name, self.strerror(self.errno()), -self.errno()))

    def shout(self, message_type: str, data: bytearray):
        """Shout a raw message of message_type to group.

        Args:
            message_type (str): Message type.
            name (str): Remote peer name.
            data (bytearray): Bytearray of data.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid message type.
            RuntimeError: Shout error.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(message_type, str):
            _message_type = message_type.encode('utf-8')
            rc = lib.peer_py_validate_message_type(_message_type)
            if rc:
                raise RuntimeError('%s> Could not send message to %s: Error %s (%d)'%(self.name(), message_type, self.strerror(rc), -rc))
        else:
            raise RuntimeError('Invalid type for message type.')
        if data is None:
            _data = c_void_p(0)
            _datalen = 0
        else:
            rdata = c_uint8 * len(data)
            _data = rdata.from_buffer(data)
            _datalen = len(data)
        
        rc = lib.peer_shout(self._handle, _message_type, _data, _datalen)
        if rc:
            raise RuntimeError('%s> Could not send message (%s) to group: Error %s (%d)'%(self.name(), message_type, self.strerror(self.errno()), -self.errno()))

    def shouts(self, message_type: str, data: str):
        """Shout a string message of message_type to the group.

        Args:
            message_type (str): Message type.
            data (bytearray): Bytearray of data.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid message type.
            RuntimeError: Shout error.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(message_type, str):
            _message_type = message_type.encode('utf-8')
            rc = lib.peer_py_validate_message_type(_message_type)
            if rc:
                raise RuntimeError('%s> Could not send message to group: Error %s (%d)'%(self.name(), self.strerror(rc), -rc))
        else:
            raise RuntimeError('Invalid type for message type.')

        if len(data) == 0:
            raise RuntimeError('Empty message string.')
        
        rc = lib.peer_shouts(self._handle, _message_type, data.encode('utf-8'))
        if rc:
            raise RuntimeError('%s> Could not send message (%s) to group: Error %s (%d)'%(self.name(), message_type, self.strerror(self.errno()), -self.errno()))

    def get_remote_address(self, name: str)->str:
        """Get remote address of peer.

        Args:
            name (str): Peer name.

        Raises:
            RuntimeError: Invalid handle.
            RuntimeError: Invalid name.
            RuntimeError: Remote address could not be determined.

        Returns:
            str: Remote address of peer.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        if isinstance(name, str):
            _peer = name.encode('utf-8')
            rc = lib.peer_py_validate_name(_peer)
            if rc:
                raise RuntimeError('%s> Could not send message to %s: Error %s (%d)'%(self.name(), name, self.strerror(rc), -rc))
        ptr = lib.peer_get_remote_address(self._handle, _peer)
        out = peer.voidptr_to_str(ptr)
        if len(out) == 0:
            raise RuntimeError('%s> Could not get interface for %s: Error %s (%d)'%(self.name(), name, self.strerror(self.errno()), -self.errno()))
        return out

    def set_endpoint(self, name: str):
        """By default, PeerNet binds to an ephemeral TCP port and broadcasts the
        local host name using UDP beacons. When this method is called, PeerNet will
        use gossip discovery instead of UDP beacons. The gossip service MUST BE set
        up separately using {@link peer_gossip_bind} and {@link peer_gossip_connect}.
        Note that, the endpoint MUST be valid for both bind and connect operations.
        inproc://, ipc://, or tcp:// transports (for tcp://, use an IP address that is
        meaningful to remote as well as local peers). Returns 0 if the bind was
        successful, -1 otherwise.

        Args:
            name (str): Format string.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        rc = lib.peer_set_endpoint(self._handle, name.encode('utf-8'))
        if rc:
            raise RuntimeError('Could not set endpoint %s'%(name))
    
    def gossip_bind(self, name: str):
        """Set up gossip discovery of other peers. At least one peer in the cluster
        must bind to a well-known gossip endpoint, so that other peers can connect to it.
        Note that, gossip endpoints are completely distinct from PeerNet node endpoints,
        and should not overlap (they can use the same transport). For details of the
        gossip network design, see the CZMQ zgossip class.

        Args:
            name (str): Format string, followed by inputs.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        lib.peer_gossip_bind(self._handle, name.encode('utf-8'))

    def gossip_connect(self, name: str):
        """Set up gossip discovery of other peers. A peer may connect to multiple other
        peers, for redundancy paths. For details of the gossip network design, see the CZMQ
        zgossip class.

        Args:
            name (str): Format string, followed by inputs.
        """
        if self._handle is None:
            raise RuntimeError('Invalid handle.')
        lib.peer_gossip_connect(self._handle, name.encode('utf-8'))
     
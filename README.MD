# pyPeerNet: Python bindings for PeerNet 
pyPeerNet is a wrapper around the [PeerNet](https://github.com/sunipkm/peernet) library.

In PeerNet, a peer can belong to a unique group, and in that group peers can have
unique names. This allows for message parsing based on which peer it came from,
unlike Zyre which concerns more with UUIDs which are generated for peers randomly
at start.

## Ownership and License
PeerNet is developed by Sunip K. Mukherjee. This project uses the MPL v2 license, see LICENSE.
Contributions/ideas are welcome.

## Pre-requisites
This version of pyPeerNet is based off PeerNet v3.0.0. PeerNet, and its prerequisites are required
to use pyPeerNet. Refer to the [PeerNet readme](https://github.com/sunipkm/peernet/blob/master/README.MD)
to install PeerNet.

## Installation
After installing the pre-requisites, obtain pyPeerNet using git, and install:
```
    $ git clone https://github.com/sunipkm/pypeernet
    $ cd pypeernet
    $ pip install .
```

## The 'Chat' example
To run the example:
```
    $ cd examples/chat
    $ python chat.py <name>
```

In order to properly test the program, open another terminal in the `pypeernet` directory and repeat the steps above. Using the same `peer_name` as the first instance will cause the
second instance to crash. Multiple such instance can be launched in multiple terminal
windows, and writing anything in one such terminal, and pressing enter will cause the
instance to send the message to all other instances.

The example starts operation by importing the library, initializing the peer, and starting it:
```py
    from peernet import peer
    this = peer("peer_name", None, "password", True) # creates a peer named "peer_name" in the default group with password "password" and encryption enabled.
```
At this point, a pre-defined callback function is registered in order to capture any peer that has connected.
```py
    this.on_connect(None, on_connect_cb) # registers on_connect_callback as a callback for any peer that connects.
```

The `on_connect_cb()` function has the following form:
```py
    def on_connect_cb(handle: c_void_p, message_type: c_char_p, message_type_len: c_size_t, remote_name: c_char_p, remote_name_len: c_size_t, remote_data: c_void_p, remote_data_len: c_size_t):
        this: peer = peer.from_handle(handle) # returns the instance of peer that the callback was executed for
        this.on_message(remote_name.decode('utf-8'), "CHAT", on_message_cb) # registers a callback for message type "CHAT" from client of remote_name for this instance
```
Essentially, the `on_connect` callback that was registered, registers a callback function that is executed when any peer sends a message, of type "CHAT", to this peer. The `on_message` callback absolutely requires a peer name in order to avoid message spamming.

The `on_message_cb()` function has the following form:
```py
    def on_connect_cb(handle: c_void_p, message_type: c_char_p, message_type_len: c_size_t, remote_name: c_char_p, remote_name_len: c_size_t, remote_data: c_void_p, remote_data_len: c_size_t):
        this = peer.from_handle(handle) # returns the instance of peer that the callback was executed for
        message = peer.voidptr_to_str(remote_data) # get the string from remote data pointer
        print('\n\n%s> %s\n'%(remote_name.decode('utf-8'), message)) # print the message from the remote peer
```

The callback will be executed only for a message of type "CHAT". Since instances of `chat.py` are talking amongst one another, the message format sanity is guaranteed.

At this point, an instance of the peer can be started:
```py
    this.start()
```
A `while` loop can be run indefinitely until the input encounters a Ctrl + D which generates EOFError,
and messages can be read from `stdin`, and `shout` the message to all available `chat.py` clients:
```py
    while True:
        try:
            message = input('%s (Ctrl + D to exit)> '%(this.name()))
        except EOFError:
            break
        print()
        this.shouts("CHAT", message)
```
The peer can be stopped by deleting the instance after it is used:
```py
    del this
```

All in all, with 28 lines of code, a terminal chat client is implemented.


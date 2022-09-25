from peernet import peer
import sys

def on_message_cb(handle, message_type, message_type_len, remote_name, remote_name_len, remote_data, remote_data_len):
    message = peer.voidptr_to_str(remote_data)
    this: peer = peer.from_handle(handle)
    print('\n\n%s> %s\n\n%s (Ctrl + D to exit)> '%(remote_name.decode('utf-8'), message, this.name()), end = '')

def on_connect_cb(handle, message_type, message_type_len, remote_name, remote_name_len, remote_data, remote_data_len):
    p_instance: peer = peer.from_handle(handle)
    p_instance.on_message(remote_name.decode('utf-8'), "CHAT", on_message_cb)

if __name__ == '__main__':
    encrypt = False
    argc = len(sys.argv)
    if (argc < 2) or (argc > 3):
        print('Invocation: python %s <Peer name> [encryption]'%(sys.argv[0]))
    if argc == 3:
        encrypt = True
    print('PeerNet version: %s'%(peer.version()))
    this = peer(sys.argv[1], None, "password", encrypt)
    this.on_connect(None, on_connect_cb)
    this.start()
    while True:
        try:
            message = input('%s (Ctrl + D to exit)> '%(this.name()))
        except EOFError:
            break
        print()
        this.shouts("CHAT", message)
    print('Exiting...')
    del this
    
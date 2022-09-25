from peernet import peer
import sys

class LanChat(peer):
    def __init__(self, name: str, password: str = 'group_passwd'):
        super(LanChat, self).__init__(name, 'lanchat_local', password, True)
        self.do_on_connect()

    def do_on_message(self, name: str):
        def on_message_cb(handle, message_type, message_type_len, remote_name, remote_name_len, remote_data, remote_data_len):
            message = peer.voidptr_to_str(remote_data)
            print('\n\n%s> %s\n\n%s (Ctrl + D to exit)> '%(remote_name.decode('utf-8'), message, self.name()), end = '')
        self.on_message(name, "CHAT", on_message_cb)
    
    def do_on_connect(self):
        def on_connect_cb(handle, message_type, message_type_len, remote_name, remote_name_len, remote_data, remote_data_len):
            self.do_on_message(remote_name.decode('utf-8'))
        self.on_connect(None, on_connect_cb)

    def shout_msg(self, message: str):
        self.shouts("CHAT", message)

if __name__ == '__main__':
    encrypt = False
    argc = len(sys.argv)
    if (argc < 2) or (argc > 3):
        print('Invocation: python %s <Peer name> [encryption]'%(sys.argv[0]))
    if argc == 3:
        encrypt = True
    print('PeerNet version: %s'%(peer.version()))
    this = LanChat(sys.argv[1])
    this.start()
    while True:
        try:
            message = input('%s (Ctrl + D to exit)> '%(this.name()))
        except EOFError:
            break
        print()
        this.shout_msg(message)
    print('Exiting...')
    del this
    
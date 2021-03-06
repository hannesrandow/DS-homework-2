"""
This script handles all the actions the client can make and communicates with the server from the terminal.
"""

import pickle
from time import sleep

from sudoku.client.game_server_discovery import GameServerDiscovery
from sudoku.client.ic_update_link import ICUpdate_link
from sudoku.client.rpc_client import RpcClient
from sudoku.common import protocol
from sudoku.client.ic_update_link import ICUpdate_link
import threading


class ClientTerminal:
    def __init__(self):
        self.current_session = None
        self.client_specifier = "default"  # used by server to distinguish clients for matching up link backs
        self.update_link = None
        self.rpcClient = None
        self.ic_update_link = None

    def leave_session(self):
        self.rpcClient.call(protocol._REQ_LEAVE_SESSION)
        pass

    def update(self, user_action):
        """
        This method allows the user to make a change to the sudoku game.
        :param user_action: Contains the row and column where the user makes the change, as well as the new number.
        :param current_session: The session that the client is currently in.
        :return: The response from the server whether the update was correct or incorrect.
        """
        user_action = user_action.split(' ')
        if len(user_action) > 1:
            row = user_action[1]
            column = user_action[2]
            number = user_action[3]
            m = row + protocol._MSG_FIELD_SEP + column + protocol._MSG_FIELD_SEP + number
        else:
            m = protocol._INIT

        print 'sent update request'
        update_request = self.rpcClient.call(protocol._REQ_UPDATE_GAME + protocol._MSG_FIELD_SEP + m)
        return update_request

    def create_session(self, game_name, max_num_players):
        """
        This method allows the user to create a new session.
        :param game_name: The name that the session should have.
        :param max_num_players: The maximum number of players that can be in the session.
        :return: The created session, from the server.
        """
        new_session = self.rpcClient.call(protocol._REQ_CREATE_SESSION + protocol._MSG_FIELD_SEP +
                                        game_name + protocol._MSG_FIELD_SEP + max_num_players)

        # Let the pub/sub run as deamon thread
        t = threading.Thread(target=self.start_session_thread, args=(game_name,))
        t.daemon = True
        t.start()

        return new_session

    def start_session_thread(self, game_name):
        """
        Use this method to start the publish subscribe scenario for game updates as a deamon thread.
        :param game_name: Name of the game and also of the exchange
        :return: None
        """
        self.ic_update_link = ICUpdate_link(game_name)
        self.ic_update_link.latest_game = self.current_session
        return


    def get_current_sessions(self):
        """
        Allows the user to view all the sessions that are currently running on the server.
        """
        #get current sessions from server
        current_sessions = self.rpcClient.call(protocol._REQ_CURRENT_SESSIONS)
        # FIXME: use sth different (do not encode here) [without it it does not work on Windows]
        current_sessions = pickle.loads(current_sessions.encode("UTF-8"))

        #print current_sessions
        for session in current_sessions:
            print '-------------------- '
            print 'session name: ', session.game_name
            print 'session id: ', session.game_id
            a = [player.nickname for player in session.current_players]
            print 'members: ', a
            print 'max players: ', session.max_num_of_players
            print ' '

    def nickname(self, n):
        """
        Allows the user to specify a nickname/username for himself
        :param n: The desired nickname/username
        :return: None
        """
        # self.send_request(protocol._REQ_NICKNAME + protocol._MSG_FIELD_SEP + n)
        res = self.rpcClient.call(protocol._REQ_NICKNAME + protocol._MSG_FIELD_SEP + n)
        print(res)
        if res == protocol._RSP_OK:
            print("nickname accepted")
        else:
            print("nickname not accepted!") # TODO: print why not!
        return

    def connect(self, serv_addr='localhost'):
        """
        This method is called for the initial connect between the client and the server.
        :return: None
        """
        # self.send_request(protocol._REQ_INITIAL_CONNECT)
        try:
            self.rpcClient =RpcClient(serv_addr)
        except Exception as e:
            print('could not establish connected with the RabbitMQ server: %s' % e)
            exit(-1)

        res = self.rpcClient.call(protocol._REQ_INITIAL_CONNECT)
        if res == protocol._RSP_OK:
            print("connected successfuly!")
        else:
            print("some problem with connection!") # TODO: print why not!
        return

    def join_session(self, user_action):
        """
        This method allows the user to join one of the existing sessions.
        :param user_action: The id of the session the user wants to join
        :return: The session that the user joined, or a message saying that the session has reached its maximum
        number of players
        """
        session_id = user_action.split(' ')[1]
        rsp = self.rpcClient.call(protocol._REQ_JOIN_SESSION + protocol._MSG_FIELD_SEP + session_id)
        # TODO: use simpler output for the joining session (on server!)
        if rsp.startswith(protocol._ACK):
            return rsp
        elif rsp.startswith(protocol._RSP_SESSION_FULL):
            print 'session full'
        else:
            print 'UUID is not available'
        return

    def find_self(self):
        """
        Find the representation of the client in current players of the session.
        E.g. to get score.
        :return: The player instance in the current players of the session.
        """
        for p in self.current_session.current_players:
            if p.client_ip == self.socket.getsockname():
                return p

    def run(self):
        """
        This method processes all the user actions from the terminal.
        :return: None
        """
        print "client running.."

        user_action = raw_input('enter action preceded by -flag (or -help): ')
        if user_action.startswith('-username'):
            nickname = user_action.split(' ')[1]
            self.client_specifier = nickname
            self.nickname(nickname)
            print 'username created'
        elif user_action.startswith('-newsession'):
            user_input = user_action.split(' ')
            #self.current_session = self.create_session(user_input[1], user_input[2])
            if self.create_session(user_input[1], user_input[2]) == protocol._ACK:
                sleep(2)
                print 'sucess'
                self.update('-')
        elif user_action.startswith('-printsession'):
            #if not self.current_session:
            if self.current_session:
                for i in self.current_session.game_state:
                    print i
            else:
                print("no session exists!")
        elif user_action.startswith('-getsessions'):
            self.get_current_sessions()
        elif user_action.startswith('-update'):
            #self.current_session = self.update(user_action, self.current_session)
            print self.update(user_action)
        elif user_action.startswith('-solution'):
            inf = user_action.split(' ')
        elif user_action.startswith('-join'):
            rsp = self.join_session(user_action)
            if rsp is not None:
                game_name = rsp.split(protocol._MSG_FIELD_SEP)[1]
                t = threading.Thread(target=self.start_session_thread, args=(game_name,))
                t.daemon = True
                t.start()
                sleep(2)
                self.update('-')
        elif user_action.startswith('-score'):
            #score = self.current_session.current_players[0].score
            if self.current_session:
                score = self.find_self().score
                print 'my score is: ', score
            else: 
                print "currenty not in a session"
        # elif user_action.startswith('-sn'):
        #     print self.socket.getsockname()
        elif user_action.startswith('-leave'):
            self.leave_session()
        elif user_action.startswith('-help'):
            print 'help: \n' \
            '  -username <usr> \n' \
            '  -newsession <name> <max_player> \n' \
            '  -printsession, -getsessions \n' \
            '  -update <session_id> <row> <col> <val> \n' \
            '  -solution \n',
            '  -join <session_id> \n' \
            '  -score \n'
        elif user_action.startswith(protocol._TERMINATOR):
            self.send_request(protocol._TERMINATOR)

        elif user_action.startswith('test'):
            r = self.rpcClient.call(user_action)
            print r

    def stop(self):
        """
        Destroy the connection.
        :return: None
        """
        self.gameUpdateLink.destroy()
        self.socket.shutdown(2)
        self.socket.close()


def client_terminal_main(args=None):
    serv_addr = raw_input("Enter server address (or 'auto'): ")
    if serv_addr == 'auto':
        game_server_discovery = GameServerDiscovery()
        print("found: ", game_server_discovery.get_list())
        serv_addr = game_server_discovery.get_list().pop(0)
        game_server_discovery.stop()
    print("connecting to %s .." % serv_addr)

    client = ClientTerminal()
    client.connect(serv_addr)
    # FIXME: some considerations required for rabbitmq for remote ip connection: http://bit.ly/2z4lwZY

    while True:
        sleep(1)
        try:
            client.run()
        except KeyboardInterrupt as e:
            client.stop()
            print("terminated!")
            exit(-1)


if __name__ == '__main__':
    client_terminal_main()
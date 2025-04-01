import card
import socket
import random
import sys
import threading
import json

HOST = "0.0.0.0"
PORT = 46500
LISTEN = 8
BUFFER = 1024

class ServerReceiver:
    def __init__(self, sock : socket.socket) -> None:
        self._socket = sock
    def r(self) -> dict:
        return json.loads(self._socket.recv(BUFFER))

class Client:
    def __init__(self, sock : socket.socket) -> None:
        self._socket : socket.socket = sock
        self._name = ""
        self._preparedFlag = False
    def getSocket(self) -> socket.socket:
        return self._socket
    def getName(self) -> str:
        return self._name
    def setName(self, name : str) -> None:
        self._name = name
    def getPrepared(self) -> bool:
        return self._preparedFlag
    def setPrepared(self, flag : bool):
        self._preparedFlag = flag


class Server:
    _clients:dict[str|Client] = {}
    _clientsLock = threading.Lock()
    _cards = card.CardsUtil.generateCards()
    _cardsLock = threading.Lock()
    _startFlag = False
    _inPlayFlag = False
    def __init__(self, host : str, port : int, listen : int):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((host, port))
        self._socket.listen(listen)
        random.shuffle(self._cards)
    def _sendOut(self, d : bytes):
        with self._clientsLock:
            for c in self._clients.values():
                try:
                    c.getSocket().sendall(d)
                except:
                    pass
    def _talk(self, address : str):
        try:
            with self._clientsLock:
                client : Client = self._clients[address]
                s = client.getSocket()
                sr = ServerReceiver(s)
                d = sr.r()
                if d["t"] != "join": return
                client.setName(d["c"]["name"])
                s.sendall(json.dumps({"t" : "done"}).encode("utf-8"))
            while s.fileno() != -1:
                d = sr.r()
                sd = {}
                match d["t"]:
                    case "ping":
                        sd = {"t" : "pong"}
                    case "prepared":
                        client.setPrepared(True)
                        sd = {"t": "done"}
                    case "getPlayers":
                        with self._clientsLock:
                            sd = {"t": "response", "c":{"players":[c.getName() for c in self._clients]}}
                    case _:
                        pass
        finally:
            self._clients.pop(address)
    def matching(self):
        while True:
            s, a = self._socket.accept()
            with self._clientsLock:
                self._clients[a] = Client(s)
            threading.Thread(target=Server._talk, args=(self, s)).start()
    #def waitFlag(self):
    #    while True:
    #



def main():
    server = Server(HOST, PORT, LISTEN)
    threading.Thread(target=Server.matching, args=(server,))
    threading.Thread(target=Server.waitFlag, args=(server,))
    try:
        while 1!=2:
            pass
    except KeyboardInterrupt:
        sys.exit(0)
    except:
        sys.exit(1)

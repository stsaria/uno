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

class Client:
    def __init__(self, sock : socket.socket) -> None:
        self._socket : socket.socket = sock
        self._name = ""
        self._preparedFlag = False
        self._haveCards:list[card.Card] = []
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
    def getHaveCards(self) -> list[card.Card]:
        return self._haveCards
    def appendGetHaveCards(self, c : card.Card) -> None:
        self._haveCards.append(c)
    def removeHaveCards(self, c : card.Card) -> None:
        self._haveCards.remove(c)
    def containsHaveCards(self, c : card.Card) -> bool:
        for i in self._haveCards:
            if i.getName() == c.getName():
                return True
        return False
    def fileno(self) -> int:
        return self.getSocket().fileno()
    def send(self, d : dict):
        self.getSocket().sendall(json.dumps(d).encode("utf-8")) if self.fileno() != -1 else None
    def recv(self) -> dict:
        return json.loads(self._socket.recv(BUFFER))


class Server:
    _clients:dict[str|Client] = {}
    _clientsLock = threading.Lock()
    _restCards = card.CardsUtil.generateCards()
    _latestCard = None
    _cardsLock = threading.Lock()
    _startFlag = False
    _inPlayFlag = False
    def __init__(self, host : str, port : int, listen : int):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((host, port))
        self._socket.listen(listen)
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
                d = client.recv()
                if d["t"] != "join": return
                client.setName(d["c"]["name"])
                client.send({"t" : "done"})
            while client.fileno() != -1:
                d = client.recv()
                start = False
                sd = {}
                match d["t"]:
                    case "ping":
                        sd = {"t" : "pong"}
                    case "prepared":
                        client.setPrepared(True)
                        with self._clientsLock:
                            notPrepared = True
                            for c in self._clients:
                                if not c.getPrepared(): notPrepared = True
                            if not notPrepared: start = True
                        sd = {"t": "done"}
                    case "getPlayers":
                        with self._clientsLock:
                            sd = {"t": "response", "c":{"players":[c.getName() for c in self._clients]}}
                    case _:
                        pass
                client.send(sd)
                if start and not self._inPlayFlag: self._startFlag = True
        finally:
            self._clients.pop(address)
    def _start(self):
        self._startFlag = False
        with self._clientsLock and self._cardsLock:
            random.shuffle(self._restCards)
            for c in self._clients:
                c:Client = c
                for i in self._restCards[:7]:
                    c.appendGetHaveCards(i)
                    self._restCards.remove(i)
                    c.send({"t":"give", "c":{"cards":[i.getName() for i in c.getHaveCards()]}})
            while self._restCards[0].isSpecialCardType():
                random.shuffle(self._restCards)
        self._latestCard = self._restCards[0]
        self._restCards.remove(self._latestCard)
        self._inPlayFlag = True
    def matching(self):
        while True:
            s, a = self._socket.accept()
            with self._clientsLock:
                self._clients[a] = Client(s)
            threading.Thread(target=Server._talk, args=(self, s)).start()
    def waitingFlag(self):
        while True:
            if self._startFlag:
                self._start()

def main():
    server = Server(HOST, PORT, LISTEN)
    threading.Thread(target=Server.matching, args=(server,), daemon=True).start()
    threading.Thread(target=Server.waitingFlag, args=(server,), daemon=True).start()
    try:
        while 1!=2:
            pass
    except KeyboardInterrupt:
        print("keyboard interrupt stop(safe)")
        sys.exit(0)
    except:
        sys.exit(1)

if __name__ == "__main__":
    main()

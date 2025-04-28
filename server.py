import time

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

stop = False

class Client:
    _overDatas = []
    _point = 0
    def __init__(self, sock : socket.socket) -> None:
        self._socket : socket.socket = sock
        self._name = ""
        self._preparedFlag = False
        self._haveCards:list[card.Card] = []
    def getName(self) -> str:
        return self._name
    def setName(self, name : str) -> None:
        self._name = name
    def getPrepared(self) -> bool:
        return self._preparedFlag
    def setPrepared(self, flag : bool):
        self._preparedFlag = flag
    def getHaveCards(self) -> list[card.Card]:
        return self._haveCards.copy()
    def appendGetHaveCards(self, c : card.Card) -> None:
        self._haveCards.append(c)
    def removeHaveCards(self, c : card.Card) -> None:
        for hc in self._haveCards:
            if isinstance(hc, card.ColorSelectableCard) and isinstance(c, card.ColorSelectableCard):
                if hc.getCardType() == c.getCardType(): self._haveCards.remove(hc)
            elif hc == c:
                self._haveCards.remove(c)
    def containsHaveCards(self, c : card.Card) -> bool:
        for hc in self._haveCards:
            if hc.getName() == c.getName():
                return True
            elif isinstance(hc, card.ColorSelectableCard) and isinstance(c, card.ColorSelectableCard):
                if hc.getCardType() == c.getCardType(): return True
        return False
    def fileno(self) -> int:
        return self._socket.fileno()
    def send(self, d : dict):
        self._socket.sendall(json.dumps(d).encode("utf-8")) if self.fileno() != -1 else None
    def recv(self) -> dict|None:
        for data in self._overDatas:
            self._overDatas.remove(data)
            return data
        b = self._socket.recv(BUFFER)
        s = b.decode("utf-8")
        sS = s.split("}{")
        if len(sS) == 0:
            return None
        elif len(sS) == 1:
            try:
                return json.loads(sS[0])
            except:
                return {"t":"n"}
        else:
            dS:list[dict] = [json.loads(sS[0]+"}")]
            if len(sS) >= 3:
                for i in range(1,len(sS)-1):
                    dS.append(json.loads("{"+sS[i]+"}"))
            dS.append(json.loads("{"+sS[-1]))
            d = dS[0]
            dS.remove(d)
            self._overDatas += dS
            return d
    def close(self) -> None:
        self._socket.close()

class Server:
    _clients:dict[str:Client] = {}
    _clientsLock:threading.Lock = threading.Lock()
    _restCards:list[card.Card] = card.CardsUtil.generateCards()
    _tableCard:card.Card = None
    _tableCards:card.Card = None
    _nextPutCardClient:Client = None
    _cardsLock:threading.Lock = threading.Lock()
    _startFlag:bool = False
    _inPlayFlag:bool = False
    _reversed:bool = False
    _pulled:bool = False
    def __init__(self, host : str, port : int, listen : int):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((host, port))
        self._socket.listen(listen)
    def sockClose(self) -> None:
        try:
            self._socket.close()
        except:
            pass
    def _setNextClient(self, skip:bool=False) -> None:
        n = (len(list(self._clients.values()))
             +list(self._clients.values()).index(self._nextPutCardClient)
             +(-1 if self._reversed else 1))
        n += (-1 if self._reversed else 1) if skip else 0
        self._nextPutCardClient = (list(self._clients.values())*3)[n]
    def _sendOutAll(self, d : dict):
        for c in self._clients.values():
            c.send(d)
    def _winEnd(self, winner : Client):
        global stop
        with self._clientsLock:
            self._sendOutAll({"t":"end", "c":{"reason":"noMoreHisCard", "winner":winner.getName()}})
        stop = True
    def _noMoreRestCardEnd(self):
        global stop
        with self._clientsLock:
            sortedClients:list[Client] = sorted(self._clients, key=lambda c: c.getHaveCards())
            self._sendOutAll({"t":"end", "c":{"reason":"noMoreTableCard", "winner":sortedClients[0].getName()}})
        stop = True
    def _talk(self, address : str):
        try:
            with self._clientsLock:
                client : Client = self._clients[address]
            while client.fileno() != -1:
                d = client.recv()
                start = False
                sd = {}
                match d["t"]:
                    case "join":
                        with self._clientsLock:
                            if d["c"]["name"] in [i.getName() for i in self._clients.values()]:
                                sd = {"t":"nameUsed"}
                            else:
                                client.setName(d["c"]["name"])
                                sd = {"t": "done"}
                    case "ping":
                        client.send({"t" : "pong"})
                        continue
                    case "prepared":
                        client.setPrepared(True)
                        with (self._clientsLock):
                            prepares = []
                            for c in self._clients.values():
                                prepares.append(c.getPrepared())
                            if prepares == [True for _ in self._clients] and len(self._clients) >= 2: start = True
                        sd = {"t": "done"}
                    case "get":
                        with self._clientsLock:
                            sd = {"t": "response", "c":{"t":"clients", "clients":[c.getName() for c in self._clients.values()]}}
                    case "put":
                        with self._clientsLock:
                            if self._nextPutCardClient != client:
                                client.send({"t": "youNotPutter"})
                                continue
                        c = card.CardsUtil.findCardByCardName(client.getHaveCards(), d["c"]["card"])
                        if not c:
                            client.send({"t": "youDontHaveThisCard"})
                            continue
                        elif not card.CardsUtil.isCanPut(client.getHaveCards(), self._tableCard, c):
                            client.send({"t": "cantPutCard"})
                            continue
                        client.removeHaveCards(c)
                        self._tableCard = c
                        match c.getCardType():
                            case card.CardType.REVERSE:
                                self._reversed = (False if self._reversed else True)
                                with self._clientsLock:
                                    if len(self._clients) == 2:
                                        self._setNextClient(skip=True)
                                    else:
                                        self._setNextClient()
                            case card.CardType.SKIP:
                                self._setNextClient(skip=True)
                            case _:
                                self._setNextClient()
                        if len(client.getHaveCards()) == 0:
                            self._winEnd(client)

                        self._pulled = False
                        self._sendOutAll({"t": "update", "c":{"t": "tableCard", "card":self._tableCard.getName()}})
                        client.send({"t":"update", "c":{"t": "clientCards", "myCards":[c.getName() for c in client.getHaveCards()]}})
                        time.sleep(0.5)
                        drawPoint = 0
                        if self._tableCard.getCardType() == card.CardType.DRAW_TWO:
                            drawPoint = 2
                        elif self._tableCard.getCardType() == card.CardType.DRAW_FOUR:
                            drawPoint = 4
                        if drawPoint != 0:
                            if not len(self._restCards) > drawPoint:
                                self._noMoreRestCardEnd()
                            for i in range(drawPoint):
                                self._nextPutCardClient.appendGetHaveCards(self._restCards[len(self._restCards)-i-1])
                                self._restCards.pop(len(self._restCards)-i-1)
                            self._nextPutCardClient.send({"t":"update", "c":{"t": "clientCards", "myCards":[c.getName() for c in self._nextPutCardClient.getHaveCards()]}})
                            self._nextPutCardClient.send({"t":"draw"})
                        sd = {"t":"update", "c":{"t": "clientCards", "cardAmounts": {}}}
                        for i in self._clients.values():
                            sd["c"]["cardAmounts"][i.getName()] = len(i.getHaveCards())
                        self._sendOutAll(sd)
                        self._nextPutCardClient.send({"t": "youArePutter"})
                        with self._clientsLock:
                            [self._clients[k].send({"t": "nextPutter", "c":{"putter":self._nextPutCardClient.getName()}}) if self._nextPutCardClient != self._clients[k] else None for k in self._clients.keys()]
                        sd = {"t":"n"}
                    case "pull":
                        with self._clientsLock:
                            if self._nextPutCardClient != client:
                                client.send({"t": "youNotPutter"})
                                continue
                        if self._pulled:
                            client.send({"t": "cantPullItAgain"})
                            continue
                        c = self._restCards[0]
                        self._restCards.pop(0)
                        client.appendGetHaveCards(c)
                        client.send({"t":"done"})
                        sd = {"t":"update", "c":{"t": "clientCards", "cardAmounts": {}}}
                        for i in self._clients.values():
                            sd["c"]["cardAmounts"][i.getName()] = len(i.getHaveCards())
                        self._sendOutAll(sd)
                        client.send({"t":"update", "c":{"t": "clientCards", "myCards":[c.getName() for c in client.getHaveCards()]}})
                        sd = {"t": "youArePutter"}
                        self._pulled = True
                    case "pass":
                        with self._clientsLock:
                            if self._nextPutCardClient != client:
                                client.send({"t": "youNotPutter"})
                                continue
                        if not self._pulled:
                            client.send({"t": "cantPass"})
                            continue
                        self._setNextClient()
                        self._nextPutCardClient.send({"t": "youArePutter"})
                        with self._clientsLock:
                            [self._clients[k].send({"t": "nextPutter", "c":{"putter":self._nextPutCardClient.getName()}}) if self._nextPutCardClient != self._clients[k] else None for k in self._clients.keys()]
                        self._pulled = False
                        sd = {"t": "done"}
                    case _:
                        pass
                client.send(sd)
                if start and not self._inPlayFlag: self._startFlag = True
        finally:
            try: self._clients.pop(address)
            except: pass
            client.close()
    def _start(self):
        self._startFlag = False
        with self._clientsLock and self._cardsLock:
            random.shuffle(self._restCards)
            for c in self._clients.values():
                for i in self._restCards[:7]:
                    c.appendGetHaveCards(i)
                    self._restCards.remove(i)
            for c in self._clients.values():
                sd = {"t":"update", "c":{"t": "clientCards", "myCards":[i.getName() for i in c.getHaveCards()], "cardAmounts": {}}}
                for i in self._clients.values():
                    sd["c"]["cardAmounts"][i.getName()] = len(i.getHaveCards())
                c.send(sd)
            while self._restCards[0].isSpecialCardType():
                random.shuffle(self._restCards)
            self._tableCard = self._restCards[0]
            self._restCards.remove(self._tableCard)
            self._sendOutAll({"t": "update", "c":{"t": "tableCard", "card":self._tableCard.getName()}})
            time.sleep(0.5)
            self._inPlayFlag = True
            time.sleep(0.5)
            self._nextPutCardClient = random.choice(list(self._clients.values()))
            [self._clients[k].send({"t": "nextPutter", "c":{"putter":self._nextPutCardClient.getName()}}) if self._nextPutCardClient != c else None for k in self._clients.keys()]
            self._nextPutCardClient.send({"t": "youArePutter"})
    def matching(self):
        while True:
            try:
                s, a = self._socket.accept()
            except:
                continue
            if self._inPlayFlag: continue
            with self._clientsLock:
                self._clients[a] = Client(s)
            threading.Thread(target=Server._talk, args=(self, a)).start()
    def waitingFlag(self):
        while True:
            if self._startFlag:
                self._start()

def main():
    global stop
    while True:
        try:
            server = Server(HOST, PORT, LISTEN)
            print("STARTED SERVER")
            break
        except:
            pass
    threading.Thread(target=Server.matching, args=(server,), daemon=True).start()
    threading.Thread(target=Server.waitingFlag, args=(server,), daemon=True).start()
    try:
        while not stop:
            pass
    except KeyboardInterrupt:
        print("keyboard interrupt stop(safe)")
        server.sockClose()
        sys.exit(0)
    except:
        sys.exit(1)

if __name__ == "__main__":
    main()

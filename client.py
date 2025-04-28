import threading

import card
import socket
import json
import sys
import typing

BUFFER = 1024
DELAY_PING = 0.5
DELAY_RECV = 0.2

stop = False

class Server:
    _overDatas = []
    def __init__(self, s:socket.socket) -> None:
        self._socket = s
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
            dS:list[dict] = [json.loads(sS[0] + "}")]
            dEnd = json.loads("{" + sS[-1])
            sS.pop(0)
            sS.pop(-1)
            if len(sS) >= 3:
                for ds in sS:
                    d = json.loads("{"+ds+"}")
                    if d["t"] == "pong":
                        continue
                    dS.append(json.loads("{"+ds+"}"))
            dS.append(dEnd)
            d = dS[0]
            dS.remove(d)
            self._overDatas += dS
            return d
    def send(self, d:dict) -> None:
        self._socket.sendall(json.dumps(d).encode("utf-8"))
    def fileno(self) -> int:
        return self._socket.fileno()

class Client:
    _myCards:list[card.Card] = None
    _cardAmounts:dict[str:int] = None
    _tableCard:card.Card = None
    _tableCards:list[card.Card] = None
    _pulled:bool = False
    _putColorSelectableCard:card.ColorSelectableCard|None = None
    def __init__(self, host : str, port : int, name : str) -> None:
        self._name = name
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((host, port))
    @staticmethod
    def inputAndExec(text : str, func : typing.Callable[[str], None]):
        func(input(text))
    def _ready(self, _):
        server = Server(self._socket)
        server.send({"t": "prepared"})
    def _action(self, a:str):
        server = Server(self._socket)
        if a.isdigit():
            if self._putColorSelectableCard:
                try:
                    putCard = self._putColorSelectableCard
                    match int(a):
                        case 0:
                            color = card.Color.RED
                        case 1:
                            color = card.Color.BLUE
                        case 2:
                            color = card.Color.GREEN
                        case 3:
                            color = card.Color.YELLOW
                        case _:
                            print("意味不明な色です。")
                            raise Exception
                    self._putColorSelectableCard = None
                    putCard.setSelectedColor(color)
                    server.send({"t": "put", "c":{"card":putCard.getName()}})
                    return
                except:
                    pass
            elif int(a) >= len(self._myCards):
                print("入力した数字はカードの範囲を超えています。")
            elif not card.CardsUtil.isCanPut(self._myCards, self._tableCard, self._myCards[int(a)]):
                print("そのカードは出せません。")
            elif isinstance(self._myCards[int(a)], card.ColorSelectableCard):
                self._putColorSelectableCard = self._myCards[int(a)]
                self.inputAndExec("赤:0\n青:1\n緑:2\n黄:3\nこのカードは色選択カードです。カードの色を選択してください: ", self._action)
                return
            else:
                server.send({"t": "put", "c":{"card":self._myCards[int(a)].getName()}})
                self._pulled = False
                return
            self.inputAndExec(": ", self._action)
            return
        match a:
            case "a":
                if self._pulled:
                    print("二度引くことはできません。カードを出すか、パスしてください。")
                else:
                    server.send({"t":"pull"})
                    self._pulled = True
                    return
            case "c":
                if not self._pulled:
                    print("まだカードを引いていない場合は、パスすることはできません。")
                else:
                    server.send({"t":"pass"})
                    self._pulled = False
                    return
        self.inputAndExec(": ", self._action)
    def _receivedDataProcess(self, d:dict):
        global stop
        match d["t"]:
            case "update":
                match d["c"]["t"]:
                    case "clientCards":
                        self._myCards = [card.CardUtil.cardNameToCard(n) for n in d["c"]["myCards"]] if "myCards" in d["c"].keys() else self._myCards
                        self._cardAmounts = d["c"]["cardAmounts"] if "cardAmounts" in d["c"].keys() else self._cardAmounts
                    case "tableCard":
                        self._tableCards = None
                        self._tableCard = card.CardUtil.cardNameToCard(d["c"]["card"])
                print("\033[2J---- 更新 ----")
                if self._cardAmounts:
                    print("~~ 他の人のカード枚数 ~~")
                    for n in self._cardAmounts.keys():
                        if n == self._name: continue
                        print(f"{n}: {self._cardAmounts[n]}")
                if self._myCards:
                    print("~~ あなたのカード ~~")
                    i = 0
                    for c in self._myCards:
                        print(f"{i} -> {card.CardUtil.cardToCasualName(c)}")
                        i += 1
                if self._tableCard:
                    print(f"テーブルのカード: {card.CardUtil.cardToCasualName(self._tableCard)}")
            case "youArePutter":
                if self._pulled:
                    self.inputAndExec("カード番号または、cを入力して自分の番をスキップしてください: ", self._action)
                else:
                    print("次はあなたの番です")
                    print("カードを出すか、出したくない・出せない場合はカードを引いてください。カードを引く場合は\"a\"と入力して進んでください。")
                    self.inputAndExec("カード番号または、アルファベットの特殊進行文字で進んでください: ", self._action)
            case "nextPutter":
                print("次は"+d["c"]["putter"]+"さんの番です。")
            case "draw":
                print(f"※あなたはドローを受けたので、{2 if self._tableCard.getCardType() == card.CardType.DRAW_TWO else 4}枚のカードが追加されました。")
            case "end":
                print(("\n"*15)+"ゲーム終了！")
                if d["c"]["winner"] == self._name:
                    print("あなたの勝ちです！！")
                else:
                    print(d["c"]["winner"]+"さんの勝ちです！")
                if d["c"]["reason"] == "noMoreHisCard":
                    print("手札がなくなりました！")
                elif d["c"]["reason"] == "noMoreTableCard":
                    print("テーブルのカードが全てなくなりました！")
                stop = True
            case "done":
                print("完了しました。")
    def talk(self) -> None:
        global stop
        server = Server(self._socket)
        server.send({"t": "join", "c":{"name":self._name}})
        while server.fileno() != -1:
            d = server.recv()
            match d["t"]:
                case "nameUsed":
                    print("cant join (name used)")
                    stop = True
                    return
                case "done":
                    print("join server")
                    self.inputAndExec("エンターを押して準備完了にしてください: ", self._ready)
                    break
        while server.fileno() != -1 and not stop:
            self._receivedDataProcess(server.recv())

def main():
    global stop
    print("UNO Client\n")
    host:str = input("Host: ")
    port:int = int(input("Port: "))
    name:str = input("UserName: ")
    client = Client(host, port, name)
    threading.Thread(target=Client.talk, args=(client,), daemon=True).start()
    try:
        while 1!=2:
            if stop:
                sys.exit(0)
    except KeyboardInterrupt:
        print("keyboard interrupt stop(safe)")
        sys.exit(0)

if __name__ == "__main__":
    main()
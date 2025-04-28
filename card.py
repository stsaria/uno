from enum import Enum

class Color(Enum):
    RED = "RED"
    BLUE = "BLUE"
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    BLACK = "BLACK"
    EMP = "EMP"

class CardType(Enum):
    ZERO = "0"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    REVERSE = "REVERSE"
    SKIP = "SKIP"
    DRAW_TWO = "DRAW_TWO"
    DRAW_FOUR = "DRAW_FOUR"
    SELECT_COLOR = "SELECT_COLOR"

class IllegalCardException(Exception):
    pass


class Card:
    def __init__(self, cardColor : Color, cardType : CardType) -> None:
        if cardColor != Color.BLACK and (cardType in [CardType.DRAW_FOUR, CardType.SELECT_COLOR]):
            raise IllegalCardException(f"The cardColor {cardColor} and the card type {cardType} are incompatible.")
        self._color : Color = cardColor
        self._cardType : CardType = cardType
    def getColor(self) -> Color:
        return self._color
    def getCardType(self) -> CardType:
        return self._cardType
    def isSpecialCardType(self) -> bool:
        return not self._cardType in [CardType.ZERO, CardType.ONE, CardType.TWO, CardType.FOUR, CardType.FIVE, CardType.SIX, CardType.SEVEN, CardType.EIGHT, CardType.NINE]
    def getName(self) -> str:
        return f"dCard-{self._color.value}-{self._cardType.value}"

class ColorSelectableCard(Card):
    def __init__(self, cardType : CardType, selectedColor : Color):
        if not cardType in [CardType.DRAW_FOUR, CardType.SELECT_COLOR]:
            raise IllegalCardException(f"The cardColor {Color.BLACK} and the card type {cardType} are incompatible.")
        elif selectedColor == Color.BLACK:
            raise IllegalCardException(f"Black is not available in select colors.")
        super().__init__(Color.BLACK, cardType)
        self._selectedColor = selectedColor
    def setSelectedColor(self, color : Color) -> None:
        self._selectedColor = color
    def getSelectedColor(self) -> Color:
        return self._selectedColor
    def getName(self) -> str:
        return f"csCard-{self._cardType.value}-{self._selectedColor.value}"
    def getOnlyTypeName(self) -> str:
        return f"csCard-{self._cardType.value}"

class CardsUtil:
    @staticmethod
    def generateCards() -> list[Card]:
        cards : list[Card] = []
        for c in Color:
            if c == Color.EMP:
                continue
            elif c == Color.BLACK:
                for _ in range(4):
                    cards.append(ColorSelectableCard(CardType.DRAW_FOUR, Color.EMP))
                    cards.append(ColorSelectableCard(CardType.SELECT_COLOR, Color.EMP))
                continue
            for t in CardType:
                if t in [CardType.DRAW_FOUR, CardType.SELECT_COLOR]:
                    continue
                cards.append(Card(c, t))
                if t != CardType.ZERO:
                    cards.append(Card(c, t))
        return cards
    @staticmethod
    def isCanPut(haveCards : list[Card], beforeCard : Card, nextCard : Card) -> bool:
        if not (nextCard in haveCards or isinstance(nextCard, ColorSelectableCard)): return False
        elif isinstance(nextCard, ColorSelectableCard):
            if not nextCard.getOnlyTypeName()+"-"+Color.EMP.value in [c.getName() for c in haveCards]: return False
            elif not isinstance(beforeCard, ColorSelectableCard): return True
        elif beforeCard.getCardType() == nextCard.getCardType(): return True
        elif not isinstance(beforeCard, ColorSelectableCard) and beforeCard.getColor() == nextCard.getColor(): return True
        elif isinstance(beforeCard, ColorSelectableCard) and beforeCard.getSelectedColor() == nextCard.getColor(): return True
        elif beforeCard.getColor() == nextCard.getColor(): return True
        return False
    @staticmethod
    def findCardByCardName(cards : list[Card], name : str) -> Card|None:
        for c in cards:
            if c.getName() == name:
                return c
            elif isinstance(c, ColorSelectableCard) and name.startswith("csCard-"):
                if c.getCardType().value == name.split("-")[1]:
                    return CardUtil.cardNameToCard(name)
        return None

class CardUtil:
    @staticmethod
    def cardNameToCard(name : str) -> Card|ColorSelectableCard|None:
        nameA = name.split("-")
        match nameA[0]:
            case "dCard":
                return Card(Color(nameA[1]), CardType(nameA[2]))
            case "csCard":
                return ColorSelectableCard(CardType(nameA[1]), Color(nameA[2]))
        return None
    @staticmethod
    def cardToCasualName(card : Card) -> str:
        if isinstance(card, ColorSelectableCard):
            if card.getSelectedColor() == Color.EMP:
                return f"色選択可能(ブラックカード) - カードタイプ:{card.getCardType().value} まだ選択されていません"
            return f"色選択可能(ブラックカード) - CardType:{card.getCardType().value} 選択された色:{card.getSelectedColor().value}"
        else:
            return f"通常カード - 色:{card.getColor().value} カードタイプ:{card.getCardType().value}"


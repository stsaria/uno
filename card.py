from enum import Enum

SPECIAL_COLOR_SELECTABLE_CARDS = 4

class Color(Enum):
    RED = 0
    BLUE = 1
    GREEN = 2
    YELLOW = 3
    BLACK = 4

class CardType(Enum):
    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    REVERSE = 10
    SKIP = 11
    DRAW_TWO = 12
    DRAW_FOUR = 13
    SELECT_COLOR = 14

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

class ColorSelectableCard(Card):
    def __init__(self, cardType : CardType, selectedColor : Color):
        if not cardType in [CardType.DRAW_FOUR, CardType.SELECT_COLOR]:
            raise IllegalCardException(f"The cardColor {Color.BLACK} and the card type {cardType} are incompatible.")
        super().__init__(Color.BLACK, cardType)
        self._selectedColor = selectedColor
    def getSelectedColor(self) -> Color:
        return self._selectedColor

class CardsUtil:
    @staticmethod
    def generateCards() -> list[Card]:
        cards : list[Card] = []
        for c in Color:
            if c == Color.BLACK:
                for _ in range(4):
                    cards.append(Card(c, CardType.DRAW_FOUR))
                    cards.append(Card(c, CardType.SELECT_COLOR))
                continue
            for t in CardType:
                if t in [CardType.DRAW_FOUR, CardType.SELECT_COLOR]:
                    continue
                cards.append(Card(c, t))
        return cards
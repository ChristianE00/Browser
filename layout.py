# import helpers as h
from helpers import get_font, FONTS
from draw import DrawText, DrawRect


class LineLayout:

    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def paint(self):
        return []

    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for word in self.children:
            word.layout()
        if not self.children:
            self.height = 0
            return

        # 3: Calculate the line's basline
        # NOTE: this code is reading from a font field on each word and writing
        # to each word's  y field. So, inside TextLayout's layout method, we
        # need to compute x, width, and height, but also fonta nd not y
        max_ascent = max([word.font.metrics("ascent") for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")
        max_descent = max([word.font.metrics("descent") for word in self.children])

        # NOTE: since each line now has its own layout object, we need to
        # calculate the line's height
        self.height = 1.25 * (max_ascent + max_descent)

class TextLayout:

    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
        self.font  = None
        self.width = None
        self.x     = None


    def paint(self):
        color = self.node.style["color"]
        return [DrawText(self.x, self.y, self.word, self.font, color)]

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        family = self.node.style["font-family"]

        if style == "normal": style = "roman"

        # 1: First calculate word size
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style, family)
        self.width = self.font.measure(self.word)

        # 2: Calculate x and y position
        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
        self.height = self.font.metrics("linespace")





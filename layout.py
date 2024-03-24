# import helpers as h
from helpers import get_font, FONTS, CHECKBOX_HEIGHT
from draw import DrawText, DrawRect, DrawLine, Rect
from Text import Text

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

    def __repr__(self):
        return "LineLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

    def should_paint(self):
        return True

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

    def __repr__(self):
        return ("TextLayout(x={}, y={}, width={}, height={}, " +
            "word={})").format(
            self.x, self.y, self.width, self.height, self.word)

    def should_paint(self):
        return True

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


INPUT_WIDTH_PX = 200
class InputLayout:

    def __init__(self, node, parent, previous):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
        self.type = 'checkbox'
        if self.type == 'checkbox':
            self.width = CHECKBOX_HEIGHT 

    def __repr__(self):
        return "InputLayout(x={}, y={}, width={}, height={}, tag={})".format(
            self.x, self.y, self.width, self.height, self.node.tag)
    
    def should_paint(self):
        return True

    def self_rect(self):
        return Rect(self.x, self.y,
            self.x + self.width, self.y + self.height)

    def inset(self, offset):
        return Rect(self.left - offset, self.right + offset, self.top + offset, self.bottom - offset)

    def paint(self):
        cmds = []
        bgcolor = self.node.style.get('background-color', 'transparent')
        if bgcolor != 'transparent':
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)

        
        if self.type == 'checkbox':
            '''
            rect = DrawRect(self.self_rect(), 'black')
            cmds.append(rect)
            '''
            if 'checked' in self.node.attributes:
                rect = DrawRect(self.self_rect().inset(3), 'red')
                cmds.append(rect)

        if self.node.tag == 'input':
            text = self.node.attributes.get('value', '')

        elif self.node.tag == 'button':
            if len(self.node.children) == 1 and isinstance(self.node.children[0], Text):
                text = self.node.children[0].text
            else:
                print("Ignoring HTML contents inside button")
                text = ""

        color = self.node.style["color"]
        cmds.append(
            DrawText(self.x, self.y, text, self.font, color))

        if self.node.is_focused:
            cx = self.x + self.font.measure(text)
            cmds.append(DrawLine(cx, self.y, cx, self.y + self.height, 'black', 1)) 
        return cmds

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        family = self.node.style["font-family"]
        
        
        if style == "normal": style = "roman"

        # 1: First calculate word size
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style, family)
        self.width = INPUT_WIDTH_PX

        # 2: Calculate x and y position
        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
        self.height = self.font.metrics("linespace")




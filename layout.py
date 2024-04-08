# import helpers as h
from helpers import get_font, FONTS, CHECKBOX_HEIGHT, WIDTH, BLOCK_ELEMENTS, HSTEP, VSTEP
from draw import DrawText, DrawRect, DrawLine, Rect, DrawOutline
from Text import Text
from Element import Element


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

        # Second layout calls
        for word in self.children:
            word.post_y_layout()

    

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
        self.y = None
        self.width = None
        self.height = None
        self.font = None

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

    def post_y_layout(self):
        return


INPUT_WIDTH_PX = 200
class InputLayout:

    def __init__(self, node, parent, previous):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.font = None
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
        if self.type == 'hidden':
            return cmds

        if bgcolor != 'transparent':
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)
        
        if self.type == 'checkbox':
            if 'checked' in self.node.attributes:
                rect = DrawRect(self.self_rect().inset(3), 'red')
                cmds.append(rect)

        if self.node.tag == 'input':
            if self.node.attributes.get('type', 'text') == 'password':
                text = '*' * len(self.node.attributes.get('value', ''))
            else:
                text = self.node.attributes.get('value', '')

        elif self.node.tag == 'button':
            if len(self.node.children) == 1 and isinstance(self.node.children[0], Text):
                text = self.node.children[0].text
            else:
                text = ""
            return cmds

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

        if self.node.tag == 'input' and self.type == 'hidden':
            self.width = 0.0

        # 2: Calculate x and y position
        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        elif self.type == 'hidden':
            self.height = 0.0
        else:
            self.x = self.parent.x
        self.height = self.font.metrics("linespace")


    def post_y_layout(self):
        if self.node.tag == 'button':
            child = BlockLayout(self.node.children[0], self, None)
            self.children.append(child)
            child.layout()


class BlockLayout:

    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x, self.y, self.width, self.height = None, None, None, None
        self.height_of_firstline = 0

    def __repr__(self):
        return "BlockLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

    def self_rect(self):
        return Rect(self.x, self.y,
                    self.x + self.width, self.y + self.height)

    def paint(self):
        cmds = []
        bgcolor = self.node.style.get("background-color", "transparent")
        if bgcolor != "transparent":
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)
        return cmds      
    
    def should_paint(self):
        return isinstance(self.node, Text) or \
            (self.node.tag != "input" and self.node.tag !=  "button")

    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children or self.node.tag == 'input':
            return "inline"
        else:
            return "block"

    def layout(self):
        self.x = self.parent.x
        self.width = self.parent.width
        self.superscript = False
        self.abbr = False

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        if isinstance(self.node, Element) and self.node.tag == "li":
            self.x = self.parent.x + (2 * HSTEP)
            self.width = self.parent.width - (2 * HSTEP)
        else:
            self.x = self.parent.x
            self.width = self.parent.width

        mode = self.layout_mode()
        if mode == "block":
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.new_line()
            self.recurse(self.node)

        for child in self.children:
            child.layout()
        self.height = sum([child.height for child in self.children])

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == 'br':
                self.new_line()
            elif node.tag == 'input' or node.tag == 'button':
                self.input(node)
            else:
                for child in node.children:
                    self.recurse(child)

    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)

    def flush(self, center=False):
        if not self.line:
            return
        
        max_ascent = max([font.metrics("ascent")
                         for x, word, font, s, color in self.line])
        baseline = self.cursor_y + 1.25 * max_ascent
        last_word_width = self.line[-1][2].measure(self.line[-1][1])
        line_length = (self.line[-1][0] + last_word_width) - self.line[0][0]
        centered_x = (WIDTH - line_length) / 2
        for rel_x, word, font, s, color in self.line:
            x = centered_x + (rel_x + self.x) - \
                self.line[0][0] if center else rel_x + self.x
            y = self.y + baseline - max_ascent if s else self.y + baseline - \
                font.metrics("ascent")
            self.display_list.append((x, y, word, font, color))

        max_descent = max([font.metrics("descent")
                          for x, word, font, s, color in self.line])

        self.height_of_firstline = (1.25 * max_descent) + (1.25 * max_ascent)
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = 0
        self.line = []

    def new_line(self):
        """Creates a new line and resets some files"""
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def word(self, node, word):
        weight = node.style["font-weight"]
        # NOTE: This might be a bug 
        style = 'roman' if (style := node.style["font-style"]) == 'normal' else style
        family = node.style["font-family"]
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style, family)
        w = font.measure(word)

        if self.cursor_x + w > self.width:
            self.new_line()

        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, previous_word)
        line.children.append(text)
        self.cursor_x += w + font.measure(" ")

    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        input = InputLayout(node, line, previous_word)
        line.children.append(input)

        family = node.style["font-family"]
        weight = node.style["font-weight"]
        style = 'roman' if (style := node.style["font-style"]) == 'normal' else style
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style, family)

        self.cursor_x += w + font.measure(" ")


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []
        self.x, self.y, self.width, self.height = None, None, None, None

    def __repr__(self):
        return "DocumentLayout()"

    def paint(self):
        return []

    def should_paint(self):
        return True

    def layout(self):
        self.width = WIDTH - 2*HSTEP
        self.x, self.y = HSTEP, VSTEP
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        child.layout()
        # self.display_list = child.display_list
        self.height = child.height

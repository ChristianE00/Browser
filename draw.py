class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.rect = Rect(x1, y1, x1 + font.measure(text), y1 + font.metrics("linespace"))
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.bottom = y1 + font.metrics("linespace")
        self.color = color

    def __repr__(self):
        #return "DrawText(text={})".format(self.text)
        #top=20.25 left=85 bottom=32.25 text=1 font=Font size=12 weight=normal slant=roman style=None
        return "DrawText(top={} left={} bottom={} text={} font={})".format(
            self.top, self.left, self.bottom, self.text, self.font)

    def execute(self, scroll, canvas):
        canvas.create_text(self.left, self.top - scroll, text=self.text, font=self.font, anchor="nw", fill=self.color)


class DrawRect:
    #def __init__(self, x1, y1, x2, y2, color):
    def __init__(self, rect, color):
        self.rect = rect
        self.color = color

    def __repr__(self):
        return "DrawRect(top={} left={} bottom={} right={} color={})".format(
            self.rect.top, self.rect.left, self.rect.bottom, self.rect.right, self.color)

    def execute(self, scroll, canvas):
        canvas.create_rectangle(self.rect.left, self.rect.top - scroll, self.rect.right, self.rect.bottom - scroll, width=0, fill=self.color)


class Rect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def __repr__(self):
        return "Rect({}, {}, {}, {})".format(self.left, self.top, self.right, self.bottom)

    def containsPoint(self, x, y):
        ''' Test whether a point is contained in a Rext '''
        return x >= self.left and x < self.right and y >= self.top and y < self.bottom


class DrawLine:
    # def __init__(self, rect, color, thickness):
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.rect = Rect(x1, y1, x2, y2)
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_line(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            fill=self.color, width=self.thickness)

class DrawOutline:
    def __init__(self, rect, color, thickness):
        self.rect = rect
        self.color = color
        self.thickness = thickness
    
    def __repr__(self):
        return "DrawOutline(top={} left={} bottom={} right={} color={} thickness={})".format(
            self.rect.top, self.rect.left, self.rect.bottom, self.rect.right, self.color, self.thickness)

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            width=self.thickness,
            outline=self.color)
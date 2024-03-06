

class LineLayout:

    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previos = previous
        self.children = []





class TextLayout:

    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous

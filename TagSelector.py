from Element import Element

class TagSelector:
    def __init__(self, tag):
        self.tag = tag
    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag
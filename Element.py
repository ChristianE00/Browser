
class Element:

    def __init__(self, tag, attributes, parent):
        self.attributes = attributes
        self.tag = tag
        self.children = []
        self.parent = parent
        self.is_focused = False


    def __repr__(self):
        attrs = [" " + k + "=\"" + v + "\"" for k, v  in self.attributes.items() if k != self.tag]
        attr_str = ""
        for attr in attrs:
            attr_str += attr
        if attr_str == "":
            return "<" + self.tag + ">"
        else:
            return "<" + self.tag + attr_str + ">"


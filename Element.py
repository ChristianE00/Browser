class Element:
    """A simple class to represent an element token."""

    def __init__(self, tag, attributes, parent):
        self.attributes = attributes
        self.tag = tag
        self.children = []
        self.parent = parent

    def __repr__(self):
        if self.attributes:
            str = "<" + self.tag
            for key, value in self.attributes.items():
                str += f' {key}="{value}"'
            return str + ">"
        # else:
        return f"<{self.tag}>"
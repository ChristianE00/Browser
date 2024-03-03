from Element import Element
class ClassSelector:
    def __init__(self, class_name):
        self.class_name = class_name
        self.priority = 10


    def __repr__(self):
        return "ClassSelector(classname={}, priority={})".format(
            self.class_name, self.priority)


    def matches(self, node):
        node_classes = node.attributes.get("class", "")
        node_classes_split = node_classes.split()
        return isinstance(node, Element) and self.class_name in node_classes_split

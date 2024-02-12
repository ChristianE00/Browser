class HTMLParser:
    def __init__(self):
        self.body = body
        self.unfinished = []

    def parse(self, html):
        pass

    def parse(self):
        """Show the body of the HTML page, without the tags."""
        out = []
        buffer = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if buffer:
#                    out.append(Text(buffer))
                    self.add_text(buffer)
                buffer = ""
            elif c == ">":
                in_tag = False
#                out.append(Tag(buffer))
                self.add_tag(buffer)
                buffer = ""
            else:
                buffer += c
        if not in_tag and buffer:
#            out.append(Text(buffer))
            self.add_text(buffer)
#        return out
        return self.finish()
    
    def finish(self):
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()


    def add_tag(self, tag):
        if tag.startswith("/"):
            if len(self.unfinished) ==1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, parent)
            self.unfinished.append(node)

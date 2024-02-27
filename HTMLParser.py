class HTMLParser:

    def __init__(self, body):
        self.body = body
        self.unfinished = []
        self.SELF_CLOSING_TAGS = [
            "area",
            "base",
            "br",
            "col",
            "command",
            "embed",
            "hr",
            "img",
            "input",
            "keygen",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        ]
        self.HEAD_TAGS = [
            "base",
            "link",
            "meta",
            "script",
            "style",
            "title",
            "basefont",
            "bgsoung",
            "noscript",
        ]

    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif (
                open_tags == ["html", "head"] and tag not in [
                    "/head"] + self.HEAD_TAGS
            ):
                self.add_tag("/head")
            else:
                break

    def get_attributes(self, text):
        """Return the tag and attributes from a string."""

        single_quote, double_quote, swap = False, False, False
        parts = []
        current = ""
        attributes = {}

        for c in text:
            if c == "'" and not double_quote:
                single_quote = not single_quote
                if not single_quote:
                    swap = True
            elif c == '"' and not single_quote:
                double_quote = not double_quote
                if not double_quote:
                    swap = True
            elif c == " " and not single_quote and not double_quote or swap:
                swap = False
                parts.append(current)
                current = ""
                # Edge case: If there is no space between the end of the quote
                # and the next attribute
                if c != " ":
                    current += c
            else:
                current += c

        if current:
            parts.append(current)
        tag = parts[0].casefold() if len(parts) > 0 else ""
        for attrpair in parts[1:]:
            # attrpair contains c = '=' where c-1 != " " and i+1 != " "
            if re.search(r"[^ ]=[^ ]", attrpair):
                # Split the attribute into key and value on c = '=' where c-1
                # != " " and i+1 != " "
                key, value = re.split(r"(?<=[^ ])=(?=[^ ])", attrpair, 1)
                attributes[key.casefold()] = value
                if len(value) > 2 and value[0] in ["", '"']:
                    value = value[1:-1]
            else:
                attributes[attrpair.casefold()] = ""
        return tag, attributes

    def parse(self):
        """Show the body of the HTML page, without the tags."""
        buffer = ""
        in_script, in_tag, is_comment, double_in_quote, single_in_quote = False, False, False, False, False
        count = 0

        # So we can determine whether or not we are inside a comment
        for i, c in enumerate(self.body):
            if c == '"' and not single_in_quote and in_tag:
                double_in_quote = not double_in_quote
            if c == "'" and not double_in_quote and in_tag:
                single_in_quote = not single_in_quote
            if count > 0:
                count -= 1
            elif c == "<" and not single_in_quote and not double_in_quote:
                if self.body[i + 1: i + 9] == "/script>":
                    in_tag = True
                    in_script = False
                elif in_script:
                    buffer += c
                    continue
                elif self.body[i + 1: i + 4] == "!--":
                    is_comment = True
                    count = 5
                in_tag = True
                if buffer:
                    self.add_text(buffer)
                buffer = ""
            elif c == ">" and not single_in_quote and not double_in_quote:
                if in_script:
                    buffer += c
                    continue
                in_tag = False
                if self.body[i - 2: i] == "--":
                    is_comment = False
                elif not is_comment:
                    if buffer == "script":
                        in_script = True
                    elif buffer == "/script":
                        in_script = False
                    self.add_tag(buffer)
                    buffer = ""
            else:
                if not is_comment:
                    buffer += c
        if not in_tag and buffer:
            self.add_text(buffer)
        return self.finish()

    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

    def add_text(self, text):
        if text.isspace():
            return
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag):
        bob = []
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("<!"):
            return
        self.implicit_tags(tag)
        if tag.startswith("/"):
            if len(self.unfinished) == 1:
                return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:

            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            # attribute added here
            parent.children.append(node)
        else:
            if tag == "p":
                for i, unfinished_tag in enumerate(self.unfinished):
                    if unfinished_tag.tag == "p":
                        if i == len(self.unfinished) - 1:
                            u_parent = self.unfinished[i - 1]
                            u_parent.children.append(unfinished_tag)
                            del self.unfinished[i]
                        else:
                            for j in range(len(self.unfinished) - 1, i, -1):
                                u_parent = self.unfinished[j - 1]
                                u_parent.children.append(self.unfinished[j])
                                unf = self.unfinished[j]
                                bob.append(
                                    Element(
                                        unf.tag,
                                        unf.attributes,
                                        unf.parent))
                                del self.unfinished[j]
                            u_parent = self.unfinished[i - 1]
                            u_parent.children.append(unfinished_tag)
                            del self.unfinished[i]
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)
            while bob:
                self.unfinished.append(bob.pop())

import platform
import re
import socket
import ssl
import time
import tkinter
import tkinter.font
import unicodedata
from typing import Dict, Optional

WIDTH, HEIGHT, HSTEP, VSTEP, C, SCROLL_STEP = 800, 600, 13, 18, 0, 100
GRINNING_FACE_IMAGE = None
EMOJIS, FONTS = {}, {}
BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]


def print_tree(node, indent=0):
    """Print the tree structure of the HTML."""
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)


def get_font(size, weight, slant):
    """Get a font from the cache or create it and add it to the cache."""
    key = (size, weight, slant)

    # If the font is not in the cache, create it and add it to the cache
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=slant)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]


def set_parameters(**params):
    """Modify the WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP parameters"""
    global WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
    if "WIDTH" in params:
        WIDTH = params["WIDTH"]
    if "HEIGHT" in params:
        HEIGHT = params["HEIGHT"]
    if "HSTEP" in params:
        HSTEP = params["HSTEP"]
    if "VSTEP" in params:
        VSTEP = params["VSTEP"]
    if "SCROLL_STEP" in params:
        SCROLL_STEP = params["SCROLL_STEP"]


def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())
    for child in layout_object.children:
        paint_tree(child, display_list)


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []
        self.x, self.y, self.width, self.height = None, None, None, None

    def paint(self):
        return []

    def layout(self):
        self.width = WIDTH - 2*HSTEP
        self.x, self.y = HSTEP, VSTEP
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
    
        child.layout()
        self.display_list = child.display_list
        self.height = child.height


class DrawText:
    def __init__(self, x1, y1, text, font):
        self.top, self.left, self.text, self.font = y1, x1, text, font
        self.bottom = y1 + font.metrics("linespace")

    def execute(self, scroll, canvas):
        canvas.create_text(self.left, self.top - scroll, text=self.text, font=self.font, anchor="nw")


class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top, self.left, self.bottome, self.right, self.color = x1, y1, y2, x2, color

    def execute(self, scroll, canvas):
        canvas.create_rectangle(self.left, self.top - scroll, self.right, self.bottom - scroll, width=0, fill=self.color)


#NOTE: Doesn't seem to be creating all the child blocks
#       Only 2 BlockLayouts are working <html>, <body>
class BlockLayout:
    """A class that takes a list of tokens and converts it to a display list."""

    def __init__(self, node, parent, previous):
        print('block created node: ', node)
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x, self.y, self.width, self.height = 0, 0, 0, 0

    def paint(self):
        cmds = []
        # Must be called before any text is drawn because it got to be behind the text
        if isinstance(self.node, Element) and self.node.tag == "pre":
            x2, y2, = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            cmds.append(rect)
        if self.layout_mode() == "inline":
            for x, y, word, font in self.display_list:
                cmds.append(DrawText(x, y, word, font))

        return cmds


    def layout_mode(self):
        print('type of node: ', type(self.node), ' node: ', self.node)
        if isinstance(self.node, Text):
            print("Inline First")
            return "inline"
        elif any([isinstance(child, Element) and child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            print("BLOCK First")
            return "block"
        elif self.node.children:
            print("INLINE Second") 
            return "inline"
        else:
            print("BLOCK Second")
            return "block"

    def layout_intermediate(self):
        previous = None
        for child in self.node.children:
            next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next

    def layout(self):
        self.x = self.parent.x
        self.width = self.parent.width
        self.superscript = False
        self.abbr = False
        self.display_list = []
        mode = self.layout_mode()
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        #NOTE: Thinks <body>
        if mode == "block":
            print('is block')
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.cursor_x, self.cursor_y = 0, 0 
            self.weight, self.style = "normal", "roman"
            self.size = 16
            self.line = []
            self.recurse(self.node)
            self.flush()

        for child in self.children:
            child.layout()
        for child in self.children:
            self.display_list.extend(child.display_list)
        if mode == "block":
            self.height = sum([child.height for child in self.children])
        else:
            self.height = self.cursor_y

    def open_tag(self, tag):
        """Process an open tag and modify the state."""
        if tag == "abbr":
            self.abbr = True
        elif tag == "sup":
            self.size = int(self.size / 2)
            self.superscript = True
        elif tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()
        elif tag == 'h1 class="title"':
            self.flush()

    def close_tag(self, tag):

        if tag == "abbr":
            self.abbr = False
        elif tag == "h1":
            self.flush(True)
        elif tag == "sup":
            self.superscript = False
            self.size = int(self.size * 2)
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP
        elif tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4

    def recurse(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.word(word)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

    def token(self, tok):
        """Process a token and add it to the display list."""
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)

    def flush(self, center=False):
        """Flush the current line to the display list."""
        if not self.line:
            return
        # NOTE: Might need to change x calculation
        max_ascent = max([font.metrics("ascent")
                         for x, word, font, s in self.line])
        baseline = self.cursor_y + 1.25 * max_ascent
        last_word_width = self.line[-1][2].measure(self.line[-1][1])
        line_length = (self.line[-1][0] + last_word_width) - self.line[0][0]
        centered_x = (WIDTH - line_length) / 2
        for rel_x, word, font, s in self.line:
            x = centered_x + (rel_x + self.x) - self.line[0][0] if center else rel_x + self.x
            y = self.y + baseline - max_ascent if s else baseline - \
                font.metrics("ascent")
            self.display_list.append((x, y, word, font))

        max_descent = max([font.metrics("descent")
                          for x, word, font, s in self.line])
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = 0
        self.line = []

    def word(self, word):
        """Add a word to the current line."""
        w = 0
        if self.abbr:
            isLower = None  # Initially, we haven't encountered any character
            buffer = ""
            for c in word:
                currentIsLower = c.islower()
                if isLower is None:
                    isLower = (
                        currentIsLower  # Set initial case based on the first character
                    )

                if currentIsLower != isLower:
                    if isLower:  # If the previous chunk was lowercase
                        font = get_font(self.size // 2, "bold", self.style)
                        transformed_buffer = buffer.upper()
                    else:  # If the previous chunk was uppercase
                        font = get_font(self.size, self.weight, self.style)
                        transformed_buffer = buffer

                    w = font.measure(transformed_buffer)
                    self.line.append(
                        (self.cursor_x, transformed_buffer, font, self.superscript)
                    )
                    self.cursor_x += w

                    if c == word[-1]:
                        self.cursor_x += font.measure(" ")

                    buffer = c
                    isLower = currentIsLower
                else:
                    buffer += c
            font = get_font(self.size, self.weight, self.style)
            # Handle any remaining characters in the buffer after the loop
            if buffer:
                if isLower:
                    font = get_font(self.size // 2, "bold", self.style)
                    transformed_buffer = buffer.upper()
                else:
                    font = get_font(self.size, self.weight, self.style)
                    transformed_buffer = buffer

            w = font.measure(transformed_buffer)
            self.line.append(
                (self.cursor_x, transformed_buffer, font, self.superscript)
            )
            self.cursor_x += w + get_font(self.size, self.weight, self.style).measure(
                " "
            )
            return

        else:
            font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)
        if word == "\n":
            self.cursor_x, self.cursor_y = HSTEP, self.cursor_y + VSTEP * 2
            return

        if self.cursor_x + w > self.width:
            if "\N{SOFT HYPHEN}" in word:
                words = word.split("\N{SOFT HYPHEN}")
                word = ""
                for current_word in words:
                    if (
                        self.cursor_x
                        + font.measure(word + "-")
                        + font.measure(current_word)
                        <= WIDTH - HSTEP
                    ):
                        word += current_word
                    else:
                        self.word(word + "-")
                        self.flush()
                        word = current_word
                self.word(word)
                return
            else:
                self.flush()
                self.cursor_y += font.metrics("linespace") * 1.25
                self.cursor_x = HSTEP
        self.line.append((self.cursor_x, word, font, self.superscript))
        self.cursor_x += w + font.measure(" ")


class Text:
    """A simple class to represent a text token."""

    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr(self.text)


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


class Tag:
    """A simple class to represent a tag token."""

    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return "Tag('{}')".format(self.tag)


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
                # Edge case: If there is no space between the end of the quote and the next attribute
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
                # Split the attribute into key and value on c = '=' where c-1 != " " and i+1 != " "
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
                                    Element(unf.tag, unf.attributes, unf.parent))
                                del self.unfinished[j]
                            u_parent = self.unfinished[i - 1]
                            u_parent.children.append(unfinished_tag)
                            del self.unfinished[i]
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)
            while bob:
                self.unfinished.append(bob.pop())


class Browser:
    """A simple browser that can load and display a web page."""

    def __init__(self):
        global GRINNING_FACE_IMAGE, EMOJIS
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
        )
        self.entry = tkinter.Entry(self.window)
        self.entry.bind("<Return>", self.on_submit)
        self.text_showing = False
        self.window.bind("<Configure>", self.resize)
        self.canvas.pack(fill=tkinter.BOTH, expand=0)
        GRINNING_FACE_IMAGE = tkinter.PhotoImage(file="openmoji/1F600.png")
        EMOJIS["\N{GRINNING FACE}"] = GRINNING_FACE_IMAGE
        self.scroll, self.last_y = 0, 0
        self.scrolling = False
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<MouseWheel>", self.scrolldown)
        self.window.bind(":", self.command_mode)
        self.window.bind("<Escape>", self.insert_mode)

    def command_mode(self, e):
        if not self.text_showing:
            self.entry.pack(fill=tkinter.X)
            self.entry.focus_set()
            self.text_showing = True

    def insert_mode(self, e):
        if self.text_showing:
            self.entry.pack_forget()
            self.text_showing = False
            self.entry.delete(0, tkinter.END)

    def on_submit(self, e):
        if self.text_showing:
            cmd = self.entry.get().strip().lower()
            self.entry.pack_forget()
            self.text_showing = False
            self.entry.delete(0, tkinter.END)
            if cmd == ":quit":
                exit()
            elif cmd == ":light blue":
                self.canvas.config(bg="light blue")
            elif cmd == ":default":
                self.canvas.config(bg="white")

    def resize(self, e):
        """Resize the canvas and redraw the display list."""
        global WIDTH, HEIGHT
        WIDTH, HEIGHT = e.width, e.height

    def scrolldown(self, e):
        """Scroll down by SCROLL_STEP pixels."""
        # Default for Windows and Linux, divide by 120 for MacOS omegalul a single ternary
        delta = (
            e.delta / 120
            if hasattr(e, "delta")
            and e.delta is not None
            and platform.system() == "Darwin"
            else e.delta if hasattr(e, "delta") else None
        )
        # Mouse wheel down. On Windows, e.delta < 0 => scroll down.
        # NOTE: on Windows delta is positive for scroll up. On MacOS divid delta by 120
        #      On Linux you need to use differenct events to scroll up and scroll down
        # Scroll up

        if (delta is not None and delta > 0) or (
            hasattr(e, "keysym") and e.keysym == "Up"
        ):
            if self.scroll > 0:
                self.scroll -= SCROLL_STEP
                self.draw()
        else:
            max_y = max(self.document.height + 2*VSTEP - HEIGHT, 0)
            self.scroll = min(self.scroll + SCROLL_STEP, max_y)
            self.draw()

    def draw(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            #print('cmd: ', cmd)
            if cmd.top > self.scroll + HEIGHT:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll, self.canvas)

        '''
            if c in EMOJIS:
                self.canvas.create_image(x, y - self.scroll, image=EMOJIS[c])
                continue
            self.canvas.create_text(
                x, y - self.scroll, text=c, font=d, anchor="nw")
   
            
        if self.display_list and self.display_list[-1][1] > HEIGHT:
            self.canvas.create_rectangle(
                WIDTH - 8,
                self.scroll / self.display_list[-1][1] * HEIGHT,
                WIDTH,
                HEIGHT / self.display_list[-1][1] * HEIGHT
                + (self.scroll / self.display_list[-1][1]) * HEIGHT,
                fill="blue",
            )
        '''

    def load(self, url, view_source: Optional[bool] = False):
        """Load the given URL and convert text tags to character tags."""
        # Note: Test for testing extra headers

        body = url.request().replace("&lt;", "<").replace("&gt;", ">")

        if view_source:
            print(body)
        else:
            self.nodes = HTMLParser(body).parse()
            # Start of broken code
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.display_list = []
            paint_tree(self.document, self.display_list)
            self.draw()


class URL:
    """This class is used to parse the url and request the data from the server"""

    cache = {}

    def format_headers(self, headers):
        """Format the given header dictionary into a string."""
        user_agent = "User-Agent: SquidWeb\r\n"
        connection = "Connection: close\r\n"
        remove_list = []
        for key in headers.keys():
            if key.lower() == "user-agent":
                user_agent = key + ": " + headers[key] + "\r\n"
                remove_list.append(key)
            if key.lower() == "connection":
                connection = key + ": " + headers[key] + "\r\n"
                remove_list.append(key)
        # Remove the headers that are already in the default headers
        for key in remove_list:
            del headers[key]

        headers_text = "\r\n".join("{}: {}".format(k, v)
                                   for k, v in headers.items())
        headers_text = "\r\n" + user_agent + connection + headers_text
        base_headers = (
            "GET {} HTTP/1.1\r\n".format(self.path)
            + "Host: {}".format(self.host)
            + headers_text
            + "\r\n\r\n"
        ).encode("utf8")
        return base_headers

    def __init__(self, url):
        """Initiate the URL class with a scheme, host, port, and path."""
        self.visited_urls = set()
        self.default_headers = {"User-Agent": "default/1.0"}
        url = url.strip()
        if "://" in url:
            self.scheme, url = url.split("://", 1)
            self.scheme = self.scheme.strip()
            if "/" in url:
                self.host, url = url.split("/", 1)
            elif "file" not in self.scheme:
                self.host = url
                url = ""
            assert self.scheme in ["http", "https", "file"]

            self.path = url
            if "file" in self.scheme:
                self.port = None
                return
            elif ":" in self.host:
                self.host, port = self.host.split(":", 1)
                self.port = int(port)
            elif self.scheme == "http":
                self.port = 80
            elif self.scheme == "https":
                self.port = 443
            self.path = "/" + self.path
        # Handle inline HTML
        elif "data:" in url:
            self.path = url
            self.scheme, url = url.split(":", 1)
            self.port = None

    def cache_response(self, url, headers, body):
        """Cache the response from the server if possible."""
        # Extract max-age from headers
        cache_control = headers.get("cache-control", "")
        if cache_control:
            directives = cache_control.split(",")
            for directive in directives:
                key, sep, val = directive.strip().partition("=")
                if key.lower() == "max-age":
                    try:
                        max_age = int(val)
                    except ValueError:
                        pass
        # Store response in cache with current time and max-age
        URL.cache[url] = (headers, body, time.time(), max_age)

    def get_from_cache(self, url):
        """Get the response from the cache if possible."""
        cached = URL.cache.get(url)
        if cached:
            headers, body, cached_time, max_age = cached
            cached = headers, cached_time, max_age
            # Check if response is still fresh
            if max_age is None or (time.time() - cached_time) <= max_age:
                return headers, body, cached_time, max_age
        return None, None, None, None

    def handle_redirect(self, response):
        """Handles the redirect from the server"""
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            if header.casefold() == "location":
                if "://" not in value:
                    value = (
                        self.scheme.strip() + "://" + self.host.strip() + value.strip()
                    )
                if value in self.visited_urls:
                    return "Error: Redirect loop detected"
                self.visited_urls.add(value.strip())
                return URL(value).request(None, self.visited_urls)
        return "Error: Redirect without location header"

    def handle_local_file(self):
        """Handles the local file file:///path/to/file"""
        with open(self.path, "r", encoding="utf8") as f:
            return f.read()

    def handle_data_scheme(self):
        """Handles the data scheme data:text/html, <html>...</html>"""
        return self.path

    def create_socket(self):
        """Create a socket and connect to the server."""
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        s.connect((self.host, self.port))
        return s

    def send_request(self, s, headers):
        """Send the request to the server."""
        my_headers = (
            "GET {} HTTP/1.1\r\n".format(self.path)
            + "Host: {}\r\nConnection: close\r\nUser-Agent: SquidWeb\r\n\r\n".format(
                self.host
            )
        ).encode("utf8")
        if headers:
            my_headers = self.format_headers(headers)
        s.send(my_headers)

    def read_response(self, s):
        """Read the response from the server."""
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        return response, status

    def read_headers(self, response):
        """Read the headers from the server."""
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        return response_headers

    def request(self, headers: Optional[Dict[str, str]] = None, visited_urls=None):
        """Handles getting the page source from the server or local file."""
        if self.scheme == "file":
            return self.handle_local_file()
        elif self.scheme == "data":
            return self.handle_data_scheme()
        elif self.scheme == "https" or self.scheme == "http":
            url = self.scheme.strip() + "://" + self.host.strip() + self.path.strip()

            # Check if url is in cache, use cached response if it is
            cached_headers, cached_body, cached_time, max_age = self.get_from_cache(
                url)
            if cached_body:
                return cached_body

            s = self.create_socket()
            self.send_request(s, headers)
            response, status = self.read_response(s)

            # Other request code
            if visited_urls is not None:
                self.visited_urls = visited_urls
            self.visited_urls.add(url)

            # Handle redirect
            if int(status) >= 300 and int(status) < 400:
                return self.handle_redirect(response)

            response_headers = self.read_headers(response)
            assert "transfer-encoding" not in response_headers
            assert "content-encoding" not in response_headers
            encoding_response = response_headers.get("content-type", "utf8")
            encoding_position = encoding_response.find("charset=")
            encoding = (
                encoding_response[encoding_position + 8:]
                if encoding_position != -1
                else "utf8"
            )

            # check if response is cacheable and cache it if it is
            if "cache-control" in response_headers:
                cache_response = response_headers["cache-control"].strip()
                if "max-age" in cache_response:
                    max_age = cache_response.split("=")[1]
                    if int(max_age) > 0:
                        body = response.read()
                        s.close()
                        self.cache_response(url, response_headers, body)
                        return body

            body = response.read()
            s.close()
            return body


if __name__ == "__main__":
    import sys
    """
    body = URL(sys.argv[1]).request()
    nodes = HTMLParser(body).parse()
    print_tree(nodes)
    """
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()

import platform
import re
import socket
import ssl
import time
import tkinter
import tkinter.font
import unicodedata
from typing import Dict, Optional
from CSSParser import CSSParser
from classselector import ClassSelector
from Text import Text
from Element import Element
from HTMLParser import HTMLParser
# NOTE CH7 IMPORTS
# CH7 GLOBALS
# NOTE might not need: from helpers import get_font
from layout import LineLayout, TextLayout
from draw import DrawRect, DrawText
from helpers import get_font, FONTS
WIDTH, HEIGHT, HSTEP, VSTEP, C, SCROLL_STEP = 800, 600, 13, 18, 0, 100
GRINNING_FACE_IMAGE = None
EMOJIS = {}
# FONTS = {}
BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]
INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "font-family": "Times",
    "color": "black",
}


def print_tree(node, indent=0):
    """Print the tree structure of the HTML."""
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)


'''
def get_font(size, weight, slant, family):
    key = (size, weight, slant, family)

    # If the font is not in the cache, create it and add it to the cache
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=slant, family=family)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]
'''


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


'''
class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.bottom = y1 + font.metrics("linespace")
        self.color = color

    def __repr__(self):
        return "DrawText(top={} left={} bottom={} text={} font={})" \
            .format(self.top, self.left, self.bottom, self.text, self.font)

    def execute(self, scroll, canvas):
        canvas.create_text(self.left, self.top - scroll, text=self.text, font=self.font, anchor="nw", fill=self.color)


class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def __repr__(self):
        return "DrawRect(top={} left={} bottom={} right={} color={})".format(
            self.top, self.left, self.bottom, self.right, self.color)

    def execute(self, scroll, canvas):
        canvas.create_rectangle(self.left, self.top - scroll, self.right, self.bottom - scroll, width=0, fill=self.color)
'''

def style(node, rules):
    node.style = {}
    # Add inherited properties to the node's style
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value

    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for property, value in pairs.items():
            node.style[property] = value

    for selector, body in rules:
        if not selector.matches(node): continue
        for property, value in body.items():
            node.style[property] = value

    # Resolve percentage sizes to absolute sizes
    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style["font-size"]
        else:
            parent_font_size = INHERITED_PROPERTIES["font-size"]
        node_pct = float(node.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style["font-size"] = str(node_pct * parent_px) + "px"

    for child in node.children:
        style(child, rules)


def cascade_priority(rule):
    selector, body = rule
    return selector.priority


def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list


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

    def layout(self):
        self.width = WIDTH - 2*HSTEP
        self.x, self.y = HSTEP, VSTEP
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        child.layout()
        #self.display_list = child.display_list
        self.height = child.height


# NOTE: Doesn't seem to be creating all the child blocks
#       Only 2 BlockLayouts are working <html>, <body>
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

    def paint(self):
        cmds = []
        bgcolor = self.node.style.get("background-color", "transparent")
        if bgcolor != "transparent":
            x2, y2, = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
            cmds.append(rect)


        if isinstance(self.node, Element) and self.node.tag == "li":
            rect = DrawRect(self.x - HSTEP - 2, self.y + (self.height_of_firstline / 2 - 2),
                self.x - HSTEP + 2, self.y + 4 + (self.height_of_firstline / 2 - 2), "black")
            cmds.append(rect)

        '''
        # Must be called before any text is drawn because it got to be behind the text
        if isinstance(self.node, Element) and self.node.tag == "pre":
            x2, y2, = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            cmds.append(rect)
        '''

        if isinstance(self.node, Element) and self.node.tag == "nav" \
        and "class" in self.node.attributes and "links" in self.node.attributes["class"]:
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "lightgray")
            cmds.append(rect)

        '''
        if self.layout_mode() == "inline":
            for x, y, word, font, color in self.display_list:
                cmds.append(DrawText(x, y, word, font, color))
        '''

        return cmds

    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children:
            return "inline"
        else:
            return "block"

    def layout(self):
        self.x = self.parent.x
        self.width = self.parent.width
        self.superscript = False
        self.abbr = False
#        self.display_list = []

        # NOTE: don't need to init. display_list, cursor_y, or line fields
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
        # NOTE: Thinks <body>

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
            # self.flush()

        for child in self.children:
            child.layout()
        self.height = sum([child.height for child in self.children])

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.new_line()
            for child in node.children:
                self.recurse(child)

    '''
    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.flush()
            for child in node.children:
                self.recurse(child)
    '''

    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)

    def flush(self, center=False):
        if not self.line:
            return
        # NOTE: Might need to change x calculation
        max_ascent = max([font.metrics("ascent")
                         for x, word, font, s, color in self.line])
        baseline = self.cursor_y + 1.25 * max_ascent
        last_word_width = self.line[-1][2].measure(self.line[-1][1])
        line_length = (self.line[-1][0] + last_word_width) - self.line[0][0]
        centered_x = (WIDTH - line_length) / 2
        for rel_x, word, font, s, color in self.line:
            x = centered_x + (rel_x + self.x) - self.line[0][0] if center else rel_x + self.x
            y = self.y + baseline - max_ascent if s else self.y + baseline - \
                font.metrics("ascent")
            self.display_list.append((x, y, word, font, color))

        max_descent = max([font.metrics("descent")
                          for x, word, font, s, color in self.line])
        # NOTE: might need to be replaced
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
        # NOTE fix what 'w' is
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        family = node.style["font-family"]
        if style == "normal": style = "roman"
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

    '''
    def word(self, node, word):
        w = 0
        # TODO: Make self.{style, weight, size} := {style, weight, size}
        color = node.style["color"]
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        family = node.style["font-family"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style, family)
        self.style = style
        self.weight = weight
        self.size = size

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
                        font = get_font(self.size // 2, "bold", self.style, family)
                        transformed_buffer = buffer.upper()
                    else:  # If the previous chunk was uppercase
                        font = get_font(self.size, self.weight, self.style, family)
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
            font = get_font(self.size, self.weight, self.style, family)
            # Handle any remaining characters in the buffer after the loop
            if buffer:
                if isLower:
                    font = get_font(self.size // 2, "bold", self.style, family)
                    transformed_buffer = buffer.upper()
                else:
                    font = get_font(self.size, self.weight, self.style, family)
                    transformed_buffer = buffer

            w = font.measure(transformed_buffer)
            self.line.append(
                (self.cursor_x, transformed_buffer, font, False, color)
            )
            self.cursor_x += w + get_font(self.size, self.weight, self.style, family).measure(
                " "
            )
            return

        else:
            font = get_font(self.size, self.weight, self.style, family)
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
        self.line.append((self.cursor_x, word, font, False, color))
        self.cursor_x += w + font.measure(" ")
    '''


class Tag:
    """A simple class to represent a tag token."""

    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return "Tag('{}')".format(self.tag)


class Browser:
    """A simple browser that can load and display a web page."""

    def __init__(self):
        global GRINNING_FACE_IMAGE, EMOJIS
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white"
        )

        # self.entry = tkinter.Entry(self.window)
        # self.entry.bind("<Return>", self.on_submit)
        # self.text_showing = False
        # self.window.bind("<Configure>", self.resize)
        # self.canvas.pack(fill=tkinter.BOTH, expand=0)

        self.canvas.pack()
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
            max_y = max(self.document.height + 2 * VSTEP - HEIGHT, 0)
            self.scroll = min(self.scroll + SCROLL_STEP, max_y)
            self.draw()

    def draw(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
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

        body = url.request()

        if view_source:
            print(body)
        else:
            DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()
            self.nodes = HTMLParser(body).parse()

            # Gather all the relative URL for each linked style sheet
            links = [node.attributes["href"]
                     for node in tree_to_list(self.nodes, [])
                     if isinstance(node, Element)
                     and node.tag == "link"
                     and node.attributes.get("rel") == "stylesheet"
                     and "href" in node.attributes]
            self.document = DocumentLayout(self.nodes)
            rules = DEFAULT_STYLE_SHEET.copy()

            # Convert relative URLs to full URLS:
            for link in links:
                try:
                    body = url.resolve(link).request()
                # ignore stylesheets that fail to download
                except Exception:
                    continue
                rules.extend(CSSParser(body).parse())

            style(self.nodes, sorted(rules, key=cascade_priority))
            self.document.layout()
            self.display_list = []
            paint_tree(self.document, self.display_list)
            self.draw()


class URL:
    """This class is used to parse the url and request the data from the server"""

    cache = {}

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

    def __repr__(self):
        return f"URL(scheme={self.scheme}, host={self.host}, port={self.port}, path='{self.path}')"

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

    def resolve(self, url):
        if "://" in url: return URL(url)
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return URL(self.scheme + "://" + self.host + \
                       ":" + str(self.port) + url)

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

            '''
            encoding_response = response_headers.get("content-type", "utf8")
            encoding_position = encoding_response.find("charset=")
            encoding = (
                encoding_response[encoding_position + 8:]
                if encoding_position != -1
                else "utf8"
            )
            '''

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
    '''
    body = URL(sys.argv[1]).request()
    nodes = HTMLParser(body).parse()
    print_tree(nodes)
    '''
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()

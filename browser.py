import platform
import re
import socket
import ssl
import time
import tkinter
import tkinter.font
import unicodedata
import urllib
import urllib.parse
import dukpy
from typing import Dict, Optional
from CSSParser import CSSParser
from classselector import ClassSelector
from Text import Text
from Element import Element
from HTMLParser import HTMLParser
from layout import LineLayout, TextLayout, InputLayout, DocumentLayout, INPUT_WIDTH_PX
from draw import DrawRect, DrawText, Rect, DrawLine, DrawOutline
from helpers import get_font, FONTS, WIDTH, HEIGHT, HSTEP, VSTEP, C, SCROLL_STEP, ENTRIES
GRINNING_FACE_IMAGE = None
EMOJIS = {}
'''
BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]
'''
INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "font-family": "Times",
    "color": "black",
}
RUNTIME_JS = open('runtime.js').read()
COOKIE_JAR = {}


def print_tree(node, indent=0):
    """Print the tree structure of the HTML."""
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)


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
    if layout_object.should_paint():
        display_list.extend(layout_object.paint())
    for child in layout_object.children:
        paint_tree(child, display_list)


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
        if not selector.matches(node):
            continue
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
        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<MouseWheel>", self.handle_down)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)
        self.window.bind("<BackSpace>", self.handle_backspace)
        self.window.bind("<Button-2>", self.handle_middle_click)

        self.focus = None
        self.url = None
        self.tabs = []
        self.active_tab = None
        self.bookmarks = []
        self.chrome = Chrome(self)

    def handle_middle_click(self, e):
        """ Forward click to the active tab """
        # click within the web page
        if e.y < self.chrome.bottom:
            pass
        # click within the tab bar
        else:
            tab_y = e.y - self.chrome.bottom
            self.active_tab.middleClick(e.x, tab_y, self)
        self.draw()

    def handle_backspace(self, e):
        self.chrome.backspace()
        self.draw()

    def new_tab(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom, self)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()

    def handle_enter(self, e):
        if self.focus == 'content':
            self.active_tab.enter()
        else:
            self.chrome.enter()
        self.draw()

    def handle_key(self, e):
        if len(e.char) == 0:
            return
        if not (0x20 <= ord(e.char) < 0x7f):
            return
        if self.chrome.keypress(e.char):
            self.draw()
        elif self.focus == 'content':
            self.active_tab.keypress(e.char)
            self.draw()

    def handle_click(self, e):
        """ Forward click to the active tab """
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
        else:
            self.focus = 'content'
            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
        self.draw()

    def handle_down(self, e):
        """ Forward scroll  to the active tab"""
        delta = e.delta
        self.active_tab.scrolldown(delta)
        self.draw()

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

    def draw(self):
        self.canvas.delete("all")
        self.active_tab.draw(self.canvas, self.chrome.bottom)
        cmds = self.chrome.paint()
        for cmd in cmds:
            cmd.execute(0, self.canvas)


class URL:
    """This class is used to parse the url and request the data from the server"""

    cache = {}

    def __init__(self, url):
        """Initiate the URL class with a scheme, host, port, and path."""
        self.visited_urls = set()
        self.default_headers = {"User-Agent": "default/1.0"}
        self.fragment = None
        url = url.strip()
        if "://" in url:
            self.scheme, url = url.split("://", 1)
            self.scheme = self.scheme.strip()
            if "/" not in url:
                url = url + "/"
            self.host, url = url.split("/", 1)
            self.path = url
            self.path = "/" + self.path

            assert self.scheme in ["http", "https", "file", "about"]

            if "#" in self.path:
                self.path, self.fragment = self.path.split("#", 1)
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
            elif self.scheme == "about":
                self.port = "None"
                self.host = "None"
                self.path = "bookmarks"

        # Handle inline HTML
        elif "data:" in url:
            self.path = url
            self.scheme, url = url.split(":", 1)
            self.port = None

    def __repr__(self):
        fragment_part = "" if self.fragment == None else ", fragment=" + self.fragment
        return "URL(scheme={}, host={}, port={}, path={!r}{})".format(
            self.scheme, self.host, self.port, self.path, fragment_part)

    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""
        if (self.fragment != None):
            return self.scheme + "://" + self.host + port_part + self.path + "#" + self.fragment
        else:
            return self.scheme + "://" + self.host + port_part + self.path

    def origin(self):
        return self.scheme + '://' + self.host + ':' + str(self.port)

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

        headers_text = "\r\n".join("{}: {}".format(k, v))
        headers_text = "\r\n" + user_agent + connection + headers_text
        base_headers = (
            "GET {} HTTP/1.1\r\n".format(self.path)
            + "Host: {}".format(self.host)
            + headers_text
            + "\r\n\r\n"
        ).encode("utf8")
        return base_headers

    def resolve(self, url):
        if "://" in url:
            return URL(url)
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
            return URL(self.scheme + "://" + self.host +
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

    
    def request(self, top_level_url, payload=None, method=None):
        if method == None:
            method = 'POST' if payload else 'GET'
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        

        s.connect((self.host, self.port))
    
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        elif self.scheme == "data":
            return self.handle_data_scheme() 

        elif self.scheme == "about":
            http_body = "<!doctype html>"
            for bookmark in browser.bookmarks:
                http_body += f'<a href="{bookmark}">{bookmark}</a><br>'
            return http_body
        
        query = ''
        if method == 'GET' and payload:
            query = '?' + payload
        
        

        body = "{} {}{} HTTP/1.0\r\n".format(method, self.path, query)
        if payload:
            length = len(payload.encode("utf8"))
            body += "Content-Length: {}\r\n".format(length)
        body += "Host: {}\r\n".format(self.host)
        # NOTE: NEW
        if self.host in COOKIE_JAR:
            cookie, params = COOKIE_JAR[self.host]
            allow_cookie = True
            if top_level_url and params.get('samesite', 'none') == 'lax':
                if method != 'GET':
                    allow_cookie = self.host == top_level_url.host
            if allow_cookie:
                body += 'Cookie: {}\r\n'.format(cookie)
        body += "\r\n" + (payload if payload else "")
        s.send(body.encode("utf8"))

        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}

        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        if 'set-cookie' in response_headers:
            cookie = response_headers['set-cookie']
            params = {}
            if ';' in cookie:
                cookie, rest = cookie.split(';', 1)
                for param in rest.split(';'):
                    if '=' in param:
                        param, value = param.split('=', 1)
                    else:
                        value = 'true'
                    params[param.strip().casefold()] = value.casefold()
            COOKIE_JAR[self.host] = (cookie, params)
    
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        body = response.read()
        s.close()
        return response_headers, body
 






class Chrome:
    def __init__(self, browser):
        self.browser = browser
        self.font = get_font(20, 'normal', 'roman', 'Courier')
        self.font_height = self.font.metrics('linespace')
        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2*self.padding
        plus_width = self.font.measure("+") + 2*self.padding
        self.newtab_rect = Rect(
            self.padding, self.padding,
            self.padding + plus_width,
            self.padding + self.font_height)

        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + \
            self.font_height + 2*self.padding
        self.bottom = self.urlbar_bottom

        back_width = self.font.measure("<") + 2*self.padding
        self.back_rect = Rect(
            self.padding,
            self.urlbar_top + self.padding,
            self.padding + back_width,
            self.urlbar_bottom - self.padding)

        self.address_rect = Rect(
            self.back_rect.top + self.padding,
            self.urlbar_top + self.padding,
            WIDTH - self.padding * 2 - 20,
            self.urlbar_bottom - self.padding,
        )

        # Make a new rectangle for the bookmarks
        self.bookmarks_rect = Rect(
            self.address_rect.right + self.padding,
            self.urlbar_top + self.padding,
            WIDTH - self.padding,
            self.urlbar_bottom - self.padding,
        )
        self.focus = None
        self.address_bar = ""

    def backspace(self):
        self.focus == "address bar"
        self.address_bar = self.address_bar[:-1]  # remove last character

    """
    def click(self, x, y):
        self.focus = None
        # Check if click is a new tab or an open tab
        if self.newtab_rect.containsPoint(x, y):
            self.browser.new_tab(URL("https://browser.engineering/"))

        elif self.back_rect.containsPoint(x, y):
            self.browser.active_tab.go_back()

        elif self.address_rect.containsPoint(x, y):
            self.focus = "address bar"
            self.address_bar = ""

        elif self.bookmarks_rect.containsPoint(x, y):
            if str(self.browser.active_tab.url) in self.browser.bookmarks:
                self.browser.bookmarks.remove(str(self.browser.active_tab.url))
            else:
                self.browser.bookmarks.append(str(self.browser.active_tab.url))

        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).containsPoint(x, y):
                    self.browser.active_tab = tab
                    break
        """
    def click(self, x, y):
        self.focus = None
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                if self.focus:
                    self.focus.is_focused = False
                self.focus = elt
                elt.is_focused = True
                return self.render()
            elif elt.tag == "button":
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent

    def keypress(self, char):
        if self.focus == "address bar":
            self.address_bar += char
            return True
        return False

    def enter(self):
        if self.focus == "address bar":
            self.browser.active_tab.load(URL(self.address_bar))
            self.focus = None

    def paint(self):
        cmds = []
        # Draw white rectangle behind chrome to ensure that Chrome is always on top of tab
        cmds.append(DrawRect(
            Rect(0, 0, WIDTH, self.bottom),
            "white"))
        cmds.append(DrawLine(
            0, self.bottom, WIDTH,
            self.bottom, "black", 1))

        cmds.append(DrawOutline(self.newtab_rect, "black", 1))
        cmds.append(DrawText(self.newtab_rect.left + self.padding,
                    self.newtab_rect.top, "+", self.font, "black"))
        for i, tab in enumerate(self.browser.tabs):
            bounds = self.tab_rect(i)
            cmds.append(DrawLine(
                bounds.left, 0, bounds.left, bounds.bottom,
                "black", 1))
            cmds.append(DrawLine(
                bounds.right, 0, bounds.right, bounds.bottom,
                "black", 1))
            cmds.append(DrawText(
                bounds.left + self.padding, bounds.top + self.padding, "tab {}".format(i), self.font, "black"))

            if tab == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, bounds.bottom, bounds.left, bounds.bottom,
                    "black", 1))
                cmds.append(DrawLine(
                    bounds.right, bounds.bottom, WIDTH, bounds.bottom,
                    "black", 1))

        cmds.append(DrawOutline(self.back_rect, "black", 1))
        cmds.append(DrawText(
            self.back_rect.left + self.padding,
            self.back_rect.top,
            "<", self.font, "black"))

        cmds.append(DrawOutline(self.address_rect, "black", 1))
        url = str(self.browser.active_tab.url)
        cmds.append(DrawText(
            self.address_rect.left + self.padding,
            self.address_rect.top,
            self.address_bar, self.font, "black"))

        if self.focus == "address bar":
            cmds.append(DrawText(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                self.address_bar, self.font, "black"))

            w = self.font.measure(self.address_bar)
            cmds.append(DrawLine(
                self.address_rect.left + self.padding + w,
                self.address_rect.top,
                self.address_rect.left + self.padding + w,
                self.address_rect.bottom,
                "red", 1))
        else:
            url = str(self.browser.active_tab.url)
            cmds.append(DrawText(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                url, self.font, "black"))

        if str(self.browser.active_tab.url) in self.browser.bookmarks:
            cmds.append(DrawRect(self.bookmarks_rect, "yellow"))

        cmds.append(DrawOutline(self.bookmarks_rect, "black", 1))

        return cmds

    def tab_rect(self, i):
        tabs_start = self.newtab_rect.right + self.padding
        tab_width = self.font.measure("Tab X") + 2*self.padding
        return Rect(tabs_start + tab_width * i, self.tabbar_top, tabs_start + tab_width * (i + 1), self.tabbar_bottom)

    def blur(self):
        self.focus = None


'''
EVENT_DISPATCH_JS = \
    "new Node(dukpy.handle).dispatchEvent(dukpy.type)"
'''


EVENT_DISPATCH_JS = \
    "new Node(dukpy.handle).dispatchEvent(new Event(dukpy.type))"


def show_comments():
    out += '<strong></strong>'
    out += '<script src=/comment.js></script>'

def add_entry(params):
    if 'guest' in params and len(params['guest']) <= 100:
        ENTRIES.append(params['guest'])
    return show_comments()


class JSContext:
    def __init__(self, tab, id_list):
        self.id_list = id_list
        
        self.tab = tab
        self.node_to_handle = {}
        self.handle_to_node = {}
        self.interp = dukpy.JSInterpreter()
        self.interp.export_function('log', print)
        self.interp.export_function('querySelectorAll', self.querySelectorAll)
        self.interp.export_function("getAttribute",
            self.getAttribute)
        self.interp.export_function("innerHTML_set", self.innerHTML_set)

        self.interp.export_function("createElement", self.createElement)
        self.interp.export_function("appendChild", self.appendChild)
        self.interp.export_function("insertBefore", self.insertBefore)

        self.interp.export_function("XMLHttpRequest_send", self.XMLHttpRequest_send)

        self.interp.export_function('get_cookies', self.getCookies)
        self.interp.export_function('set_cookies', self.setCookies)

        self.interp.export_function("getChildren", self.getChildren)
        self.interp.evaljs(RUNTIME_JS)
        self.create_id_nodes()

    def getCookies(self):
        cookies = COOKIE_JAR.get(self.tab.url.host, ('', {}))
        if 'httponly' in cookies[1]:
            return ''
        return COOKIE_JAR.get(self.tab.url.host, ('', {}))[0]

    def setCookies(self, cookie):
        cookies = COOKIE_JAR.get(self.tab.url.host, ('', {}))
        if 'httponly' in cookies[1]:
            return ''
        '''
        if 'set-cookie' in cookies[1]:
            print('entered setCookies')
            cookie = cookies[1]['set-cookie']
            params = {}
            if ';' in cookie:
                cookie, rest = cookie.split(';', 1)
                for param in rest.split(';'):
                    if '=' in param:
                        param, value = param.split('=', 1)
                    else:
                        value = 'true'
                    params[param.strip().casefold()] = value.casefold()
            COOKIE_JAR[self.host] = (cookie, params)
        '''

    # NOTE; new code
    def XMLHttpRequest_send(self, method, url, body):
        """ Just call Request """
        full_url = self.tab.url.resolve(url)
        if not self.tab.allowed_request(full_url):
            raise Exception('Cross-origin XHR request blocked by CSP') 
        if full_url.origin() != self.tab.url.origin():
            raise Exception('Cross-origin XHR request not allowed')
        headers, out = full_url.request(self.tab.url, body)
        return out

    def create_id_nodes(self):
        for node in self.id_list:
            javascript_string = '{} = new Node({})'.format(node.attributes['id'], self.get_handle(node))
            self.interp.evaljs(javascript_string)
        
    def remove_id_node(self, node):
        self.id_list.remove(node)
        javascript_string = 'delete {}'.format(node.attributes['id'])
        self.interp.evaljs(javascript_string)

    def getChildren(self, handle):
        elt = self.handle_to_node[handle]
        elements = []
        for child in elt.children:
            if isinstance(child, Element):
                elements.append(self.get_handle(child))

        return elements


    def createElement(self, tagName):
        elt = Element(tagName, {}, None)
        if elt:
            print('!dbg [PY createElement] is NOT null')
        else:
            print('!dbg [PY createElement] is null')
        return self.get_handle(elt)

    def appendChild(self, parent_handle, child_handle):
        print('!dbgentering appendChild----')
        parent = self.handle_to_node[parent_handle]
        child = self.handle_to_node[child_handle]
        child.parent = parent
        parent.children.append(child)
        self.tab.render()

    def insertBefore(self, parent_handle, child_handle, sibling_handle=None):
        print("!dbg ENTERED insertBefore")
        parent = self.handle_to_node[parent_handle]
        child = self.handle_to_node[child_handle]
        child.parent = parent
        if sibling_handle is None:
            parent.children.append(child)
        else:
            sibling = self.handle_to_node[sibling_handle]
            sibling_index = parent.children.index(sibling)
            parent.children.insert(sibling_index, child)
        self.tab.render()

    def run(self, code):
        return self.interp.evaljs(code)

    def querySelectorAll(self, selector_text):
        selector = CSSParser(selector_text).selector()
        nodes = [node for node
                 in tree_to_list(self.tab.nodes, [])
                 if selector.matches(node)]
        return [self.get_handle(node) for node in nodes]

    def get_handle(self, elt):
        if elt:
            print('!dbg [PY get_handle] elt is NOT null')
        else:
            print('!dbg [PY get_handle] elt is null') 
        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt
        else:
            handle = self.node_to_handle[elt]
        if handle:
            print('!dbg [PY get_handle] handle is NOT null')
        else:
            print('!dbg [PY get_handle] handle is null')
        return handle

    def getAttribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        attr = elt.attributes.get(attr, None)
        return attr if attr else ''

    def dispatch_event(self, type, elt):
        handle = self.node_to_handle.get(elt, -1)
       # self.interp.evaljs(EVENT_DISPATCH_JS, type=type, handle=handle)
        
        do_default = self.interp.evaljs(
            EVENT_DISPATCH_JS, type=type, handle=handle)
        return not do_default

    '''
    def innerHTML_set(self, handle, s):
        doc = HTMLParser('<html><body>' + s + '</body></html>').parse() 
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes

        for child in elt.children:
            child.parent = elt
    '''
    def innerHTML_set(self, handle, s):
        doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]

        for child in tree_to_list(elt, []):
            if isinstance(child, Element):
                if 'id' in child.attributes:
                    self.remove_id_node(child)
        
        elt.children = new_nodes

        for child in tree_to_list(elt, []):
            if isinstance(child, Element):
                if 'id' in child.attributes:
                    self.id_list.append(child)

        for child in elt.children:
            child.parent = elt
        self.tab.render()
        self.create_id_nodes()

class Tab:

    def __init__(self, tab_height, browser):
        self.scroll = 0
        self.tab_height = tab_height
        self.history = []
        self.browser = browser
        self.focus = None

    def __repr__(self):
        return "Tab(history={})".format(self.history)

    def allowed_request(self, url):
        return self.allowed_origins == None or \
        url.origin() in self.allowed_origins

    def enter(self):
        if self.focus:
            elt = self.focus.parent
            while elt:
                if elt.tag == 'form' and "action" in elt.attributes:
                    return self.submit_form(elt)
                else:
                    elt = elt.parent


    def middleClick(self, x_pos, y_pos, browser):
        x, y = x_pos, y_pos
        y += self.scroll

        objs = [obj for obj in tree_to_list(
            self.document, []) if obj.x <= x < obj.x + obj.width and obj.y <= y < obj.y + obj.height]
        if not objs:
            return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == 'a' and 'href' in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                browser.new_tab(url)
                browser.active_tab = self
                return
            elt = elt.parent

    def draw(self, canvas, offset):
        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom < self.scroll:
                continue
            cmd.execute(self.scroll - offset, canvas)

    def click(self, x_pos, y_pos):
        x, y = x_pos, y_pos
        y += self.scroll
        objs = [obj for obj in tree_to_list(
            self.document, []) if obj.x <= x < obj.x + obj.width and obj.y <= y < obj.y + obj.height]

        if not objs:
            return
        elt = objs[-1].node

        while elt:
            if isinstance(elt, Text):
                pass
            
            elif elt.tag == 'button':
                if self.js.dispatch_event('click', elt): return

                # Find the form that it's in by walking up the tree
                while elt:
                    if elt.tag == 'form' and 'action' in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent

            elif elt.tag == 'input':
                if self.js.dispatch_event('click', elt): return

                elt.attributes['value'] = ''

                if elt.attributes.get('type', 'text') == 'checkbox':
                    if 'checked' in elt.attributes:
                        del elt.attributes['checked']
                    else:
                        elt.attributes['checked'] = ''

                if self.focus:
                    self.focus.is_focused = False
                self.focus = elt
                elt.is_focused = True
                return self.render()

            elif elt.tag == 'a' and 'href' in elt.attributes:
                if self.js.dispatch_event('click', elt): return

                if elt.attributes.get("href")[1:] == '#':
                    return self.scroll_to(elt.attributes.get("href")[1:])
                else:
                    url = self.url.resolve(elt.attributes['href'])
                    return self.load(url)
            elt = elt.parent
    """
    def click(self, x, y):
        self.focus = None
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                if self.focus:
                    self.focus.is_focused = False
                self.focus = elt
                elt.is_focused = True
                return self.render()
            elif elt.tag == "button":
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent
        """
    def scrolldown(self, delta):
        """Scroll down by SCROLL_STEP pixels."""
        # Default for Windows and Linux, divide by 120 for MacOS omegalul a single ternary
        '''
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
        '''

        if delta > 0:
            if self.scroll > 0:
                self.scroll -= SCROLL_STEP
                # self.draw()
        else:
            max_y = max(self.document.height + 2 * VSTEP - self.tab_height, 0)
            self.scroll = min(self.scroll + SCROLL_STEP, max_y)
            # self.draw()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def scroll_to(self, fragment):
        for obj in tree_to_list(self.document, []):
            if (isinstance(obj.node, Element) and obj.node.attributes.get("id") == fragment):
                self.scroll = obj.y

    '''
    def load(self, url, payload=None, method='GET', view_source: Optional[bool]=False):
        """Load the given URL and convert text tags to character tags."""
        # Note: Test for testing extra headers
        self.url = url
        self.history.append(url)
        body = url.request(payload, method=method)

        if view_source:
            print(body)
        else:
            DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()
            self.rules = DEFAULT_STYLE_SHEET.copy()
            self.nodes = HTMLParser(body).parse()

            # Gather all the relative URL for each linked style sheet
            links = [node.attributes["href"]
                     for node in tree_to_list(self.nodes, [])
                     if isinstance(node, Element)
                     and node.tag == "link"
                     and node.attributes.get("rel") == "stylesheet"
                     and "href" in node.attributes]

            scripts = [node.attributes['src'] for node \
                    in tree_to_list(self.nodes, [])
                    if isinstance(node, Element)
                    and node.tag == 'script'
                    and 'src' in node.attributes]

            self.js = JSContext(self)
            for script in scripts:
                body = url.resolve(script).request()
                print('Script returned: ', dukpy.evaljs(body))
                try: 
                    self.js.run(body)
                except dukpy.JSRuntimeError as e:
                    print('Script', script, 'crashed', e)

            self.document = DocumentLayout(self.nodes)
            rules = DEFAULT_STYLE_SHEET.copy()

            # Convert relative URLs to full URLS:
            for link in links:
                try:
                    body = url.resolve(link).request(self.browser)
                # ignore stylesheets that fail to download
                except Exception:
                    continue
                self.rules.extend(CSSParser(body).parse())

            style(self.nodes, sorted(self.rules, key=cascade_priority))
            self.document.layout()
            if url.fragment:
                self.scroll_to(url.fragment)
            self.display_list = []
            paint_tree(self.document, self.display_list)
        self.render()
    '''
    def load(self, url, payload=None, method='GET'):
        self.scroll = 0
        self.url = url
        self.history.append(url)
        # NOTE: new
        headers, body = url.request(self.url, payload)
        self.allowed_origins = None
        if 'content-security-policy' in headers:
            csp = headers['content-security-policy'].split()
            if len(csp) > 0 and csp[0] == 'default-src':
                self.allowed_origins = []
                for origin in csp[1:]:
                    self.allowed_origins.append(URL(origin).origin())
        self.nodes = HTMLParser(body).parse()

        id_list = []
        for node in tree_to_list(self.nodes, []):
            if isinstance(node, Element):
                if 'id' in node.attributes:
                    id_list.append(node)


        #self.js = JSContext(self)
        
        scripts = [node.attributes["src"] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        
        self.js = JSContext(self, id_list)

        for script in scripts:
            #body = url.resolve(script).request()
            # NOTE: new
            script_url = url.resolve(script)
            if not self.allowed_request(script_url):
                print('Blocked script', script, 'due to CSP')
                continue
            header, body = script_url.request(url)
            try:
                self.js.run(body)
            except dukpy.JSRuntimeError as e:
                print("Script", script, "crashed", e)

        DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()
        self.rules = DEFAULT_STYLE_SHEET.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]
        for link in links:
            script_url = url.resolve(link)
            if not self.allowed_request(script_url):
                print('Blocked style', link, 'due to CSP')
                continue
            
            try:
                #body = url.resolve(link).request()
                header, body = script_url.request(url)
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        self.render()


    def render(self):
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event('keydown', self.focus): return
            self.focus.attributes["value"] += char
            self.render()

    def submit_form(self, elt):
        """In charge of finding all input elements, encoding them, and sending the post request """
        if self.js.dispatch_event('submit', elt): return

        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element)
                  and node.tag == "input"
                  and "name" in node.attributes]
        body = ''
        for input in inputs:
            name = input.attributes['name']
            value = input.attributes.get('value', '')

#            if name == 'check':
            name = urllib.parse.quote(name)
            value = urllib.parse.quote(value)
            body += '&' + name + '=' + value

#            else: pass

        body = body[1:]
        url = self.url.resolve(elt.attributes['action'])
        method = elt.attributes.get('method')
        if method == None:
            method = 'GET'
        self.load(url, body, method)


if __name__ == "__main__":
    import sys
    body = URL(sys.argv[1]).request()
    nodes = HTMLParser(body).parse()
    # Browser().load(URL(sys.argv[1]))
    Browser().new_tab(URL(sys.argv[1]))
    tkinter.mainloop()

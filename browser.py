import socket, ssl, time, tkinter, platform, re, unicodedata
from typing import Optional, Dict

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18
GRINNING_FACE_IMAGE = None


def lex(body):
    """Show the body of the HTML page, without the tags."""

    emoji_pattern = "&#x.*?;"
    text = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            text += c

    matches = re.finditer(emoji_pattern, text)
    for match in matches:
        print(
            "match: ", match.group(0), " start: ", match.start(), " end: ", match.end()
        )
    return text


def layout(text):
    """Layout the text on the screen."""

    new_line = False
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    grapheme_cluster = ""
    for c in text:
        if c == "\\":
            new_line = True
            continue
        elif new_line:
            if c == "n":
                cursor_y += VSTEP * 2
                cursor_x = HSTEP
                continue
            new_line = False

        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_x = HSTEP
            cursor_y += VSTEP
    return display_list


class Browser:
    """A simple browser that can load and display a web page."""

    def __init__(self):
        global GRINNING_FACE_IMAGE
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
        )
        self.canvas.pack()
        GRINNING_FACE_IMAGE = tkinter.PhotoImage(file="openmoji/1F600.png")
        self.scroll = 0
        self.scrolling = False
        self.last_y = 0
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<MouseWheel>", self.scrolldown)

    """
        self.windows.bind("<Button-1>", self.start_scroll)
        self.window.bind("<B!-Motion>", self.perform_scroll)
        self.window.bind("<ButtonRelease-1>", self.end_scroll)

    """

    def scrolldown(self, e):
        """Scroll down by SCROLL_STEP pixels."""

        # Default for Windows and Linux
        delta = e.delta if hasattr(e, "delta") else None
        if hasattr(e, "delta"):
            # For MacOS
            if platform.system() == "Darwin":
                delta = e.delta / 120

        # Mouse wheel down. On Windows, e.delta < 0 => scroll down.
        # NOTE: on Windows delta is positive for scroll up. On MacOS divid delta by 120
        #      On Linux you need to use differenct events to scroll up and scroll down
        if (delta is not None and delta < 0) or e.keysym == "Down":
            if self.display_list[-1][1] * 1.1 > self.scroll + HEIGHT:
                self.scroll += SCROLL_STEP
                self.draw()
            else:
                print("at bottom, cannot scroll further down")

        elif (delta is not None and delta > 0) or e.keysym == "Up":
            if self.scroll > 0:
                self.scroll -= SCROLL_STEP
                self.draw()
            else:
                print("already at top, cannot scroll further up")

    def draw(self):
        """Draw the display list."""
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT:
                continue
            if y + VSTEP < self.scroll:
                continue
            # print("c: ", c)
            if c == "\N{GRINNING FACE}":
                print("grinning face")
                self.canvas_create_image(x, y - self.scroll, image=GRINNING_FACE_IMAGE)
                return
            self.canvas.create_text(x, y - self.scroll, text=c)

        if self.display_list[-1][1] > HEIGHT:
            self.canvas.create_rectangle(
                WIDTH - 8,
                self.scroll / self.display_list[-1][1] * HEIGHT,
                WIDTH,
                HEIGHT / self.display_list[-1][1] * HEIGHT
                + (self.scroll / self.display_list[-1][1]) * HEIGHT,
                fill="blue",
            )

    def load(self, url, view_source: Optional[bool] = False):
        """Load the given URL and convert text tags to character tags."""

        # Note: Test for testing extra headers

        body = url.request().replace("&lt;", "<").replace("&gt;", ">")

        print(
            "matches: ",
        )
        if view_source:
            print(body)
        else:
            body = body.replace("<p>", "<p>\\n")
            cursor_x, cursor_y = HSTEP, VSTEP
            text = lex(body)
            self.display_list = layout(text)
            self.draw()


class URL:
    """
    This class is used to parse the url and request the data from the server
    """

    cache = {}

    def format_headers(self, headers):
        """Format the given header dictionary into a string."""
        user_agent_found, connection_found = False, False
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

        headers_text = "\r\n".join("{}: {}".format(k, v) for k, v in headers.items())
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
        creation_time = time.time()
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
            cached_headers, cached_body, cached_time, max_age = self.get_from_cache(url)
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
                encoding_response[encoding_position + 8 :]
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

    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()

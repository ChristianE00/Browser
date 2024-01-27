import socket, ssl
import time
from typing import Optional, Dict


def show(body):
    """Show the body of the HTML page, without the tags.
    """
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")


def load(url, view_source: Optional[bool] = False):
    """Load the given URL and convert text tags to character tags.
    """
    # Note: Test for testing extra headers
    body = url.request().replace("&lt;", "<").replace("&gt;", ">")
    if view_source:
        print(body)
    else:
        show(body)


class URL:
    """
    This class is used to parse the url and request the data from the server
    """
    cache = {}
    def format_headers(self, headers):
        """Format the given header dictionary into a string.
        """
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
        # remove the headers that are already in the default headers
        for key in remove_list:
            del headers[key]

        headers_text = "\r\n".join("{}: {}".format(k, v) for k, v in headers.items())
        headers_text = "\r\n" + user_agent + connection + headers_text
        base_headers = ("GET {} HTTP/1.1\r\n".format(self.path) + \
                    "Host: {}".format(self.host) + \
                    headers_text + "\r\n\r\n").encode("utf8")
        return base_headers


    def __init__(self, url):
        """Initiate the URL class with a scheme, host, port, and path.
        """

    
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
                print("hit else-------------")
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
        #Handle inline HTML
        elif "data:" in url:
            self.path = url
            self.scheme, url = url.split(":", 1)
            self.port = None


    def cache_response(self, url, headers, body):
        # Extract max-age from headers
        cache_control = headers.get('Cache-Control', '')
        max_age = None
        if cache_control:
            directives = cache_control.split(',')
            for directive in directives:
                key, sep, val = directive.strip().partition('=')
                if key.lower() == 'max-age':
                    try:
                        max_age = int(val)
                    except ValueError:
                        pass
        #print("body:", body)
        # Store response in cache with current time and max-age
        URL.cache[url] = (headers, body, time.time(), max_age)
       # print("length of cache:", len(URL.cache))
    
    def get_from_cache(self, url):
        #print("length of cache:", len(URL.cache))
        cached = URL.cache.get(url)
        if cached:
            #print("Cache hit")
            headers, body, cached_time, max_age = cached
            # Check if response is still fresh
            if max_age is None or (time.time() - cached_time) <= max_age:
                return headers, body, cached_time, max_age
        return None, None, None, None

    def handle_redirect(self, response):
        """Handles the redirect from the server
        """
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            if header.casefold() == "location":
                if "://" not in value:
                    value = self.scheme.strip() + "://" + self.host.strip() + value.strip()
                if value in self.visited_urls:
                    return "Error: Redirect loop detected"
                self.visited_urls.add(value.strip())
                return URL(value).request(None, self.visited_urls)
        return "Error: Redirect without location header"



    def handle_local_file(self):
        with open(self.path, "r", encoding="utf8") as f:
            return f.read()


    def handle_data_scheme(self):
        return self.path


    def create_socket(self):
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
        my_headers =  ("GET {} HTTP/1.1\r\n".format(self.path) + \
                       "Host: {}\r\nConnection: close\r\nUser-Agent: SquidWeb\r\n\r\n".format(self.host)) \
                       .encode("utf8")
        if headers:
            my_headers = self.format_headers(headers)
        s.send(my_headers)


    def read_response(self, s):
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        return response, status


    def read_headers(self, response):
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        return response_headers


    def request(self, headers: Optional[Dict[str, str]] = None, visited_urls=None):
        """Handles getting the page source from the server or local file.
        """
        if self.scheme == "file":
            return self.handle_local_file()
        elif self.scheme == "data":
            return self.handle_data_scheme()
        elif self.scheme == "https" or self.scheme == "http":
            url = self.scheme.strip() + "://" + self.host.strip() + self.path.strip()
            if(len(URL.cache) > 0):
                cached_headers, cached_body, cached_time, max_age = self.get_from_cache(url)
                #if cached_body and (time.time() - cached_time) <= max_age:
                if cached_body:
                    #print("Using cached response")
                    return cached_body
           # else: 
          #      print("Fetching from server")

            s = self.create_socket()
            self.send_request(s, headers)
            response, status = self.read_response(s)
            
            # other request code
            if visited_urls is not None:
                self.visited_urls = visited_urls
            self.visited_urls.add(url)
            
            # handle redirect
            if int(status) >= 300 and int(status) < 400: 
                return self.handle_redirect(response)

            response_headers = self.read_headers(response)
            assert "transfer-encoding" not in response_headers
            assert "content-encoding" not in response_headers
            #print( "response headers: ", response_headers)
            encoding_response = response_headers.get("content-type", "utf8")
            encoding_position = encoding_response.find("charset=")
            encoding = encoding_response[encoding_position + 8:] if encoding_position != -1 else "utf8"
            if "cache-control" in response_headers:
               # print("cache-control found")
                cache_response = response_headers["cache-control"].strip()
                if "max-age" in cache_response:
                    #print("Caching response")
                    max_age = cache_response.split("=")[1]
                    if int(max_age) > 0:
                        body = response.read()
                        s.close()
                     #   print("url:", url)
                       # print("first body:", body)
                        self.cache_response(url, response_headers, body)
                        return body
                    
            body = response.read() 
            s.close()
            return body



    


if __name__ == "__main__":
    import sys
#    load(URL(sys.argv[1]), True)

    load(URL(sys.argv[1]))




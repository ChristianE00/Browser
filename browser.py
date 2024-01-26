import socket, ssl
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
    '''
    # Note: Test for testing extra headers
    extra_client_headers = {"User-Agent" : "d"}
    body = url.request(headers=extra_client_headers)
    '''
    body = url.request().replace("&lt;", "<").replace("&gt;", ">")
    if view_source:
        print(body)
    else:
        show(body)


class URL:
    """
    This class is used to parse the url and request the data from the server
    """
    def format_headers(self, headers):
        """Format the given header dictionary into a string.
        """
        user_agent_found, connection_found = False, False
        user_agent = "\r\nUser-Agent: SquidWeb"
        connection = "\r\nConnection: close"
        headers_text = "\r\n".join("{}: {}".format(k, v) for k, v in headers.items())
        remove_list = []
        for key in headers.keys():
            if key.lower() == "user-agent":
                user_agent = "\r\nUser-Agent: " + headers[key]
                remove_list.append(key)
            if key.lower() == "connection":
                connection = "\r\n" + key + ": " + headers[key]
                remove_list.append(key)
        # remove the headers that are already in the default headers
        for key in remove_list:
            del headers[key]
        headers_text = "\r\n".join("{}: {}".format(k, v) for k, v in headers.items())
        headers_text += connection + user_agent
        base_headers = ("GET {} HTTP/1.1\r\n".format(self.path) + \
                    "Host: {}\r\n".format(self.host) + \
                    headers_text + "\r\n\r\n").encode("utf8")
#        print("header: ", headers_text)
        return base_headers


    def __init__(self, url):
        """Initiate the URL class with a scheme, host, port, and path.
        """
        if "://" in url:
            self.scheme, url = url.split("://", 1)
            if "/" in url:
                self.host, url = url.split("/", 1)
            else:
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
        #Handle inline HTML
        elif "data:" in url:
            self.path = url
            self.scheme, url = url.split(":", 1)
            self.port = None
            print("self.scheme: ", self.scheme, "url: ", url)

    def request(self, headers: Optional[Dict[str, str]] = None):
        """Handles getting the page source from the server or local file.
        """

        # Check for local file first'
        if self.scheme == "file":
            print('file scheme found')
            with open(self.path, "r", encoding="utf8") as f:
                return f.read()
        elif self.scheme == "data":
            print('data scheme found')
            return self.path
        elif self.scheme == "https" or self.scheme == "http":
            #sending a request to the server`
            s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
            if self.scheme == "https":
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)
            s.connect((self.host, self.port))

            #Handle the headers
            my_headers =  ("GET {} HTTP/1.1\r\n".format(self.path) + \
                           "Host: {}\r\nConnection: close\r\nUser-Agent: SquidWeb\r\n\r\n".format(self.host)) \
                           .encode("utf8")
            if headers:
                my_headers = self.format_headers(headers)
            s.send(my_headers)
            
            #Reading the response form the server
            response = s.makefile("r", encoding="utf8", newline="\r\n")
            statusline = response.readline()
            version, status, explanation = statusline.split(" ", 2)
            
            response_headers = {}
            while True:
                line = response.readline()
                if line == "\r\n": break
                #Next will come the headers
                header, value = line.split(":", 1)
                response_headers[header.casefold()] = value.strip()
            
            
            #Ensure that non of the data is being sent in an unusual way
            assert "transfer-encoding" not in response_headers
            assert "content-encoding" not in response_headers
            encoding_response = response_headers.get("content-type", "utf8")
            encoding_position = encoding_response.find("charset=")
            encoding = encoding_response[encoding_position + 8:] if encoding_position != -1 else "utf8"

            body = response.read() 
            s.close()
            return body




    


if __name__ == "__main__":
    import sys
#    load(URL(sys.argv[1]), True)

    load(URL(sys.argv[1]))




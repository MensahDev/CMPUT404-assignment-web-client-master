#!/usr/bin/env python3
# coding: utf-8
# Copyright 2016 Abram Hindle, https://github.com/tywtyw2002, and https://github.com/treedust
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it

import sys
import socket
import re
# you may use urllib to encode data appropriately
import urllib.parse

# for debugging
DEBUG = 0
DEFAULT_HTTP_PORT = 80

def help():
    print("httpclient.py [GET/POST] [URL]\n")

class HTTPResponse(object):
    def __init__(self, code=200, body=""):
        self.code = code
        self.body = body
        self.headers = dict()

    def __str__(self):
        ''' for debugging '''
        s = {"code": self.code, "body": self.body, "headers": self.headers}
        return str(s)

class HTTPClient(object):
    #def get_host_port(self,url):

    def connect(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            return True
        except Exception as e:
            print("Problem in connection to %s on port %d" % (host, port))
        return False

    def get_code(self, data):
        ''' the work of get_code, get_headers and get_body is
        done by 1 parse of response in parse_response(..) '''
        return None

    def get_headers(self, data):
        return None

    def get_body(self, data):
        return None
    
    def sendall(self, data):
        self.socket.sendall(data.encode('utf-8'))
        
    def close(self):
        self.socket.close()

    # read everything from the socket
    def recvall(self, sock):
        buffer = bytearray()
        done = False
        while not done:
            part = sock.recv(1024)
            if (part):
                buffer.extend(part)
            else:
                done = not part
        return buffer.decode('utf-8')

    def GET(self, url, args=None):
        code = 500
        body = ""
        valid, host, port, path = self.parse_url(url)
        if not valid:
            print("[GET] Malformed HTTP URL: %s" % url)
            return HTTPResponse(code, body)

        if not port:
            # when if requesting on a URL with no port use default
            # port 80
            port = DEFAULT_HTTP_PORT

        if not path or path == "":
            path = "/"

        if not self.connect(host, port):
            return HTTPResponse(code, body)

        # got sample http GET request format from
        # curl -v http://www.cs.ualberta.ca
        req = "GET " + path + " HTTP/1.1\r\n" 
        req += "Host: " + host + ":" + str(port) + "\r\n"
        req += "User-Agent: " + "curl/7.71.1" + "\r\n"
        req += "Accept: " + "*/*" + "\r\n"
        req += "\r\n"
        req += path

        if DEBUG:
            print("[GET] Requesting...")
            print(req + "\n********************")

        self.sendall(req)
        response = self.recvall(self.socket)
        self.close()

        if DEBUG:
            print("*****Response:******")
            print(response + "\n********************")

        return self.parse_response(response)

    def POST(self, url, args=None):
        '''
        POST on URL.

        TODO: GET and POST have a lot of common code: scope of refactoring
        '''
        code = 500
        body = ""

        valid, host, port, path = self.parse_url(url)
        if not valid:
            print("[POST] Malformed HTTP URL: %s" % url)
            return HTTPResponse(code, body)

        if not port:
            # when if requesting on a URL with no port use default
            # port 80
            port = DEFAULT_HTTP_PORT

        if not path or path == "":
            path = "/"

        if not self.connect(host, port):
            return HTTPResponse(code, body)

        # got sample http POST request format from
        # curl -v -d "a=aaa&b=bbbb" -X POST http://127.0.0.1:3000
        if args:
            payload = urllib.parse.urlencode(args)
            payload_len = len(payload)
        else:
            payload_len = 0

        req = "POST " + path + " HTTP/1.1\r\n"
        req += "Host: " + host + ":" + str(port) + "\r\n"
        req += "User-Agent: " + "curl/7.71.1" + "\r\n"
        req += "Accept: " + "*/*" + "\r\n"
        req += "Content-Length: " + str(payload_len) + "\r\n"
        req += "Content-Type: application/x-www-form-urlencoded\r\n"
        req += "\r\n"
        if args:
            req += payload

        if DEBUG:
            print("[POST] Requesting...")
            print(req + "\n********************")

        self.sendall(req)
        response = self.recvall(self.socket)
        self.close()

        if DEBUG:
            print("*****Response:******")
            print(response + "\n********************")

        return self.parse_response(response)

    def parse_url(self, url):
        '''
        A valid URL starts with http:// or https://.
        Then has a host and a port separated by comma.
        This returns <valid>, host, port, path
        where, valid is True/False, and host and port from the url
        '''
        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme
        if scheme != "http" and scheme != "https":
            return False, None, None, None

        return True, parsed.hostname, parsed.port, parsed.path

    def parse_response(self, response_str):
        '''
        Parse an http response as a string, extract body, status code and 
        headers, and return an httpclient.HTTPResponse object
        '''
        response_obj = HTTPResponse(500, '')
        lines = response_str.split("\n")

        if len(lines) == 0:
            return response_obj

        if not lines[0].startswith('HTTP/1.0 ') and not lines[0].startswith('HTTP/1.1 '):
            if DEBUG:
                print("Bad 1st line in response. Expected HTTP/1.0 or HTTP/1.1")
            return response_obj

        resp_line_pattern = re.compile("HTTP/1\.. (\d+) .*")
        matches = resp_line_pattern.match(lines[0])

        if not matches:
            if DEBUG:
                print("Bad 1st line in response: %s" % lines[0])
            return response_obj

        code = int(matches.group(1))
        response_obj.code = code

        # parse headers
        i = 1
        while i < len(lines):
            header_line = lines[i].strip()
            if header_line == "":
                break
            tok = header_line.split(":")

            if len(tok) < 2:
                # header_name: header_val is not there
                if DEBUG:
                    print("[WARN] Bad header line::: %s" % header_line)
            else:
                header_name = tok[0].strip()
                header_val  = ''.join(tok[1:])
                header_val  = header_val.strip()
                response_obj.headers[header_name] = header_val

            i += 1

        # extract body if exists
        body = ''
        if i+1 < len(lines):
            body = lines[i+1]

        response_obj.body = body
        return response_obj


    def command(self, url, command="GET", args=None):
        if (command == "POST"):
            return self.POST( url, args )
        else:
            return self.GET( url, args )
    
if __name__ == "__main__":
    client = HTTPClient()
    command = "GET"
    if (len(sys.argv) <= 1):
        help()
        sys.exit(1)
    elif (len(sys.argv) == 3):
        print(client.command( sys.argv[2], sys.argv[1] ))
    else:
        print(client.command( sys.argv[1] ))

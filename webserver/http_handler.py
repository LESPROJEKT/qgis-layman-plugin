# -*- coding: utf-8 -*-
"""
Created on Wed Aug 16 12:38:25 2023

@author: Honza
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import tempfile
import os
import urllib.parse

class CallbackHandler(BaseHTTPRequestHandler):
    def write_code(self, value):
        path = tempfile.gettempdir() + os.sep + "atlas" + os.sep + "auth.txt"    
        with open(path, "w") as f:
            f.write(value)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'code' in query_params:
            code = query_params['code'][0]
            self.write_code(code)
            self.wfile.write(b"Authorization code obtained. You can now switch back to QGIS and continue.")
        else:
            self.wfile.write(b"Layman QGIS.")

def run_server(server_class=HTTPServer, handler_class=CallbackHandler, port=7070):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()

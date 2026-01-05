from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            return

        self.send_response(404)
        self.end_headers()


def run() -> None:
    server = HTTPServer(("0.0.0.0", 8000), HealthHandler)
    print("Sample app listening on :8000")
    server.serve_forever()


if __name__ == "__main__":
    run()

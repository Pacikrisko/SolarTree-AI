"""Wi-Fi and partial sensor uploads for the SolarTree Pico 2 W."""
import json
import time

HOST = "https://solartree.pgknma.space/"
DEVICE_CODE = "IVAN-TREE-0001"
INTERVAL = 30

# Google Trust Services public root for the Render edge.
GTS_ROOT_R4 = """-----BEGIN CERTIFICATE-----
MIICCTCCAY6gAwIBAgINAgPlwGjvYxqccpBQUjAKBggqhkjOPQQDAzBHMQswCQYD
VQQGEwJVUzEiMCAGA1UEChMZR29vZ2xlIFRydXN0IFNlcnZpY2VzIExMQzEUMBIG
A1UEAxMLR1RTIFJvb3QgUjQwHhcNMTYwNjIyMDAwMDAwWhcNMzYwNjIyMDAwMDAw
WjBHMQswCQYDVQQGEwJVUzEiMCAGA1UEChMZR29vZ2xlIFRydXN0IFNlcnZpY2Vz
IExMQzEUMBIGA1UEAxMLR1RTIFJvb3QgUjQwdjAQBgcqhkjOPQIBBgUrgQQAIgNi
AATzdHOnaItgrkO4NcWBMHtLSZ37wWHO5t5GvWvVYRg1rkDdc/eJkTBa6zzuhXyi
QHY7qca4R9gq55KRanPpsXI5nymfopjTX15YhmUPoYRlBtHci8nHc8iMai/lxKvR
HYqjQjBAMA4GA1UdDwEB/wQEAwIBhjAPBgNVHRMBAf8EBTADAQH/MB0GA1UdDgQW
BBSATNbrdP9JNqPV2Py1PsVq8JQdjDAKBggqhkjOPQQDAwNpADBmAjEA6ED/g94D
9J+uHXqnLrmvT/aDHQ4thQEd0dlq7A/Cr8deVl5c1RxYIigL9zC2L7F8AjEA8GE8
p/SgguMh1YQdc4acLa/KNJvxn7kjNuK8YAOdgLOaVsjh4rsUecrNIdSUtUlD
-----END CERTIFICATE-----
"""


def read_config(name):
    try:
        with open("/" + name, "r") as config_file:
            value = json.load(config_file)
        if isinstance(value, dict):
            return value
    except (OSError, ValueError):
        pass
    return {}


class SolarLink:
    def __init__(self):
        config = read_config("wifi.json")
        self.ssid = config.get("ssid")
        self.password = config.get("password", "")
        self.key = read_config("device.json").get("key")
        self.radio = None
        self.pool = None
        self.tls = None
        self.stage = "Wi-Fi"
        self.status = "Set wifi.json"
        self.ready = False
        self.next_try = 0
        self.retry = 10
        if not isinstance(self.ssid, str) or not self.ssid or not isinstance(self.password, str):
            return
        if not isinstance(self.key, str) or not (self.key and all(33 <= ord(c) <= 126 for c in self.key)):
            self.key = None
        try:
            import wifi
            self.radio = wifi.radio
            self.status = "Connecting..."
        except (ImportError, RuntimeError):
            self.status = "Wi-Fi unavailable"

    def display(self):
        online = self.radio is not None and self.ready and self.radio.connected
        return ("Wi-Fi: online" if online else "Wi-Fi: offline", self.status[:16])

    def post(self, sample):
        import socketpool
        import ssl
        if self.pool is None:
            self.pool = socketpool.SocketPool(self.radio)
        if self.tls is None:
            self.stage = "Load CA"
            context = ssl.create_default_context()
            context.load_verify_locations(cadata=GTS_ROOT_R4)
            self.tls = context
        self.stage = "DNS"
        self.pool.getaddrinfo(HOST, 443, self.pool.AF_INET, self.pool.SOCK_STREAM)
        self.stage = "Socket"
        sock = self.pool.socket(self.pool.AF_INET, self.pool.SOCK_STREAM)
        try:
            self.stage = "TLS"
            sock.settimeout(12)
            sock = self.tls.wrap_socket(sock, server_hostname=HOST)
            sock.settimeout(12)
            sock.connect((HOST, 443))
            self.stage = "Send"
            body = json.dumps(sample).encode("utf-8")
            headers = ("POST /api/device/{}/sensors HTTP/1.1\r\n"
                       "Host: {}\r\nX-Device-Key: {}\r\n"
                       "Content-Type: application/json\r\nContent-Length: {}\r\n"
                       "Connection: close\r\n\r\n").format(DEVICE_CODE, HOST, self.key, len(body))
            remaining = memoryview(headers.encode("ascii") + body)
            while len(remaining):
                count = sock.send(remaining)
                if not count:
                    raise OSError("closed")
                remaining = remaining[count:]
            self.stage = "Reply"
            sock.settimeout(20)
            line = bytearray()
            chunk = bytearray(64)
            while len(line) < 256:
                count = sock.recv_into(chunk, len(chunk))
                if not count:
                    break
                line.extend(chunk[:count])
                if b"\r\n" in bytes(line):
                    first = bytes(line).split(b"\r\n", 1)[0].split()
                    if len(first) >= 2 and first[0].startswith(b"HTTP/"):
                        return int(first[1])
                    break
            raise OSError("incomplete response")
        finally:
            sock.close()

    def tick(self, bme, mq8):
        if self.radio is None or time.monotonic() < self.next_try:
            return
        delay = self.retry
        try:
            if not self.ready or not self.radio.connected:
                self.stage = "Wi-Fi"
                self.ready = False
                self.radio.connect(self.ssid, self.password, timeout=6)
                self.ready = True
            if not self.key:
                self.status = "Set device.json"
                delay = INTERVAL
            else:
                self.stage = "Sensor"
                sample = {"temperature_c": round(bme.temperature, 2),
                          "humidity_pct": round(bme.relative_humidity, 2),
                          "mq8_adc_raw": mq8.value}
                self.stage = "Network"
                status = self.post(sample)
                self.status = "Upload OK" if status == 200 else "HTTP {}".format(status)
                if status == 200:
                    self.retry = 10
                    delay = INTERVAL
                else:
                    self.retry = min(120, delay * 2)
        except (OSError, RuntimeError, ValueError, ImportError, MemoryError, TypeError) as error:
            detail = error.args[0] if error.args else ""
            label = str(detail) if isinstance(detail, int) else type(error).__name__
            if "cert" in str(error).lower():
                label = "cert"
            self.status = self.stage + " " + label
            print("SolarTree:", self.stage, type(error).__name__, error)
            self.retry = min(120, delay * 2)
        self.next_try = time.monotonic() + delay

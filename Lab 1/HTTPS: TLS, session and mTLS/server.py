# netsec{mTLS_wh0_4r3_y0u_d8b9a744}

import secrets
import ssl
import threading
from pathlib import Path

from flask import Flask, jsonify, make_response, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

PASSWORD = "netsec"
COOKIE_NAME = "session"

SESSIONS = {}

cert_file = str(BASE_DIR / "server.cert")
key_file = str(BASE_DIR / "server.key")


@app.route("/", methods=["GET"])
def index():
    return jsonify(), 200


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    user = data.get("user")
    password = data.get("password")

    if password != PASSWORD:
        return jsonify({"error": "unauthorized"}), 401

    session_id = secrets.token_urlsafe(32)
    SESSIONS[session_id] = user

    resp = make_response(jsonify({"user": user}), 200)
    resp.set_cookie(
        COOKIE_NAME,
        session_id,
        secure=True,
        httponly=True,
    )
    return resp


@app.route("/me", methods=["GET"])
def me():
    session_id = request.cookies.get(COOKIE_NAME)

    user = SESSIONS.get(session_id) if session_id else None

    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    return jsonify({"user": user}), 200


@app.route("/whoami", methods=["GET"])
def whoami():
    sock = request.environ.get("werkzeug.socket")
    cert = sock.getpeercert() if sock else None
    if not cert:
        return "unauthorized", 401

    for rdn in cert["subject"]:
        for key, value in rdn:
            if key == "commonName":
                return value, 200, {"Content-Type": "text/plain"}

    return "unauthorized", 401


def main():
    # port 8443
    ctx_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx_tls.load_cert_chain(cert_file, key_file)

    # port 8444
    ctx_mtls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx_mtls.load_cert_chain(cert_file, key_file)
    ctx_mtls.verify_mode = ssl.CERT_REQUIRED
    ctx_mtls.load_verify_locations(str(BASE_DIR / "ca.crt"))

    threading.Thread(
        target=app.run,
        kwargs={
            "host": "0.0.0.0",
            "port": 8443,
            "ssl_context": ctx_tls,
            "threaded": True,
        },
        daemon=True,
    ).start()

    app.run(host="0.0.0.0", port=8444, ssl_context=ctx_mtls, threaded=True)


if __name__ == "__main__":
    main()

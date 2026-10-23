# flag: netsec{1m_4_t34p0t_418_4297bda6}

from flask import Flask, jsonify, request

app = Flask(__name__)

store = {}

id = -1


@app.route("/", methods=["GET"])
def index():
    return jsonify(), 200


@app.route("/echo", methods=["GET"])
def echo():
    msg = request.args.get("msg", "")
    return jsonify(msg=msg), 200


@app.route("/notes", methods=["POST"])
def post_note():
    global id

    if not request.is_json:
        return jsonify(error="Content-Type must be application/json"), 415

    text = request.get_json()

    if not isinstance(text, dict) or not isinstance(text.get("text"), str):
        return jsonify(), 400

    id += 1
    store[id] = text["text"]

    return jsonify(id=id), 201


@app.route("/notes/<int:id>", methods=["GET"])
def get_note(id):
    if id not in store:
        return jsonify(), 404

    return jsonify(id=id, text=store[id]), 200


@app.route("/notes/<int:id>", methods=["DELETE"])
def delete_note(id):
    if id not in store:
        return jsonify(), 404

    store.pop(id)

    return jsonify(), 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

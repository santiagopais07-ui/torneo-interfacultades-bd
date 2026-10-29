import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask


load_dotenv(Path(__file__).with_name(".env"))

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


@app.get("/")
def inicio():
    return """
    <h1>Torneo Interfacultades de Fútbol 5</h1>
    <p>La aplicación está funcionando.</p>
    """


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
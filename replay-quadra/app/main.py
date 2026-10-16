"""Ponto de entrada. Rode da raiz do projeto com:  python -m app.main"""
import atexit
import logging
import signal
import sys

from flask import Flask

from app import config
from app.recorder import Recorder
from app.routes import bp


def criar_app():
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app


def principal():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config.REPLAYS_DIR.mkdir(parents=True, exist_ok=True)

    # Começa a gravar o buffer assim que o programa sobe.
    recorder = Recorder()
    recorder.iniciar()
    atexit.register(recorder.parar)

    # O systemd encerra o serviço com SIGTERM. Convertendo em sys.exit(),
    # o atexit roda e o FFmpeg é encerrado direito.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    # use_reloader=False: o reloader do Flask abriria o programa duas vezes,
    # e teríamos dois FFmpeg disputando a mesma câmera.
    criar_app().run(
        host=config.HOST, port=config.PORT, threaded=True, use_reloader=False
    )


if __name__ == "__main__":
    principal()

"""Rotas HTTP.

Esta camada só recebe a requisição, chama o serviço certo e devolve a
resposta. Ela não sabe nada de FFmpeg nem de arquivos de vídeo.
"""
from flask import Blueprint, abort, jsonify, render_template, request, send_file

from app import clip_service, storage

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.post("/replay")
def create_replay():
    try:
        name = clip_service.create_replay()
    except clip_service.BusyError as e:
        return jsonify(error=str(e)), 409
    except clip_service.ClipError as e:
        return jsonify(error=str(e)), 500
    return jsonify(name=name), 201


@bp.get("/replays")
def list_replays():
    return jsonify(storage.list_replays())


@bp.get("/replays/<name>")
def get_replay(name):
    path = storage.get_replay_path(name)
    if path is None:
        abort(404)
    # conditional=True permite o navegador pular para o meio do vídeo
    return send_file(
        path,
        mimetype="video/mp4",
        conditional=True,
        as_attachment=request.args.get("download") == "1",
    )


@bp.delete("/replays/<name>")
def delete_replay(name):
    if not storage.delete_replay(name):
        abort(404)
    return "", 204

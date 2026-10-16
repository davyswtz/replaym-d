"""Regra de negócio: transformar o buffer em um replay salvo.

Quando o botão é apertado, pegamos os últimos segmentos COMPLETOS do buffer
e juntamos num único .mp4. Como os segmentos já são H.264, a junção usa
"-c copy" (não reencoda), então leva menos de um segundo.
"""
import os
import subprocess
import tempfile
import threading
from datetime import datetime

from app import config

# Impede dois replays sendo gerados ao mesmo tempo (clique duplo no botão).
_lock = threading.Lock()


class ClipError(Exception):
    """Falha ao gerar o replay."""


class BusyError(ClipError):
    """Já existe um replay sendo gerado."""


def _latest_segments():
    """Devolve os últimos segmentos completos, do mais antigo ao mais novo."""
    pattern = f"{config.SEGMENT_PREFIX}*{config.SEGMENT_EXT}"

    # Ordena por data de modificação, NÃO por nome: com o buffer circular os
    # nomes voltam ao início (seg_019 -> seg_000), então o nome engana.
    files = list(config.BUFFER_DIR.glob(pattern))

    # Um dos segmentos ainda está sendo escrito pelo FFmpeg e não pode entrar
    # no replay. Como achar qual?
    #  - Se existe arquivo vazio, é o segmento que o FFmpeg acabou de abrir.
    #    (Não dá para confiar só na data: o segmento novo e o que acabou de
    #    fechar têm datas quase idênticas e podem aparecer fora de ordem.)
    #  - Senão, é o de data de modificação mais recente.
    in_progress = [f for f in files if f.stat().st_size == 0]
    if not in_progress and files:
        in_progress = [max(files, key=lambda f: f.stat().st_mtime)]

    complete = [f for f in files if f not in in_progress]

    # Ordena por data de modificação, NÃO por nome: com o buffer circular os
    # nomes voltam ao início (seg_019 -> seg_000), então o nome engana.
    complete.sort(key=lambda f: f.stat().st_mtime)
    return complete[-config.SEGMENTS_PER_REPLAY:]


def create_replay():
    """Gera o replay e devolve o nome do arquivo criado."""
    if not _lock.acquire(blocking=False):
        raise BusyError("Já existe um replay sendo gerado")

    try:
        segments = _latest_segments()
        if not segments:
            raise ClipError("O buffer ainda está vazio. Aguarde alguns segundos.")

        config.REPLAYS_DIR.mkdir(parents=True, exist_ok=True)
        name = f"{config.REPLAY_PREFIX}{datetime.now():%Y%m%d_%H%M%S}{config.REPLAY_EXT}"
        output = config.REPLAYS_DIR / name

        # O "concat demuxer" do FFmpeg lê uma lista de arquivos em texto.
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False
        ) as list_file:
            for segment in segments:
                list_file.write(f"file '{segment}'\n")
            list_path = list_file.name

        try:
            cmd = [
                "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "concat", "-safe", "0", "-i", list_path,
                "-c", "copy",
                "-movflags", "+faststart",  # o vídeo começa a tocar logo no navegador
                str(output),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise ClipError("O FFmpeg demorou demais para juntar o replay")
        finally:
            os.unlink(list_path)

        if result.returncode != 0:
            raise ClipError(f"Falha ao juntar o replay: {result.stderr.strip()}")

        return name
    finally:
        _lock.release()

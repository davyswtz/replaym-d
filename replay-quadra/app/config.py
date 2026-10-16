"""Configurações do projeto.

Aqui ficam só constantes. Se quiser mudar a duração do replay, a câmera
ou a pasta de destino, mude neste arquivo e nenhum outro.
"""
from pathlib import Path

# Raiz do projeto (pasta replay-quadra/), calculada a partir deste arquivo.
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- Câmera
CAMERA_DEVICE = "/dev/video0"
VIDEO_SIZE = "1280x720"
FRAMERATE = 30
# Formato que a webcam entrega. Descubra com: v4l2-ctl --list-formats-ext
# Use "mjpeg" ou "yuyv422". Se for None, o FFmpeg escolhe sozinho.
INPUT_FORMAT = "mjpeg"

# Como o vídeo é codificado em H.264 (necessário para tocar no celular).
# libx264 usa a CPU. Alternativa com hardware da Pi 4:
#   ["-c:v", "h264_v4l2m2m", "-b:v", "4M"]
VIDEO_ENCODER_ARGS = [
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-tune", "zerolatency",
    "-crf", "28",
]

# ---------------------------------------------------------- Buffer circular
# /dev/shm é RAM: gravar aqui o tempo todo não desgasta o cartão SD.
BUFFER_DIR = Path("/dev/shm/replay_buffer")
SEGMENT_SECONDS = 2          # duração de cada pedaço gravado
REPLAY_SECONDS = 30          # quanto tempo para trás o replay captura
SEGMENT_PREFIX = "seg_"
SEGMENT_EXT = ".ts"

# Quantos segmentos o buffer guarda antes de sobrescrever os mais antigos.
# Os segmentos do replay + uma folga, para o FFmpeg não sobrescrever um
# arquivo que ainda estamos juntando.
SEGMENTS_PER_REPLAY = REPLAY_SECONDS // SEGMENT_SECONDS
BUFFER_SEGMENTS = SEGMENTS_PER_REPLAY + 5

# ---------------------------------------------------------------- Replays
REPLAYS_DIR = BASE_DIR / "replays"
REPLAY_PREFIX = "replay_"
REPLAY_EXT = ".mp4"

# ----------------------------------------------------------------- Logs
FFMPEG_LOG = BASE_DIR / "ffmpeg.log"

# --------------------------------------------------------------- Servidor
HOST = "0.0.0.0"   # aceita conexões de outros aparelhos da rede (celular)
PORT = 5000

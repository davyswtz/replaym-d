"""Gravação contínua do buffer circular.

Este módulo só sabe uma coisa: manter um processo do FFmpeg rodando que
grava a câmera em segmentos curtos dentro de BUFFER_DIR. Quando chega no
último segmento, o FFmpeg volta ao primeiro e sobrescreve (buffer circular).
"""
import logging
import shutil
import subprocess
import threading

from app import config

log = logging.getLogger(__name__)


class Recorder:
    def __init__(self):
        self._process = None
        self._thread = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------ comando
    def _montar_comando(self):
        cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "warning"]

        # Entrada: a webcam via Video4Linux2
        cmd += ["-f", "v4l2"]
        if config.INPUT_FORMAT:
            cmd += ["-input_format", config.INPUT_FORMAT]
        cmd += [
            "-video_size", config.VIDEO_SIZE,
            "-framerate", str(config.FRAMERATE),
            "-i", config.CAMERA_DEVICE,
        ]

        # Codificação: H.264 com um quadro-chave (keyframe) a cada segmento,
        # senão o FFmpeg não consegue cortar exatamente a cada N segundos.
        cmd += config.VIDEO_ENCODER_ARGS
        cmd += [
            "-pix_fmt", "yuv420p",
            "-g", str(config.FRAMERATE * config.SEGMENT_SECONDS),
            "-sc_threshold", "0",
            "-force_key_frames", f"expr:gte(t,n_forced*{config.SEGMENT_SECONDS})",
        ]

        # Saída: segmentos circulares (seg_000.ts ... seg_N.ts, e volta ao 0)
        pattern = f"{config.SEGMENT_PREFIX}%03d{config.SEGMENT_EXT}"
        cmd += [
            "-f", "segment",
            "-segment_time", str(config.SEGMENT_SECONDS),
            "-segment_wrap", str(config.BUFFER_SEGMENTS),
            "-segment_format", "mpegts",
            "-reset_timestamps", "1",
            str(config.BUFFER_DIR / pattern),
        ]
        return cmd

    # ----------------------------------------------------------- processo
    def _preparar_buffer(self):
        """Começa com o buffer limpo, sem sobras da execução anterior."""
        shutil.rmtree(config.BUFFER_DIR, ignore_errors=True)
        config.BUFFER_DIR.mkdir(parents=True, exist_ok=True)

    def _iniciar_processo(self):
        cmd = self._montar_comando()
        log.info("Iniciando FFmpeg: %s", " ".join(cmd))
        # Os avisos/erros do FFmpeg vão para um arquivo de log. Se a câmera
        # não abrir, é lá que você descobre o motivo.
        with open(config.FFMPEG_LOG, "ab") as logfile:
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=logfile
            )

    def esta_rodando(self):
        # poll() devolve None enquanto o processo está vivo
        return self._process is not None and self._process.poll() is None

    def _vigiar(self):
        """Roda em outra thread: se o FFmpeg cair, sobe de novo."""
        while not self._stop_event.wait(2):
            if not self.esta_rodando():
                code = self._process.returncode if self._process else None
                log.warning("FFmpeg parou (código %s). Reiniciando...", code)
                # Limpa o buffer: sobraria um segmento cortado no meio e um
                # "buraco" no tempo entre a gravação antiga e a nova.
                self._preparar_buffer()
                self._iniciar_processo()

    # ---------------------------------------------------------- interface
    def iniciar(self):
        self._stop_event.clear()
        self._preparar_buffer()
        self._iniciar_processo()
        self._thread = threading.Thread(target=self._vigiar, daemon=True)
        self._thread.start()

    def parar(self):
        self._stop_event.set()
        if self.esta_rodando():
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()

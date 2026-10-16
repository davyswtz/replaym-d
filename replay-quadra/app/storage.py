"""Acesso aos replays já salvos em disco: listar, localizar e apagar."""
from datetime import datetime

from app import config


def listar_replays():
    """Lista os replays do mais novo para o mais antigo."""
    pattern = f"{config.REPLAY_PREFIX}*{config.REPLAY_EXT}"
    files = sorted(
        config.REPLAYS_DIR.glob(pattern),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [
        {
            "name": f.name,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        }
        for f in files
    ]


def obter_caminho_replay(name):
    """Devolve o caminho do replay ou None se o nome for inválido.

    Segurança (path traversal): o nome vem da URL, então alguém poderia
    mandar "../../etc/passwd". Resolvemos o caminho final e conferimos que
    ele continua dentro da pasta de replays.
    """
    replays_dir = config.REPLAYS_DIR.resolve()
    path = (replays_dir / name).resolve()

    if path.parent != replays_dir:
        return None
    if not path.name.startswith(config.REPLAY_PREFIX):
        return None
    if path.suffix != config.REPLAY_EXT or not path.is_file():
        return None
    return path


def apagar_replay(name):
    """Apaga um replay. Devolve True se apagou, False se não existe."""
    path = obter_caminho_replay(name)
    if path is None:
        return False
    path.unlink()
    return True

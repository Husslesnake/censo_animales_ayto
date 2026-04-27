"""Empaqueta el proyecto en un .zip excluyendo lo voluminoso/innecesario."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEST = ROOT.parent / "censo_animales_sin_docker.zip"

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    "worktrees", "mariadb_data", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "tests",
}
EXCLUDE_FILE_SUFFIX = (".pyc", ".pyo")
EXCLUDE_PREFIX_REL = (
    "db/backups/",
    "logs/log_",
    ".claude/worktrees/",
    ".claude/preview-",  # cache de la herramienta de preview
)
INCLUDE_EMPTY_DIRS = ("logs", "db/backups")


def deberia_excluir(p: Path) -> bool:
    rel = p.relative_to(ROOT).as_posix()
    parts = set(p.relative_to(ROOT).parts)
    if parts & EXCLUDE_DIRS:
        return True
    if p.suffix in EXCLUDE_FILE_SUFFIX:
        return True
    for pre in EXCLUDE_PREFIX_REL:
        if rel.startswith(pre):
            return True
    if p.name == "_make_zip.py":
        return True
    return False


def main() -> None:
    n = 0
    bytes_total = 0
    with zipfile.ZipFile(DEST, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in ROOT.rglob("*"):
            if not p.is_file():
                continue
            if deberia_excluir(p):
                continue
            arc = "censo_animales/" + p.relative_to(ROOT).as_posix()
            z.write(p, arc)
            n += 1
            bytes_total += p.stat().st_size
        # Conservar carpetas vacías necesarias en runtime
        for sub in INCLUDE_EMPTY_DIRS:
            z.writestr(f"censo_animales/{sub}/.gitkeep", "")
    mb = DEST.stat().st_size / 1024 / 1024
    print(f"[OK] {DEST}")
    print(f"     {n} archivos, {bytes_total/1024/1024:.1f} MB sin comprimir → {mb:.1f} MB en zip")


if __name__ == "__main__":
    main()

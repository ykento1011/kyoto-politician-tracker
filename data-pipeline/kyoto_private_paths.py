"""Explicit private storage boundary; no Git/network operation on import."""
import hashlib
import os
from pathlib import Path

class UpdateSafetyError(RuntimeError):
    pass

def _hash_file(path):
    # Refuse symlinks/junctions in any component instead of following them.
    for part in (path, *path.parents):
        st = part.lstat()
        if part.is_symlink() or getattr(st, "st_file_attributes", 0) & 0x400:
            raise UpdateSafetyError("Reparse/symlink path is not supported")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_storage():
    value = os.environ.get("KYOTO_PRIVATE_ROOT", "")
    if not value or not Path(value).is_absolute():
        raise UpdateSafetyError("Set KYOTO_PRIVATE_ROOT to an existing absolute private directory")
    root = Path(value)
    if not root.is_dir():
        raise UpdateSafetyError("Private storage must already exist")
    for part in (root, *root.parents):
        if (part.is_symlink() or getattr(part.lstat(), "st_file_attributes", 0) & 0x400
                or (part / ".git").exists()):
            raise UpdateSafetyError("Private storage cannot be a checkout or reparse path")
    repo = Path(__file__).resolve().parent.parent
    if root.resolve().is_relative_to(repo) or repo.is_relative_to(root.resolve()):
        raise UpdateSafetyError("Private storage cannot overlap the repository")
    return root.resolve()

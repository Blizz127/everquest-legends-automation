"""Read-only installed-file binding for the copied native region model.

Hash once at owner job startup; retain stable file identities during movement.
This verifies on-disk files, not loaded memory, collision or a server's rules.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import os
from pathlib import Path
import stat

from .client_region_classification import CLIENT_SHA256, ENGINE_SHA256


def identity(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


@dataclass(frozen=True)
class InstalledModelFile:
    relative_path: str
    sha256: str
    identity: tuple


@dataclass(frozen=True)
class InstalledRegionModel:
    game_dir: str
    files: tuple[InstalledModelFile, ...]

    def check(self):
        root = Path(self.game_dir)
        if root.resolve() != root or not root.is_dir():
            raise ValueError('Installed region-model directory changed')
        for item in self.files:
            value = (root/item.relative_path).lstat()
            if not stat.S_ISREG(value.st_mode) or identity(value) != item.identity:
                raise ValueError('Installed region-model file changed: '+item.relative_path)

    def check_policy(self, policy):
        record = policy.record()
        actual = {item.relative_path:item.sha256 for item in self.files}
        if (len(actual) != len(self.files) or actual.get('eqgame.exe') != record['client_sha256']
                or actual.get('EQGraphics.dll') != record['engine_sha256']):
            raise ValueError('Installed executables do not match the native region policy')
        self.check()

    def record(self):
        return dict(format='eql-installed-region-model-v1', **asdict(self),
            installed_file_hashes_verified=True, runtime_memory_verified=False,
            real_client_accepted=False, input_authorized=False)


def verify_installed_region_model(game_dir, *, additional_pins=()):
    root = Path(game_dir).resolve(strict=True)
    pins = (('eqgame.exe', CLIENT_SHA256), ('EQGraphics.dll', ENGINE_SHA256), *additional_pins)
    if len({name for name, _ in pins}) != len(pins):
        raise ValueError('Duplicate installed region-model file')
    records = []
    for name, expected in pins:
        relative = Path(name)
        if (relative.is_absolute() or '..' in relative.parts or not relative.parts
                or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected)):
            raise ValueError('Invalid installed region-model pin')
        path = root/relative
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 128*1024*1024:
            raise ValueError('Unsupported installed region-model file: '+name)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            if identity(os.fstat(fd)) != identity(before):
                raise ValueError('Installed file changed before hashing: '+name)
            digest = sha256(); size = 0
            while block := os.read(fd, 1024*1024):
                size += len(block)
                if size > before.st_size:
                    raise ValueError('Installed file grew during hashing: '+name)
                digest.update(block)
            if (size != before.st_size or digest.hexdigest() != expected
                    or identity(os.fstat(fd)) != identity(before)
                    or identity(path.lstat()) != identity(before)):
                raise ValueError('Installed region-model hash or identity differs: '+name)
        finally:
            os.close(fd)
        records.append(InstalledModelFile(name, expected, identity(before)))
    binding = InstalledRegionModel(str(root), tuple(records))
    binding.check()
    return binding

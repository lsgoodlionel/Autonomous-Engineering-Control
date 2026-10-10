"""Fail-closed installation, upgrade, and removal of Harness-owned files."""

from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys


MANIFEST_PATH = ".agent-harness-install.json"
FORMAT_VERSION = 1
RUNTIME_FILES = (
    "scripts/agent-harness",
    "tools/agent-harness/agent_harness/__init__.py",
    "tools/agent-harness/agent_harness/cli.py",
    "tools/agent-harness/agent_harness/codex_adapter.py",
    "tools/agent-harness/agent_harness/codex_response.schema.json",
    "tools/agent-harness/agent_harness/config.py",
    "tools/agent-harness/agent_harness/diagnostics.py",
    "tools/agent-harness/agent_harness/distribution.py",
    "tools/agent-harness/agent_harness/doctor.py",
    "tools/agent-harness/agent_harness/gate_runner.py",
    "tools/agent-harness/agent_harness/git_guard.py",
    "tools/agent-harness/agent_harness/run_service.py",
    "tools/agent-harness/agent_harness/state.py",
    "tools/agent-harness/drills/run_drills.py",
    "tools/agent-harness/run_tests.py",
)
HOST_SEED_FILES = (
    "AGENTS.md",
    "docs/agent/AUTONOMY.md",
    "docs/agent/GATE_MATRIX.yaml",
    "docs/agent/HARNESS_DELIVERY.json",
    "docs/agent/HARNESS_HOST.json",
    "docs/agent/PROGRESS.md",
    "docs/agent/PROJECT_MEMORY.md",
    "docs/agent/PROTECTED_PATHS.yaml",
    "docs/agent/STATE_SCHEMA.json",
    "docs/superpowers/plans/approved-plan.md",
    "docs/superpowers/plans/real-executor-smoke.md",
    "tests/fixtures/real_executor_smoke.txt",
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_DIRECTORY_FLAGS = (os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                    | getattr(os, "O_NOFOLLOW", 0))


class DistributionError(RuntimeError):
    def __init__(self, message, exit_code=3):
        super().__init__(message)
        self.exit_code = exit_code


def _relative(value):
    if (not isinstance(value, str) or not value or "\x00" in value or "\\" in value
            or value != PurePosixPath(value).as_posix()):
        raise DistributionError("安装清单包含非法路径")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise DistributionError("安装清单包含非法路径")
    return path


@contextmanager
def _parent_descriptor(root, relative, *, create=False):
    """Open every parent from the repository fd without following symlinks."""
    parts = _relative(relative).parts
    descriptors = []
    try:
        current = os.open(root, _DIRECTORY_FLAGS)
        descriptors.append(current)
        for part in parts[:-1]:
            try:
                child = os.open(part, _DIRECTORY_FLAGS, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, mode=0o755, dir_fd=current)
                    child = os.open(part, _DIRECTORY_FLAGS, dir_fd=current)
                except OSError as error:
                    raise DistributionError("无法安全创建目标目录") from error
            except OSError as error:
                raise DistributionError("目标路径包含符号链接或非目录组件") from error
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                raise DistributionError("目标路径包含非目录组件")
            descriptors.append(child)
            current = child
        yield current, parts[-1]
    except FileNotFoundError:
        raise
    except DistributionError:
        raise
    except OSError as error:
        raise DistributionError("无法安全打开目标路径") from error
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _metadata(root, relative, *, required=True):
    try:
        with _parent_descriptor(root, relative) as (parent, name):
            metadata = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        if required:
            raise DistributionError("套件拥有文件缺失")
        return None
    except OSError as error:
        raise DistributionError("无法安全检查目标文件") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise DistributionError("目标文件不是普通文件或为符号链接")
    return metadata


def _read(root, relative):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        with _parent_descriptor(root, relative) as (parent, name):
            descriptor = os.open(name, flags, dir_fd=parent)
            try:
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode):
                    raise DistributionError("套件文件身份无效")
                chunks = []
                while True:
                    chunk = os.read(descriptor, 1024 * 1024)
                    if not chunk:
                        return b"".join(chunks)
                    chunks.append(chunk)
            finally:
                os.close(descriptor)
    except FileNotFoundError as error:
        raise DistributionError("套件拥有文件缺失") from error
    except OSError as error:
        raise DistributionError("无法安全读取套件文件") from error


def _write_to_descriptor(parent, name, content, mode):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, mode, dir_fd=parent)
    try:
        os.fchmod(descriptor, mode)
        view = memoryview(content)
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_new(root, relative, content, mode):
    try:
        with _parent_descriptor(root, relative, create=True) as (parent, name):
            try:
                os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise DistributionError("拒绝覆盖已有宿主文件")
            _write_to_descriptor(parent, name, content, mode)
    except OSError as error:
        raise DistributionError("无法安全创建套件文件") from error


def _replace(root, relative, content, mode):
    temporary = "." + _relative(relative).name + ".agent-harness-" + str(os.getpid())
    try:
        with _parent_descriptor(root, relative) as (parent, name):
            temporary_created = False
            try:
                target = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if stat.S_ISLNK(target.st_mode) or not stat.S_ISREG(target.st_mode):
                    raise DistributionError("目标文件不是普通文件或为符号链接")
                try:
                    os.stat(temporary, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise DistributionError("升级临时文件冲突")
                _write_to_descriptor(parent, temporary, content, mode)
                temporary_created = True
                target = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if stat.S_ISLNK(target.st_mode) or not stat.S_ISREG(target.st_mode):
                    raise DistributionError("替换前目标文件身份变化")
                os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                temporary_created = False
            finally:
                if temporary_created:
                    try:
                        os.unlink(temporary, dir_fd=parent)
                    except OSError:
                        pass
    except FileNotFoundError as error:
        raise DistributionError("套件拥有文件缺失") from error
    except OSError as error:
        raise DistributionError("无法原子替换套件文件") from error


def _unlink(root, relative):
    try:
        with _parent_descriptor(root, relative) as (parent, name):
            metadata = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise DistributionError("目标文件不是普通文件或为符号链接")
            os.unlink(name, dir_fd=parent)
    except FileNotFoundError as error:
        raise DistributionError("套件拥有文件缺失") from error
    except OSError as error:
        raise DistributionError("无法安全删除套件文件") from error


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _entry(relative, content, mode):
    return {"path": relative, "sha256": _sha256(content), "mode": f"{mode:04o}"}


def _source_inventory(source):
    entries = []
    for relative in RUNTIME_FILES:
        content = _read(source, relative)
        mode = 0o755 if relative == "scripts/agent-harness" else 0o644
        entries.append((_entry(relative, content, mode), content))
    return entries


def _validate_repository(target):
    try:
        root = Path(target).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as error:
        raise DistributionError("目标必须是可访问的 Git 仓库", 2) from error
    git = "/usr/bin/git"
    environment = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "")}
    commands = (("rev-parse", "--show-toplevel"),
                ("rev-parse", "--verify", "--end-of-options", "HEAD^{commit}"))
    outputs = []
    for command in commands:
        try:
            result = subprocess.run([git, "--no-optional-locks", "--no-replace-objects", *command],
                                    cwd=root, text=True, capture_output=True, check=False,
                                    timeout=5, env=environment, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise DistributionError("无法验证目标 Git 仓库", 2) from error
        if result.returncode:
            raise DistributionError("目标必须是已有提交的 Git 仓库", 2)
        outputs.append(result.stdout.strip())
    try:
        if Path(outputs[0]).resolve(strict=True) != root or not re.fullmatch(r"[0-9a-f]{40,64}", outputs[1]):
            raise DistributionError("目标必须是仓库根目录且 HEAD 明确", 2)
    except (OSError, RuntimeError, ValueError) as error:
        raise DistributionError("目标仓库身份无效", 2) from error
    return root


def _manifest_bytes(version, owned, seeded):
    document = {
        "formatVersion": FORMAT_VERSION,
        "suiteVersion": version,
        "ownedFiles": sorted(owned, key=lambda entry: entry["path"]),
        "seededFiles": sorted(seeded, key=lambda entry: entry["path"]),
    }
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _load_manifest(root):
    try:
        document = json.loads(_read(root, MANIFEST_PATH))
        if (set(document) != {"formatVersion", "suiteVersion", "ownedFiles", "seededFiles"}
                or document["formatVersion"] != FORMAT_VERSION
                or not isinstance(document["suiteVersion"], str)
                or not isinstance(document["ownedFiles"], list)
                or not isinstance(document["seededFiles"], list)):
            raise ValueError()
        seen = set()
        for entry in document["ownedFiles"]:
            if (set(entry) != {"path", "sha256", "mode"}
                    or _SHA256.fullmatch(entry["sha256"]) is None
                    or re.fullmatch(r"0[0-7]{3}", entry["mode"]) is None):
                raise ValueError()
            entry["path"] = _relative(entry["path"]).as_posix()
            if entry["path"] in seen:
                raise ValueError()
            seen.add(entry["path"])
        if seen != set(RUNTIME_FILES):
            raise ValueError()
        for entry in document["seededFiles"]:
            if (set(entry) != {"path", "sha256"} or _SHA256.fullmatch(entry["sha256"]) is None):
                raise ValueError()
            _relative(entry["path"])
        return document
    except (DistributionError, OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        if isinstance(error, DistributionError):
            raise
        raise DistributionError("安装清单无效") from error


def _verify_owned(root, entries):
    for entry in entries:
        content = _read(root, entry["path"])
        mode = stat.S_IMODE(_metadata(root, entry["path"]).st_mode)
        if _sha256(content) != entry["sha256"] or mode != int(entry["mode"], 8):
            raise DistributionError("套件拥有文件已被修改，拒绝继续")


def _prune(root, paths):
    directories = sorted({_relative(path).parent for path in paths},
                         key=lambda path: len(path.parts), reverse=True)
    for directory in directories:
        while directory != PurePosixPath("."):
            try:
                with _parent_descriptor(root, directory.as_posix()) as (parent, name):
                    metadata = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                        break
                    os.rmdir(name, dir_fd=parent)
            except (DistributionError, FileNotFoundError, OSError):
                break
            directory = directory.parent


def install(source, target):
    source = Path(source).resolve(strict=True)
    root = _validate_repository(target)
    if (_metadata(root, MANIFEST_PATH, required=False) is not None
            or _metadata(root, ".agent-harness-install", required=False) is not None):
        raise DistributionError("Harness 已安装；请使用 upgrade.sh")
    inventory = _source_inventory(source)
    for entry, _ in inventory:
        if _metadata(root, entry["path"], required=False) is not None:
            raise DistributionError("拒绝覆盖已有宿主文件")
    seeded = []
    seed_content = []
    for relative in HOST_SEED_FILES:
        source_relative = "templates/host/" + relative
        content = _read(source, source_relative)
        if _metadata(root, relative, required=False) is None:
            seed_content.append((relative, content))
            seeded.append({"path": relative, "sha256": _sha256(content)})
    created = []
    try:
        for entry, content in inventory:
            _write_new(root, entry["path"], content, int(entry["mode"], 8))
            created.append(entry["path"])
        for relative, content in seed_content:
            _write_new(root, relative, content, 0o644)
            created.append(relative)
        version = _read(source, "VERSION").decode().strip()
        _write_new(root, MANIFEST_PATH,
                   _manifest_bytes(version, [entry for entry, _ in inventory], seeded), 0o600)
    except Exception:
        for relative in reversed(created):
            try:
                _unlink(root, relative)
            except DistributionError:
                pass
        _prune(root, created)
        raise
    print(f"Installed control plane {version}; host templates were seeded without overwrites.")


def upgrade(source, target):
    source = Path(source).resolve(strict=True)
    root = _validate_repository(target)
    manifest = _load_manifest(root)
    _verify_owned(root, manifest["ownedFiles"])
    inventory = _source_inventory(source)
    old = {entry["path"]: entry for entry in manifest["ownedFiles"]}
    new = {entry["path"]: (entry, content) for entry, content in inventory}
    for relative in new.keys() - old.keys():
        if _metadata(root, relative, required=False) is not None:
            raise DistributionError("升级拒绝覆盖非套件文件")
    backup = ".agent-harness-backups/" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + str(os.getpid())
    for entry in manifest["ownedFiles"]:
        _write_new(root, backup + "/" + entry["path"], _read(root, entry["path"]), int(entry["mode"], 8))
    for relative, (entry, content) in new.items():
        if relative in old:
            _replace(root, relative, content, int(entry["mode"], 8))
        else:
            _write_new(root, relative, content, int(entry["mode"], 8))
    for relative in old.keys() - new.keys():
        _unlink(root, relative)
    version = _read(source, "VERSION").decode().strip()
    _replace(root, MANIFEST_PATH,
             _manifest_bytes(version, [entry for entry, _ in inventory], manifest["seededFiles"]), 0o600)
    _prune(root, old.keys() - new.keys())
    print(f"Upgraded control plane to {version}; backup: {root / backup}")


def uninstall(target):
    root = _validate_repository(target)
    manifest = _load_manifest(root)
    _verify_owned(root, manifest["ownedFiles"])
    paths = [entry["path"] for entry in manifest["ownedFiles"]]
    for relative in paths:
        _unlink(root, relative)
    _unlink(root, MANIFEST_PATH)
    _prune(root, paths)
    print("Removed hash-matching Harness-owned files; host policy, seeds, backups and runtime history were preserved.")


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(arguments) == 3 and arguments[0] in ("install", "upgrade"):
            globals()[arguments[0]](arguments[1], arguments[2])
        elif len(arguments) == 2 and arguments[0] == "uninstall":
            uninstall(arguments[1])
        else:
            raise DistributionError("无效的 distribution manager 参数", 2)
        return 0
    except DistributionError as error:
        print(str(error), file=sys.stderr)
        return error.exit_code


if __name__ == "__main__":
    raise SystemExit(main())

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sync_release_metadata import sync_release_metadata


def test_sync_release_metadata_writes_runtime_version_and_windows_info(tmp_path):
    version_dir = tmp_path / "src" / "catalyst"
    version_dir.mkdir(parents=True)
    version_file = version_dir / "_version.py"
    version_file.write_text(
        '"""Runtime version helpers."""\n\n__version__ = "1.0.0"\n\n'
        "def get_version() -> str:\n"
        "    return __version__\n",
        encoding="utf-8",
    )

    sync_release_metadata(tmp_path, "v1.2.3")

    version_text = version_file.read_text(encoding="utf-8")
    assert '__version__ = "1.2.3"' in version_text
    assert "def get_version() -> str:" in version_text
    version_info = (tmp_path / "version_info.txt").read_text(encoding="utf-8")
    assert "filevers=(1, 2, 3, 0)" in version_info
    assert "ProductVersion',   u'1.2.3'" in version_info
    assert "OriginalFilename', u'Catalyst.exe'" in version_info


def test_sync_release_metadata_rejects_non_numeric_versions(tmp_path):
    version_dir = tmp_path / "src" / "catalyst"
    version_dir.mkdir(parents=True)

    with pytest.raises(ValueError):
        sync_release_metadata(tmp_path, "1.2.3-beta")

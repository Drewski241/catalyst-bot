import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "catalyst")
)

from user_paths import (
    coin_prep_last_json,
    coin_prep_output_log,
    coin_prep_status_file,
    data_dir,
)


def test_coin_prep_sidecars_live_under_data_dir():
    dd = data_dir()
    assert coin_prep_output_log() == os.path.join(dd, "coin_prep_output.log")
    assert coin_prep_status_file() == os.path.join(dd, "coin_prep_status.json")
    assert coin_prep_last_json() == os.path.join(dd, "coin_prep_last.json")
    assert not coin_prep_output_log().startswith("/opt/catalyst")

from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from primecvd.common import load_config
from primecvd.data import load_clean,load_emr

@pytest.fixture(scope="session")
def cfg(): return load_config("configs/demo.json")
@pytest.fixture(scope="session")
def clean(cfg): return load_clean(cfg)
@pytest.fixture(scope="session")
def emr(cfg): return load_emr(cfg)

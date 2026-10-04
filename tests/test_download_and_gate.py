import io
import json
import zipfile
import pytest
from primecvd.download import safe_extract_emr,download_stream
from primecvd.data import EMR_FILES
from primecvd.pipeline import finalize,train_models


def test_safe_zip_extraction(tmp_path):
    z=tmp_path/"asset2.zip"
    with zipfile.ZipFile(z,"w") as f:
        for name in EMR_FILES.values(): f.writestr(name,"Patient_ID,Value\n269,1\n")
    paths=safe_extract_emr(z,tmp_path/"extracted")
    assert len(paths)==3 and all(p.exists() for p in paths)


def test_zip_path_traversal_rejected(tmp_path):
    z=tmp_path/"bad.zip"
    with zipfile.ZipFile(z,"w") as f: f.writestr("../attack.csv","bad")
    with pytest.raises(ValueError): safe_extract_emr(z,tmp_path/"extracted")
    assert not (tmp_path/"attack.csv").exists()


def test_zip_missing_tables_rejected(tmp_path):
    z=tmp_path/"bad.zip"
    with zipfile.ZipFile(z,"w") as f: f.writestr("other.csv","x")
    with pytest.raises(ValueError): safe_extract_emr(z,tmp_path/"extracted")


class FakeResponse:
    headers={"Content-Type":"text/csv"}; url="https://example.test/file"
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def raise_for_status(self): pass
    def iter_content(self,chunk_size): yield b"a,b\n"+b"1,2\n"*100
class FakeSession:
    def get(self,*a,**k): return FakeResponse()


def test_download_stream_with_mock(tmp_path):
    path=tmp_path/"sample.csv"; record=download_stream(FakeSession(),"https://example.test/file",path)
    assert record["bytes"]==404 and len(record["sha256"])==64
    assert path.exists() and not (tmp_path/"sample.csv.part").exists()


def test_failed_download_does_not_leave_partial(tmp_path):
    with pytest.raises(ValueError): download_stream(FakeSession(),"https://example.test/file",tmp_path/"sample.csv",max_bytes=10)
    assert not (tmp_path/"sample.csv.part").exists()


def test_test_set_requires_explicit_unlock(cfg):
    with pytest.raises(RuntimeError,match="封存"): finalize(cfg,False)


def test_pipeline_freeze_and_retraining_guard(cfg,tmp_path):
    c={**cfg,"output_dir":str(tmp_path/"run"),"features":["Age","BMI","diabetes"],"cv_folds":2,"ridge_alphas":[0.01]}
    report=train_models(c)
    assert report.exists()
    with pytest.raises(RuntimeError,match="变化"): finalize({**c,"horizon_years":4},True)
    report=finalize(c,True)
    assert "工程演示数据" in report.read_text(encoding="utf-8")
    with pytest.raises(RuntimeError,match="已打开"): train_models(c)
    with pytest.raises(RuntimeError,match="已存在"): finalize(c,True)


def test_official_emr_requires_manifest(monkeypatch,tmp_path):
    import primecvd.data as data
    monkeypatch.setattr(data,"data_dir",lambda cfg:tmp_path)
    with pytest.raises(RuntimeError,match="manifest"):
        data.load_emr({"mode":"official"})


def test_official_emr_rejects_changed_hash(monkeypatch,tmp_path):
    import primecvd.data as data
    monkeypatch.setattr(data,"data_dir",lambda cfg:tmp_path)
    for name in data.EMR_FILES.values():
        (tmp_path/name).write_text("Patient_ID\n269\n")
    (tmp_path/"manifest.json").write_text(json.dumps({"status":"downloaded", "extracted_sha256":{name:"wrong" for name in data.EMR_FILES.values()}}))
    with pytest.raises(RuntimeError,match="完整性"):
        data.load_emr({"mode":"official"})

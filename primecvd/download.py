"""下载锁定版本的Figshare文件，保留原字节、来源与校验记录。
2026-09-27 已在 macOS 上实测远端下载成功，两个文件的提供者 MD5 均核验通过。
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import hashlib
import json
import shutil
import zipfile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .common import write_json, sha256
from .data import EMR_FILES

# Asset1 于 2026-08-12 发布版本 2（文件名 Data001_ReadyForCoxPH_v2(2026-08-12).csv）。
# 早期 QuickStart 链接的文件 62102364 属于版本 1，不在版本 2 的文件列表里，
# 若按"版本 2 + 文件 62102364"锁定，元数据核验必然失败。Asset2 是由版本 2 生成的
# （已逐字段核对 ID、年龄、检验值和事件月份），所以这里锁定版本 2 的文件 67453365。
SOURCES = {
    "asset1": {"file_id":67453365,"article_id":31395765,"version":2,"filename":"asset1.csv",
               "doi":"10.6084/m9.figshare.31395765.v2"},
    "asset2": {"file_id":62130498,"article_id":31403028,"version":1,"filename":"asset2_original.zip",
               "doi":"10.6084/m9.figshare.31403028.v1"},
}


def safe_extract_emr(archive: Path, target: Path) -> list[Path]:
    """只提取预期的三个CSV；限制大小、拒绝路径穿越和重复成员。"""
    expected=set(EMR_FILES.values()); seen={}; target.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        if sum(i.file_size for i in z.infolist())>300_000_000: raise ValueError("解压体积异常。")
        for info in z.infolist():
            pp=PurePosixPath(info.filename)
            if pp.is_absolute() or ".." in pp.parts or "\\" in info.filename:
                raise ValueError("ZIP含不安全路径。")
            if info.is_dir(): continue
            if pp.name in expected:
                if pp.name in seen: raise ValueError("ZIP中有重复数据文件。")
                seen[pp.name]=info
        if set(seen)!=expected:
            raise ValueError(f"Asset2文件名与锁定版本不符：缺少{expected-set(seen)}，实际{z.namelist()}。")
        if z.testzip() is not None: raise ValueError("ZIP的CRC校验失败。")
        paths=[]
        for name,info in seen.items():
            dest=target/name; partial=dest.with_suffix(dest.suffix+".part")
            with z.open(info) as src,partial.open("wb") as out: shutil.copyfileobj(src,out)
            partial.replace(dest); paths.append(dest)
    return paths


def session():
    s=requests.Session()
    retry=Retry(total=2,backoff_factor=.8,status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
    s.mount("https://",HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"]="PRIME-CVD-learning-project/1.0 (educational dataset download)"
    return s


def download_stream(s, url: str, destination: Path, max_bytes=200_000_000) -> dict:
    partial=destination.with_suffix(destination.suffix+".part")
    destination.parent.mkdir(parents=True,exist_ok=True)
    size=0; md5=hashlib.md5()
    try:
        with s.get(url,stream=True,timeout=(15,90),allow_redirects=True) as r:
            r.raise_for_status()
            ctype=r.headers.get("Content-Type","").lower()
            if "text/html" in ctype: raise ValueError("服务器返回HTML页面，不是数据文件。")
            with partial.open("wb") as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if not chunk: continue
                    size+=len(chunk)
                    if size>max_bytes: raise ValueError("下载体积超出保护上限。")
                    f.write(chunk); md5.update(chunk)
            resolved=r.url
        if size<100: raise ValueError("响应过小，不像完整数据文件。")
        partial.replace(destination)
        return {"url":url,"resolved_url":resolved,"bytes":size,"sha256":sha256(destination),"md5":md5.hexdigest()}
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def download_official(target: Path, force=False) -> dict:
    from .data import load_clean, load_emr
    target.mkdir(parents=True,exist_ok=True)
    manifest={"status":"in_progress","data_status":"OFFICIAL_PINNED_FIGSHARE_FILES",
              "downloaded_at_utc":datetime.now(timezone.utc).isoformat(),"sources":{},"errors":[]}
    s=session()
    for key,spec in SOURCES.items():
        dest=target/spec["filename"]
        record={**spec}
        # 若已有文件，仅在旧manifest的哈希吻合时复用；不把任意同名CSV当作已验证下载。
        oldpath=target/"manifest.json"
        old=json.loads(oldpath.read_text(encoding="utf-8")) if oldpath.exists() else {}
        known=old.get("sources",{}).get(key,{})
        if dest.exists() and not force and known.get("sha256")==sha256(dest):
            record.update(known); record["reused_existing_verified_local_file"]=True
        else:
            candidates=[f"https://ndownloader.figshare.com/files/{spec['file_id']}",
                        f"https://figshare.com/ndownloader/files/{spec['file_id']}"]
            failures=[]
            for url in candidates:
                try:
                    record.update(download_stream(s,url,dest)); break
                except (requests.RequestException, ValueError, OSError) as exc:
                    failures.append(f"{url}: {type(exc).__name__}: {exc}")
            else:
                manifest["status"]="download_failed"; manifest["errors"].extend(failures)
                write_json(target/"DOWNLOAD_STATUS.json",manifest)
                raise RuntimeError("官方数据下载失败。请检查本机网络/代理；本程序不会替换成演示数据。\n"+"\n".join(failures))
            record["failed_download_attempts"]=failures
            # 提供者MD5可获得才称为provider-verified。否则只记录本地SHA256，不能证明远端真实性。
            api=f"https://api.figshare.com/v2/articles/{spec['article_id']}/versions/{spec['version']}"
            try:
                response=s.get(api,timeout=(10,20)); response.raise_for_status(); meta=response.json()
                write_json(target/f"{key}_figshare_metadata.json",meta)
                remote=next((f for f in meta.get("files",[]) if f.get("id")==spec["file_id"]),None)
                if remote is None:
                    dest.unlink(missing_ok=True)
                    raise RuntimeError("已读取的文章版本不含该文件ID；文件已删除，请核对版本，不能降级为仅缺少校验。")
                expected=remote.get("computed_md5") or remote.get("supplied_md5")
                record["provider_md5"]=expected
                if expected and expected.lower()!=record["md5"].lower():
                    dest.unlink(missing_ok=True)
                    raise RuntimeError("提供者MD5不匹配，文件已删除。")
                record["provider_checksum_verified"]=bool(expected)
                record["provider_filename"]=remote.get("name")
                record["provider_license"]=meta.get("license")
            except (requests.RequestException,ValueError,StopIteration) as exc:
                record["provider_checksum_verified"]=False
                record["metadata_warning"]=str(exc)
        manifest["sources"][key]=record
    extracted=safe_extract_emr(target/"asset2_original.zip",target)
    manifest["extracted_sha256"]={p.name:sha256(p) for p in extracted}
    # 最终结构校验独立于是否下载成功；不在这里生成假分析结果。
    import pandas as pd
    from .data import REQUIRED
    clean=pd.read_csv(target/"asset1.csv")
    if not set(REQUIRED).issubset(clean): raise ValueError("下载CSV不符合Asset1结构。")
    if len(clean)!=50000: raise ValueError(f"锁定源版本应为50000行，实际{len(clean)}。请人工核对。")
    manifest["status"]="downloaded"; manifest["clean_rows"]=len(clean)
    write_json(target/"manifest.json",manifest); write_json(target/"DOWNLOAD_STATUS.json",manifest)
    return manifest

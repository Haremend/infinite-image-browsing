"""
文件夹文件数量统计 — 纯新增功能。

交互：输入根目录 → 后台实时递归统计各子文件夹媒体文件数 → 存入 folder_file_count 表
→ 列表展示 → 行内按钮在 stackView 打开。仅在点「重新统计」时重算，否则恒用表里的结果。

计数策略：并行 os.scandir，仅按扩展名判断媒体文件，**不读文件内容、不取大小（不 stat）**，
所以与单文件大小无关，20 万图约 5–30s（SSD），瓶颈只在目录列举元数据。
"""
import os
import threading
import time
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

from .tool import is_media_file
from .db.datamodel import DataBase, FolderFileCount
from .logger import logger


# ===== 后台 job 状态（仿 topic_cluster.py 的写法，独立一份，互不影响）=====
_FOLDER_COUNT_JOBS: Dict[str, Dict] = {}
_FOLDER_COUNT_JOBS_LOCK = threading.Lock()
_FOLDER_COUNT_JOBS_MAX = 16


def _job_now() -> float:
    return time.time()


def _job_trim() -> None:
    with _FOLDER_COUNT_JOBS_LOCK:
        if len(_FOLDER_COUNT_JOBS) <= _FOLDER_COUNT_JOBS_MAX:
            return
        items = sorted(
            _FOLDER_COUNT_JOBS.items(),
            key=lambda kv: (kv[1].get("updated_at") or 0),
            reverse=True,
        )
        keep = dict(items[:_FOLDER_COUNT_JOBS_MAX])
        _FOLDER_COUNT_JOBS.clear()
        _FOLDER_COUNT_JOBS.update(keep)


def _job_get(job_id: str) -> Optional[Dict]:
    with _FOLDER_COUNT_JOBS_LOCK:
        j = _FOLDER_COUNT_JOBS.get(job_id)
        return dict(j) if isinstance(j, dict) else None


def _job_upsert(job_id: str, patch: Dict) -> None:
    with _FOLDER_COUNT_JOBS_LOCK:
        cur = _FOLDER_COUNT_JOBS.get(job_id)
        if not isinstance(cur, dict):
            cur = {"job_id": job_id}
        cur.update(patch or {})
        cur["updated_at"] = _job_now()
        _FOLDER_COUNT_JOBS[job_id] = cur
    _job_trim()


# ===== 计数核心 =====
def count_files_recursive(root_path: str, progress_cb=None) -> list:
    """递归统计 root_path 下每个文件夹的媒体文件数量（图片+视频+音频）。

    - 并行扫描顶层各子目录（ThreadPoolExecutor, 8 线程），每个子树各自迭代式 DFS，
      避免 Python 递归深度限制。
    - 仅 os.scandir 列举目录条目 + 按扩展名判断，**不 stat、不读文件内容**。
    - 每个文件夹只扫描一次，顶层根目录的直属文件单独计入 root_path。
    - 返回 [{path, count}, ...]，progress_cb(scanned, counted) 周期性回调用于进度展示。
    """
    counter: dict = {}          # folder -> media file count
    total = 0
    scanned = 0
    lock = threading.Lock()

    def _add(folder: str, n: int) -> None:
        nonlocal total
        if n <= 0:
            return
        with lock:
            counter[folder] = counter.get(folder, 0) + n
            total += n

    def _scanned_one() -> None:
        nonlocal scanned
        with lock:
            scanned += 1
            s, t = scanned, total
        if progress_cb and s % 50 == 0:
            try:
                progress_cb(s, t)
            except Exception:
                pass

    def _scan_dir(folder: str):
        """扫描单个文件夹的直属条目，返回 (子目录路径列表, 直属媒体文件数)。"""
        subs = []
        cnt = 0
        try:
            with os.scandir(folder) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            subs.append(entry.path)
                        elif entry.is_file(follow_symlinks=False) and is_media_file(entry.name):
                            cnt += 1
                    except OSError:
                        pass
        except (PermissionError, OSError):
            pass
        return subs, cnt

    def walk(root_folder: str) -> None:
        # 迭代式 DFS，避免深层目录树触发递归上限
        stack = [root_folder]
        while stack:
            cur = stack.pop()
            subs, cnt = _scan_dir(cur)
            _add(cur, cnt)
            for s in subs:
                stack.append(s)
            _scanned_one()

    # 先扫一次根目录：拿到它的直属文件数 + 顶层子目录
    root_subs, root_cnt = _scan_dir(root_path)
    _add(root_path, root_cnt)
    _scanned_one()

    # 各顶层子目录并行各自走子树
    if root_subs:
        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(walk, root_subs))

    if progress_cb:
        try:
            progress_cb(scanned, total)
        except Exception:
            pass

    return [{"path": p, "count": c} for p, c in counter.items()]


async def _run_count_job(job_id: str, folder_path: str) -> None:
    """后台统计 job：跑 count_files_recursive → 完成写表 → 更新 job 状态。"""
    _job_upsert(
        job_id,
        {
            "status": "running",
            "stage": "scanning",
            "folder_path": folder_path,
            "scanned": 0,
            "counted": 0,
        },
    )
    try:

        def progress_cb(scanned, counted):
            _job_upsert(job_id, {"scanned": scanned, "counted": counted})

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: count_files_recursive(folder_path, progress_cb)
        )
        total = sum(item["count"] for item in result)
        # 写入数据库（thread-local connection）
        conn = DataBase.get_conn()
        FolderFileCount.save(conn, folder_path, result, total)
        _job_upsert(
            job_id,
            {
                "status": "done",
                "stage": "done",
                "result": result,
                "total": total,
                "counted": total,
            },
        )
        logger.info("[folder_count] job %s done: %d folders, %d files", job_id, len(result), total)
    except Exception as e:
        logger.exception("[folder_count] job %s failed", job_id)
        _job_upsert(job_id, {"status": "error", "stage": "error", "error": str(e)})


# ===== 路由挂载 =====
class FolderCountScanReq(BaseModel):
    folder_path: str


def mount_folder_count_routes(
    app: FastAPI,
    db_api_base: str,
    verify_secret,
    write_permission_required,
    check_path_trust,
):
    """挂载文件夹文件数量统计的 3 个端点。"""

    @app.post(
        f"{db_api_base}/folder_count_scan",
        dependencies=[Depends(verify_secret), Depends(write_permission_required)],
    )
    async def folder_count_scan(req: FolderCountScanReq):
        folder_path = os.path.normpath(req.folder_path)
        check_path_trust(folder_path)
        if not os.path.isdir(folder_path):
            raise HTTPException(status_code=400, detail="folder_path is not a directory")
        job_id = uuid.uuid4().hex
        _job_upsert(
            job_id,
            {"status": "queued", "stage": "queued", "created_at": _job_now()},
        )
        asyncio.create_task(_run_count_job(job_id, folder_path))
        return {"job_id": job_id}

    @app.get(
        f"{db_api_base}/folder_count_status",
        dependencies=[Depends(verify_secret), Depends(write_permission_required)],
    )
    async def folder_count_status(job_id: str):
        j = _job_get(job_id)
        if not j:
            raise HTTPException(status_code=404, detail="job not found")
        return j

    @app.get(
        f"{db_api_base}/folder_count_result",
        dependencies=[Depends(verify_secret)],
    )
    async def folder_count_result(folder_path: str):
        folder_path = os.path.normpath(folder_path)
        check_path_trust(folder_path)
        conn = DataBase.get_conn()
        row = FolderFileCount.get(conn, folder_path)
        if not row:
            return {"result": [], "total": 0, "counted_at": None}
        return row

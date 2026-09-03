"""
SQLite数据库模块
技术方向：智能制造系统集成（数据持久化）
"""
import sqlite3
import json
import os
import time
from contextlib import contextmanager


class Database:
    """FJSP调度系统数据库"""

    def __init__(self, db_path=None):
        """
        初始化数据库
        :param db_path: 数据库文件路径，默认在项目根目录/data/fjsp.db
        """
        if db_path is None:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(base, "data", "fjsp.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_tables()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_tables(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scheduling_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT NOT NULL,
                    instance_name TEXT,
                    status TEXT DEFAULT 'pending',
                    parameters TEXT,
                    result TEXT,
                    makespan REAL,
                    elapsed_time REAL,
                    created_at REAL,
                    completed_at REAL
                );

                CREATE TABLE IF NOT EXISTS scheduling_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    instance_id TEXT NOT NULL,
                    makespan REAL,
                    machine_schedule TEXT,
                    job_schedule TEXT,
                    machine_utilization TEXT,
                    convergence_history TEXT,
                    analysis TEXT,
                    created_at REAL,
                    FOREIGN KEY (task_id) REFERENCES scheduling_tasks(id)
                );

                CREATE TABLE IF NOT EXISTS dataset_cache (
                    instance_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    stats TEXT,
                    updated_at REAL
                );

                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT DEFAULT 'info',
                    module TEXT,
                    message TEXT,
                    created_at REAL
                );
            """)

    # ==================== 调度任务管理 ====================

    def create_task(self, instance_id, instance_name="", parameters=None):
        """创建调度任务"""
        now = time.time()
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO scheduling_tasks (instance_id, instance_name, parameters, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
                (instance_id, instance_name, json.dumps(parameters or {}, ensure_ascii=False), now)
            )
            return cursor.lastrowid

    def update_task_status(self, task_id, status, result=None, makespan=None, elapsed_time=None):
        """更新任务状态"""
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE scheduling_tasks SET status=?, result=?, makespan=?, elapsed_time=?, completed_at=? WHERE id=?",
                (status, json.dumps(result or {}, ensure_ascii=False) if result else None,
                 makespan, elapsed_time, now, task_id)
            )

    def get_task(self, task_id):
        """获取任务详情"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM scheduling_tasks WHERE id=?", (task_id,)).fetchone()
            if row:
                return dict(row)
            return None

    def list_tasks(self, limit=20, offset=0):
        """列出任务列表"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM scheduling_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [dict(row) for row in rows]

    # ==================== 调度结果管理 ====================

    def save_result(self, task_id, instance_id, schedule_result, analysis=None):
        """保存调度结果"""
        now = time.time()
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO scheduling_results
                   (task_id, instance_id, makespan, machine_schedule, job_schedule,
                    machine_utilization, convergence_history, analysis, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id,
                    instance_id,
                    schedule_result["makespan"],
                    json.dumps(schedule_result["machine_schedule"], ensure_ascii=False),
                    json.dumps(schedule_result["job_schedule"], ensure_ascii=False),
                    json.dumps(schedule_result["machine_utilization"], ensure_ascii=False),
                    json.dumps(schedule_result["convergence_history"], ensure_ascii=False),
                    json.dumps(analysis or {}, ensure_ascii=False),
                    now,
                )
            )
            return cursor.lastrowid

    def get_result(self, result_id):
        """获取调度结果"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM scheduling_results WHERE id=?", (result_id,)).fetchone()
            if row:
                d = dict(row)
                for key in ["machine_schedule", "job_schedule", "machine_utilization",
                            "convergence_history", "analysis"]:
                    if d.get(key):
                        d[key] = json.loads(d[key])
                return d
            return None

    def get_latest_result(self, instance_id):
        """获取某实例的最新调度结果"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM scheduling_results WHERE instance_id=? ORDER BY created_at DESC LIMIT 1",
                (instance_id,)
            ).fetchone()
            if row:
                d = dict(row)
                for key in ["machine_schedule", "job_schedule", "machine_utilization",
                            "convergence_history", "analysis"]:
                    if d.get(key):
                        d[key] = json.loads(d[key])
                return d
            return None

    # ==================== 数据集缓存 ====================

    def cache_instance(self, instance_id, data, stats=None):
        """缓存实例数据"""
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO dataset_cache (instance_id, data, stats, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (instance_id, json.dumps(data, ensure_ascii=False),
                 json.dumps(stats or {}, ensure_ascii=False), now)
            )

    def get_cached_instance(self, instance_id):
        """获取缓存的实例数据"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM dataset_cache WHERE instance_id=?", (instance_id,)).fetchone()
            if row:
                d = dict(row)
                d["data"] = json.loads(d["data"])
                if d.get("stats"):
                    d["stats"] = json.loads(d["stats"])
                return d
            return None

    # ==================== 系统日志 ====================

    def add_log(self, level, module, message):
        """添加系统日志"""
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO system_logs (level, module, message, created_at) VALUES (?, ?, ?, ?)",
                (level, module, message, now)
            )

    def get_logs(self, limit=50, level=None):
        """获取系统日志"""
        with self._get_conn() as conn:
            if level:
                rows = conn.execute(
                    "SELECT * FROM system_logs WHERE level=? ORDER BY created_at DESC LIMIT ?",
                    (level, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM system_logs ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(row) for row in rows]

    # ==================== 统计信息 ====================

    def get_stats(self):
        """获取数据库统计信息"""
        with self._get_conn() as conn:
            task_count = conn.execute("SELECT COUNT(*) as c FROM scheduling_tasks").fetchone()["c"]
            result_count = conn.execute("SELECT COUNT(*) as c FROM scheduling_results").fetchone()["c"]
            cache_count = conn.execute("SELECT COUNT(*) as c FROM dataset_cache").fetchone()["c"]
            avg_makespan = conn.execute("SELECT AVG(makespan) as a FROM scheduling_results").fetchone()["a"]
            return {
                "total_tasks": task_count,
                "total_results": result_count,
                "cached_instances": cache_count,
                "avg_makespan": round(avg_makespan, 2) if avg_makespan else 0,
            }


# 全局数据库实例
_db_instance = None


def get_db():
    """获取全局数据库实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

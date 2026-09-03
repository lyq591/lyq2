"""
FJSP智能调度系统 - 一键启动程序
同时启动后端Flask服务和前端HTTP服务，自动打开浏览器
用法: python start.py
"""
import subprocess
import sys
import os
import time
import socket
import webbrowser
import signal

# ==================== 配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 5500

BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
FRONTEND_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"

IS_WINDOWS = sys.platform == "win32"

# PID文件，用于一键关闭脚本定位进程
PID_FILE = os.path.join(BASE_DIR, ".running_pids")

# ==================== 工具函数 ====================

def print_banner():
    print()
    print("=" * 60)
    print("   FJSP Intelligent Scheduling System - Launcher")
    print("=" * 60)
    print()
    print(f"  Project : {BASE_DIR}")
    print(f"  Backend : {BACKEND_URL}")
    print(f"  Frontend: {FRONTEND_URL}")
    print()


def check_port(host, port):
    """检查端口是否被占用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def wait_for_service(host, port, timeout=20):
    """等待服务启动就绪"""
    start = time.time()
    while time.time() - start < timeout:
        if check_port(host, port):
            return True
        time.sleep(0.5)
    return False


def stop_process(proc, name):
    """停止子进程"""
    if proc and proc.poll() is None:
        print(f"  Stopping {name}...", end=" ", flush=True)
        try:
            if IS_WINDOWS:
                # Windows: use taskkill to kill the whole process tree
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=5
                )
            else:
                proc.terminate()
                proc.wait(timeout=5)
            print("OK")
        except Exception as e:
            print(f"warning: {e}")
            try:
                proc.kill()
            except Exception:
                pass


# ==================== 主程序 ====================

def main():
    print_banner()

    # 1. 检查Python
    print("[Check] Python environment...")
    print(f"  OK: {sys.executable} (Python {sys.version.split()[0]})")

    # 2. 检查依赖
    print("[Check] Backend dependencies...")
    try:
        import flask
        import flask_cors
        flask_ver = getattr(flask, '__version__', 'installed')
        print(f"  OK: Flask {flask_ver}")
    except ImportError:
        print("  Installing dependencies...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r",
             os.path.join(BACKEND_DIR, "requirements.txt")],
            cwd=BASE_DIR
        )
        print("  OK: dependencies installed")

    # 3. 检查端口
    print("[Check] Port availability...")
    if check_port(BACKEND_HOST, BACKEND_PORT):
        print(f"  ERROR: Backend port {BACKEND_PORT} is already in use!")
        print("  Please close the program using this port and try again.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    if check_port(FRONTEND_HOST, FRONTEND_PORT):
        print(f"  ERROR: Frontend port {FRONTEND_PORT} is already in use!")
        print("  Please close the program using this port and try again.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    print(f"  OK: ports {BACKEND_PORT} and {FRONTEND_PORT} are free")

    # 4. 检查文件
    if not os.path.exists(os.path.join(BACKEND_DIR, "main.py")):
        print("  ERROR: backend/main.py not found!")
        input("\nPress Enter to exit...")
        sys.exit(1)
    if not os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
        print("  ERROR: frontend/index.html not found!")
        input("\nPress Enter to exit...")
        sys.exit(1)

    backend_proc = None
    frontend_proc = None

    try:
        # 5. 启动后端
        print()
        print("[Start] Backend service (Flask)...")
        if IS_WINDOWS:
            # Windows: open in new console window to avoid pipe issues
            backend_proc = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=BACKEND_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            backend_proc = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=BACKEND_DIR
            )
        print(f"  PID: {backend_proc.pid}")
        print("  Waiting for backend to be ready...", end=" ", flush=True)
        if wait_for_service(BACKEND_HOST, BACKEND_PORT, timeout=25):
            print("OK")
            print(f"  API: {BACKEND_URL}/api/health")
        else:
            print("TIMEOUT")
            print("  WARNING: Backend may have failed to start. Check the backend window.")

        # 6. 启动前端
        print()
        print("[Start] Frontend service (HTTP Server)...")
        if IS_WINDOWS:
            frontend_proc = subprocess.Popen(
                [sys.executable, "-m", "http.server", str(FRONTEND_PORT),
                 "--bind", FRONTEND_HOST],
                cwd=FRONTEND_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            frontend_proc = subprocess.Popen(
                [sys.executable, "-m", "http.server", str(FRONTEND_PORT),
                 "--bind", FRONTEND_HOST],
                cwd=FRONTEND_DIR
            )
        print(f"  PID: {frontend_proc.pid}")
        print("  Waiting for frontend to be ready...", end=" ", flush=True)
        if wait_for_service(FRONTEND_HOST, FRONTEND_PORT, timeout=10):
            print("OK")
        else:
            print("TIMEOUT")

        # 记录PID到文件，供一键关闭脚本使用
        try:
            with open(PID_FILE, "w") as f:
                f.write(f"backend={backend_proc.pid}\n")
                f.write(f"frontend={frontend_proc.pid}\n")
            print(f"  PID file written: {PID_FILE}")
        except Exception as e:
            print(f"  WARNING: Could not write PID file: {e}")

        # 7. 打开浏览器
        print()
        print("[Browser] Opening frontend page...")
        try:
            webbrowser.open(FRONTEND_URL)
            print(f"  OK: {FRONTEND_URL}")
        except Exception as e:
            print(f"  WARNING: Could not open browser automatically: {e}")
            print(f"  Please open {FRONTEND_URL} manually")

        # 8. 运行中提示
        print()
        print("=" * 60)
        print("  System is RUNNING")
        print(f"  Frontend: {FRONTEND_URL}")
        print(f"  Backend : {BACKEND_URL}")
        print(f"  API Doc : {BACKEND_URL}/api/health")
        print()
        print("  Two console windows opened:")
        print("    - 'FJSP Backend (Flask)'  : backend logs")
        print("    - 'FJSP Frontend (HTTP)'  : frontend logs")
        print()
        print("  Press Ctrl+C in THIS window to stop all services")
        print("=" * 60)
        print()

        # 9. 监控循环
        while True:
            time.sleep(2)
            # 检查进程状态
            backend_alive = backend_proc and backend_proc.poll() is None
            frontend_alive = frontend_proc and frontend_proc.poll() is None
            if not backend_alive:
                print("[WARNING] Backend process has exited!")
            if not frontend_alive:
                print("[WARNING] Frontend process has exited!")
            if not backend_alive and not frontend_alive:
                print("[ERROR] Both services have stopped. Exiting.")
                break

    except KeyboardInterrupt:
        print()
        print()
        print("[Stop] Received Ctrl+C, stopping all services...")
    except Exception as e:
        print()
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 10. 清理
        print()
        stop_process(backend_proc, "Backend")
        stop_process(frontend_proc, "Frontend")
        # 删除PID文件
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass
        print()
        print("=" * 60)
        print("  All services stopped.")
        print("=" * 60)
        print()
        input("Press Enter to close this window...")


if __name__ == "__main__":
    main()

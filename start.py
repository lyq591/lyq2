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
import threading

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

# 颜色输出
class Color:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

# Windows下启用ANSI颜色
if sys.platform == "win32":
    os.system("")

# ==================== 工具函数 ====================

def print_banner():
    """打印启动横幅"""
    print()
    print(f"{Color.BOLD}{Color.CYAN}{'=' * 60}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}   FJSP智能调度辅助Agent系统 - 一键启动{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'=' * 60}{Color.RESET}")
    print()
    print(f"  项目目录: {BASE_DIR}")
    print(f"  后端地址: {BACKEND_URL}")
    print(f"  前端地址: {FRONTEND_URL}")
    print()


def check_port(host, port):
    """检查端口是否被占用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def wait_for_service(host, port, timeout=15):
    """等待服务启动就绪"""
    start = time.time()
    while time.time() - start < timeout:
        if check_port(host, port):
            return True
        time.sleep(0.5)
    return False


def stream_output(process, prefix, color):
    """实时输出子进程日志"""
    try:
        for line in process.stdout:
            if line:
                line = line.rstrip()
                if line:
                    print(f"{color}[{prefix}]{Color.RESET} {line}")
    except Exception:
        pass


# ==================== 主程序 ====================

def main():
    print_banner()

    # 1. 检查Python环境
    print(f"{Color.BOLD}[检查]{Color.RESET} Python环境...")
    result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
    print(f"  {Color.GREEN}✓{Color.RESET} {result.stdout.strip() or result.stderr.strip()}")

    # 2. 检查依赖
    print(f"{Color.BOLD}[检查]{Color.RESET} 后端依赖...")
    try:
        import flask
        import flask_cors
        print(f"  {Color.GREEN}✓{Color.RESET} Flask {flask.__version__}, flask-cors 已安装")
    except ImportError:
        print(f"  {Color.YELLOW}⚠{Color.RESET} 依赖未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r",
                        os.path.join(BACKEND_DIR, "requirements.txt")])
        print(f"  {Color.GREEN}✓{Color.RESET} 依赖安装完成")

    # 3. 检查端口
    print(f"{Color.BOLD}[检查]{Color.RESET} 端口占用...")
    if check_port(BACKEND_HOST, BACKEND_PORT):
        print(f"  {Color.RED}✗{Color.RESET} 后端端口 {BACKEND_PORT} 已被占用！")
        print(f"    请先关闭占用该端口的程序，或修改 start.py 中的 BACKEND_PORT")
        input("\n按回车键退出...")
        sys.exit(1)
    if check_port(FRONTEND_HOST, FRONTEND_PORT):
        print(f"  {Color.RED}✗{Color.RESET} 前端端口 {FRONTEND_PORT} 已被占用！")
        print(f"    请先关闭占用该端口的程序，或修改 start.py 中的 FRONTEND_PORT")
        input("\n按回车键退出...")
        sys.exit(1)
    print(f"  {Color.GREEN}✓{Color.RESET} 端口 {BACKEND_PORT} 和 {FRONTEND_PORT} 均可用")

    # 4. 启动后端
    print()
    print(f"{Color.BOLD}[启动]{Color.RESET} 后端服务 (Flask)...")
    backend_proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

    # 后端日志线程
    backend_thread = threading.Thread(
        target=stream_output, args=(backend_proc, "后端", Color.BLUE), daemon=True
    )
    backend_thread.start()

    # 等待后端就绪
    print(f"  等待后端服务就绪...", end=" ", flush=True)
    if wait_for_service(BACKEND_HOST, BACKEND_PORT, timeout=20):
        print(f"{Color.GREEN}✓{Color.RESET}")
        print(f"  {Color.GREEN}后端API: {BACKEND_URL}/api/health{Color.RESET}")
    else:
        print(f"{Color.RED}✗ 超时{Color.RESET}")
        print(f"  {Color.YELLOW}后端可能启动失败，请检查上方日志{Color.RESET}")

    # 5. 启动前端
    print()
    print(f"{Color.BOLD}[启动]{Color.RESET} 前端服务 (HTTP Server)...")
    frontend_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(FRONTEND_PORT), "--bind", FRONTEND_HOST],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

    # 前端日志线程
    frontend_thread = threading.Thread(
        target=stream_output, args=(frontend_proc, "前端", Color.GREEN), daemon=True
    )
    frontend_thread.start()

    # 等待前端就绪
    print(f"  等待前端服务就绪...", end=" ", flush=True)
    if wait_for_service(FRONTEND_HOST, FRONTEND_PORT, timeout=10):
        print(f"{Color.GREEN}✓{Color.RESET}")
    else:
        print(f"{Color.RED}✗ 超时{Color.RESET}")

    # 6. 打开浏览器
    print()
    print(f"{Color.BOLD}[浏览器]{Color.RESET} 正在打开前端页面...")
    try:
        webbrowser.open(FRONTEND_URL)
        print(f"  {Color.GREEN}✓{Color.RESET} 已打开 {FRONTEND_URL}")
    except Exception:
        print(f"  {Color.YELLOW}⚠{Color.RESET} 自动打开失败，请手动访问 {FRONTEND_URL}")

    # 7. 运行中提示
    print()
    print(f"{Color.BOLD}{Color.CYAN}{'=' * 60}{Color.RESET}")
    print(f"{Color.BOLD}  系统运行中{Color.RESET}")
    print(f"  前端界面: {Color.CYAN}{FRONTEND_URL}{Color.RESET}")
    print(f"  后端API:  {Color.CYAN}{BACKEND_URL}{Color.RESET}")
    print(f"  API文档:  {Color.CYAN}{BACKEND_URL}/api/health{Color.RESET}")
    print(f"{Color.YELLOW}  按 Ctrl+C 停止所有服务{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'=' * 60}{Color.RESET}")
    print()

    # 8. 等待退出信号
    processes = [backend_proc, frontend_proc]
    try:
        while True:
            # 检查进程是否还在运行
            for proc in processes:
                if proc.poll() is not None:
                    name = "后端" if proc is backend_proc else "前端"
                    print(f"\n{Color.RED}[警告]{Color.RESET} {name}服务已退出 (code={proc.returncode})")
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        print(f"\n{Color.YELLOW}[停止]{Color.RESET} 正在停止所有服务...")

        # 优雅终止进程
        for proc, name in [(backend_proc, "后端"), (frontend_proc, "前端")]:
            if proc.poll() is None:
                print(f"  停止{name}服务...", end=" ", flush=True)
                try:
                    if sys.platform == "win32":
                        proc.terminate()
                    else:
                        proc.send_signal(signal.SIGTERM)
                    proc.wait(timeout=5)
                    print(f"{Color.GREEN}✓{Color.RESET}")
                except subprocess.TimeoutExpired:
                    proc.kill()
                    print(f"{Color.YELLOW}已强制停止{Color.RESET}")
                except Exception:
                    print(f"{Color.RED}停止失败{Color.RESET}")

        print()
        print(f"{Color.GREEN}所有服务已停止。{Color.RESET}")
        print()


if __name__ == "__main__":
    main()

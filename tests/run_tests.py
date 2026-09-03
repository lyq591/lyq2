"""
自动化测试运行器
运行所有单元测试并输出汇总报告
"""
import sys
import os
import time

# 确保backend和项目根目录在路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from tests.test_ga import run_all_tests as run_ga_tests
from tests.test_database import run_all_tests as run_db_tests
from tests.test_analysis import run_all_tests as run_analysis_tests
from tests.test_api import run_all_tests as run_api_tests


def main():
    print("\n" + "=" * 70)
    print("  FJSP智能调度辅助Agent系统 - 自动化测试套件")
    print("=" * 70)
    print(f"  测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python版本: {sys.version.split()[0]}")
    print("=" * 70 + "\n")

    start_time = time.time()
    passed = 0
    failed = 0
    test_suites = [
        ("遗传算法模块", run_ga_tests),
        ("数据库模块", run_db_tests),
        ("数据分析模块", run_analysis_tests),
        ("API接口模块", run_api_tests),
    ]

    for name, test_func in test_suites:
        try:
            print(f"\n{'─' * 70}")
            print(f"  运行测试套件: {name}")
            print(f"{'─' * 70}")
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n  ✗ 测试套件 [{name}] 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    elapsed = round(time.time() - start_time, 2)

    print("\n" + "=" * 70)
    print("  测试汇总报告")
    print("=" * 70)
    print(f"  测试套件总数: {len(test_suites)}")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  总耗时: {elapsed}秒")
    print("=" * 70)

    if failed > 0:
        print("\n  ⚠ 存在失败的测试套件，请检查上述错误信息。")
        sys.exit(1)
    else:
        print("\n  ✓ 所有测试套件全部通过!")
        sys.exit(0)


if __name__ == "__main__":
    main()

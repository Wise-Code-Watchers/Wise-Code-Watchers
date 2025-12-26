#!/usr/bin/env python3
"""
智能备份脚本 - 遵守 .gitignore 规则创建压缩包
"""

import os
import tarfile
import fnmatch
import subprocess
from datetime import datetime
from pathlib import Path

def is_ignored(file_path, git_root):
    """使用 git check-ignore 检查文件是否被忽略"""
    try:
        # 获取相对于 git root 的路径
        rel_path = os.path.relpath(file_path, git_root)

        # 使用 git check-ignore 命令
        result = subprocess.run(
            ['git', 'check-ignore', rel_path],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=5
        )

        # 如果返回结果，说明被忽略
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # 如果 git 不可用，fallback 到手动检查
        return False

def should_ignore(file_path, git_root, ignore_patterns):
    """
    手动检查文件是否应该被忽略（fallback）
    用于没有 git 的环境
    """
    rel_path = os.path.relpath(file_path, git_root)

    # 检查每个部分路径
    parts = Path(rel_path).parts

    for pattern in ignore_patterns:
        # 检查完整路径
        if fnmatch.fnmatch(rel_path, pattern):
            return True

        # 检查路径的每个部分
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True

        # 检查目录模式
        if pattern.endswith('/'):
            if fnmatch.fnmatch(rel_path + '/', pattern):
                return True

    return False

def parse_gitignore(gitignore_path):
    """解析 .gitignore 文件，返回忽略模式列表"""
    patterns = []

    if not os.path.exists(gitignore_path):
        return patterns

    with open(gitignore_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue

            patterns.append(line)

    return patterns

def create_backup(project_root, output_file, use_git=True, verbose=False):
    """
    创建项目备份压缩包

    Args:
        project_root: 项目根目录
        output_file: 输出文件路径
        use_git: 是否使用 git 命令检查（更准确）
        verbose: 是否显示详细信息
    """
    gitignore_path = os.path.join(project_root, '.gitignore')

    if use_git:
        print("🔍 使用 git check-ignore 检测文件...")
        check_ignored = lambda f: is_ignored(f, project_root)
    else:
        print("🔍 解析 .gitignore 文件...")
        ignore_patterns = parse_gitignore(gitignore_path)
        print(f"   找到 {len(ignore_patterns)} 个忽略模式")
        check_ignored = lambda f: should_ignore(f, project_root, ignore_patterns)

    print(f"📦 开始创建备份: {output_file}")
    print(f"   源目录: {project_root}")

    total_files = 0
    skipped_files = 0
    added_files = 0

    with tarfile.open(output_file, "w:gz") as tar:
        for root, dirs, files in os.walk(project_root):
            # 过滤掉 .git 目录
            if '.git' in dirs:
                dirs.remove('.git')

            for file in files:
                file_path = os.path.join(root, file)
                total_files += 1

                # 检查是否应该忽略
                if check_ignored(file_path):
                    skipped_files += 1
                    if verbose:
                        rel_path = os.path.relpath(file_path, project_root)
                        print(f"   ⊘ 忽略: {rel_path}")
                    continue

                # 添加到压缩包
                rel_path = os.path.relpath(file_path, project_root)
                tar.add(file_path, arcname=rel_path)
                added_files += 1

                if verbose and added_files % 100 == 0:
                    print(f"   已添加 {added_files} 个文件...")

    print(f"\n✅ 备份完成!")
    print(f"   总文件数: {total_files}")
    print(f"   已添加: {added_files}")
    print(f"   已忽略: {skipped_files}")
    print(f"   压缩包大小: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='智能备份脚本 - 遵守 .gitignore 规则',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用 git 命令检查（推荐）
  python backup_project.py

  # 不使用 git 命令（fallback）
  python backup_project.py --no-git

  # 自定义输出文件
  python backup_project.py -o my_backup.tar.gz

  # 显示详细信息
  python backup_project.py -v
        """
    )

    parser.add_argument(
        '-o', '--output',
        default=None,
        help='输出文件路径 (默认: wise_code_watchers_YYYYMMDD_HHMMSS.tar.gz)'
    )

    parser.add_argument(
        '--no-git',
        action='store_true',
        help='不使用 git 命令检查（手动解析 .gitignore）'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细信息'
    )

    parser.add_argument(
        '--dir',
        default='/home/landasika/Wise-Code-Watchers',
        help='项目根目录 (默认: /home/landasika/Wise-Code-Watchers)'
    )

    args = parser.parse_args()

    # 生成默认文件名
    if args.output is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'wise_code_watchers_{timestamp}.tar.gz'

    # 检查输出文件是否已存在
    if os.path.exists(args.output):
        response = input(f"⚠️  文件 {args.output} 已存在，是否覆盖? (y/N): ")
        if response.lower() != 'y':
            print("❌ 已取消")
            return

    # 创建备份
    create_backup(
        project_root=args.dir,
        output_file=args.output,
        use_git=not args.no_git,
        verbose=args.verbose
    )

if __name__ == '__main__':
    main()

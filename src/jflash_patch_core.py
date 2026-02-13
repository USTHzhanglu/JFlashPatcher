#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JFlash 补丁工具 - 核心函数库（无 UI 依赖）
供命令行和 GUI 版本共同调用
"""

import os
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ----------------------------------------------------------------------
# 路径检测
# ----------------------------------------------------------------------
def find_jflash_path():
    """自动检测 JFlash 安装目录（环境变量/PATH/默认路径）"""
    for env_var in ['JLINK_HOME', 'SEGGER_JLINK_PATH', 'SEGGER_JLINK_HOME']:
        if env_var in os.environ:
            path = os.environ[env_var]
            if os.path.isdir(path):
                return path

    is_windows = sys.platform.startswith('win')
    exe_name = 'jflash.exe' if is_windows else 'JFlashExe'
    for path_dir in os.environ.get('PATH', '').split(os.pathsep):
        if path_dir and os.path.isfile(os.path.join(path_dir, exe_name)):
            return path_dir

    common_paths = []
    if is_windows:
        common_paths = [
            r'C:\Program Files\SEGGER\JLink',
            r'C:\Program Files (x86)\SEGGER\JLink'
        ]
    else:
        common_paths = [
            '/opt/SEGGER/JLink',
            '/usr/local/SEGGER/JLink'
        ]
    for p in common_paths:
        if os.path.isdir(p):
            return p
    return None


# ----------------------------------------------------------------------
# XML 设备名称提取（递归，支持 ChipInfo）
# ----------------------------------------------------------------------
def get_device_name(elem):
    """从 XML 元素中递归提取 Name 属性（大小写不敏感）"""
    # 1. 自身属性
    name = elem.get('Name')
    if name:
        return name, True
    name = elem.get('name')
    if name:
        return name, True
    for key, value in elem.attrib.items():
        if key.lower() == 'name':
            return value, True

    # 2. Device 元素递归子元素
    if elem.tag.lower() == 'device':
        for child in elem:
            if child.tag.lower() == 'chipinfo':
                for key, value in child.attrib.items():
                    if key.lower() == 'name':
                        return value, True
                sub_name, found = get_device_name(child)
                if found:
                    return sub_name, True
        for child in elem:
            sub_name, found = get_device_name(child)
            if found:
                return sub_name, True

    return None, False


# ----------------------------------------------------------------------
# XML 合并（去重/更新）
# ----------------------------------------------------------------------
def merge_xml(target_xml, src_xml, backup=True, log_func=print):
    """
    将 src_xml 的设备定义合并到 target_xml
    :param target_xml: 目标文件路径（JFlash 目录下的 JLinkDevices.xml）
    :param src_xml:    源文件路径（补丁包中的 JLinkDevices.xml）
    :param backup:     是否备份原文件
    :param log_func:   日志输出函数（默认为 print）
    """
    if not os.path.exists(src_xml):
        log_func(f"  警告：源文件 {src_xml} 不存在，跳过")
        return

    if backup and os.path.exists(target_xml):
        bak_file = target_xml + '.bak'
        if not os.path.exists(bak_file):
            shutil.copy2(target_xml, bak_file)
            log_func(f"  已备份原文件至 {bak_file}")

    if not os.path.exists(target_xml):
        shutil.copy2(src_xml, target_xml)
        log_func(f"  已创建 {target_xml}")
        return

    try:
        tree_target = ET.parse(target_xml)
        root_target = tree_target.getroot()
        tree_src = ET.parse(src_xml)
        root_src = tree_src.getroot()
    except ET.ParseError as e:
        log_func(f"  XML 解析失败: {e}")
        return

    # 收集目标文件中的现有设备名称
    existing_names = set()
    for elem in root_target:
        name, found = get_device_name(elem)
        if found:
            existing_names.add(name)
        else:
            tag = elem.tag
            idx = list(root_target).index(elem)
            placeholder = f"__unnamed_{tag}_{idx}__"
            existing_names.add(placeholder)

    added = 0
    replaced = 0
    skipped_no_name = 0

    for elem_src in root_src:
        name, found = get_device_name(elem_src)

        if not found:
            root_target.append(elem_src)
            added += 1
            skipped_no_name += 1
            log_func(f"   ⚠️ 设备无 Name 属性，已直接追加（XML 结构：{elem_src.tag})")
            continue

        if name not in existing_names:
            root_target.append(elem_src)
            added += 1
            existing_names.add(name)
            log_func(f"   ✅ 新增设备: {name}")
        else:
            # 同名设备：移除旧节点，添加新节点（更新）
            for idx, elem_target in enumerate(root_target):
                target_name, _ = get_device_name(elem_target)
                if target_name == name:
                    root_target.remove(elem_target)
                    break
            root_target.append(elem_src)
            replaced += 1
            log_func(f"   🔄 更新设备: {name}")

    tree_target.write(target_xml, encoding='utf-8', xml_declaration=True)
    log_func(f"  XML 合并完成：新增 {added} 项，更新 {replaced} 项")


# ----------------------------------------------------------------------
# 扫描有效的 MCU 补丁文件夹
# ----------------------------------------------------------------------
def get_mcu_folders(patch_root):
    """
    返回 patch_root 下所有包含 JLinkDevices.xml 且至少有一个子文件夹的目录
    """
    valid_folders = []
    base = Path(patch_root).resolve()
    for item in base.iterdir():
        if item.is_dir():
            xml_path = item / 'JLinkDevices.xml'
            if xml_path.is_file():
                subdirs = [d for d in item.iterdir() if d.is_dir()]
                if subdirs:
                    valid_folders.append(str(item))
    return valid_folders


# ----------------------------------------------------------------------
# 设备文件夹复制（核心逻辑，不包含交互）
# ----------------------------------------------------------------------
def copy_devices(src_mcu_folder, jflash_dir, select_callback, log_func=print):
    """
    复制设备文件夹到 JFlash 根目录，保持原名
    :param src_mcu_folder:  补丁文件夹路径（包含 JLinkDevices.xml 和子文件夹）
    :param jflash_dir:      JFlash 安装目录
    :param select_callback: 选择设备子文件夹的回调函数，接收参数 (mcu_folder, parent_widget=None)
                            返回 (selected_path, found) 或 (None, False)
    :param log_func:        日志输出函数
    """
    src_dev_folder, found = select_callback(src_mcu_folder)
    if not found:
        log_func(f"  错误：未选择设备文件夹，跳过")
        return

    src_folder_name = os.path.basename(src_dev_folder)
    log_func(f"  设备文件夹: {src_folder_name}")

    dst_target = os.path.join(jflash_dir, src_folder_name)

    if not os.path.exists(dst_target):
        shutil.copytree(src_dev_folder, dst_target)
        log_func(f"  已创建 {dst_target}")
    else:
        try:
            shutil.copytree(src_dev_folder, dst_target, dirs_exist_ok=True)
        except TypeError:
            # Python < 3.8
            for root, dirs, files in os.walk(src_dev_folder):
                rel_path = os.path.relpath(root, src_dev_folder)
                dest_dir = os.path.join(dst_target, rel_path)
                os.makedirs(dest_dir, exist_ok=True)
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dest_dir, file)
                    shutil.copy2(src_file, dst_file)
        log_func(f"  文件夹合并完成: {dst_target}")


# ----------------------------------------------------------------------
# 一键处理单个补丁（组合 XML 合并 + 文件夹复制）
# ----------------------------------------------------------------------
def process_patch(folder, jflash_dir, select_callback, backup=True, log_func=print):
    """
    处理单个 MCU 补丁
    """
    src_xml = os.path.join(folder, 'JLinkDevices.xml')
    target_xml = os.path.join(jflash_dir, 'JLinkDevices.xml')

    merge_xml(target_xml, src_xml, backup=backup, log_func=log_func)
    copy_devices(folder, jflash_dir, select_callback, log_func=log_func)

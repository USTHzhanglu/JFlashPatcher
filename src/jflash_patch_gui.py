#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JFlash 设备补丁工具 - PySide6 GUI 版本
依赖 jflash_patch_core.py
"""

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QTextEdit,
    QProgressBar,
    QMessageBox,
    QInputDialog,
    QGroupBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, Slot
from PySide6.QtGui import QFont, QTextCursor, QAction

from theme import ModernTheme

# 导入核心函数
from jflash_patch_core import find_jflash_path, get_mcu_folders, process_patch

# 版本信息
__version__ = "1.0.0"
__author__ = "USTHzhanglu@outlook.com"
__deepseek__ = "Powered by DeepSeek"


# ----------------------------------------------------------------------
# GUI 交互：选择设备子文件夹（PySide6 弹窗）
# ----------------------------------------------------------------------
def select_folder_gui(mcu_folder, parent_widget=None):
    """
    PySide6 弹窗选择子文件夹
    parent_widget: 父窗口，用于显示对话框
    """
    subdirs = [d for d in Path(mcu_folder).iterdir() if d.is_dir()]
    subdir_names = [d.name for d in subdirs]

    if not subdirs:
        return None, False

    # 优先 JLinkDevices
    if "JLinkDevices" in subdir_names:
        idx = subdir_names.index("JLinkDevices")
        return str(subdirs[idx]), True

    # 其次 Devices
    if "Devices" in subdir_names:
        idx = subdir_names.index("Devices")
        return str(subdirs[idx]), True

    # 只有一个子文件夹
    if len(subdirs) == 1:
        return str(subdirs[0]), True

    # 多个子文件夹 -> 弹窗让用户选择
    item, ok = QInputDialog.getItem(
        parent_widget,
        "选择设备文件夹",
        f"在 {os.path.basename(mcu_folder)} 下发现多个子文件夹，请选择包含算法文件的文件夹：",
        subdir_names,
        0,
        False,
    )
    if ok and item:
        idx = subdir_names.index(item)
        return str(subdirs[idx]), True
    else:
        return None, False


# ----------------------------------------------------------------------
# 工作线程（避免阻塞 UI）
# ----------------------------------------------------------------------
class PatchWorker(QObject):
    log_signal = Signal(str)
    finished_signal = Signal()
    progress_signal = Signal(int)

    def __init__(self, jflash_dir, selected_folders, backup):
        super().__init__()
        self.jflash_dir = jflash_dir
        self.selected_folders = selected_folders
        self.backup = backup
        self.parent_widget = None

    def set_parent_widget(self, widget):
        self.parent_widget = widget

    @Slot()
    def run(self):
        total = len(self.selected_folders)
        for idx, folder in enumerate(self.selected_folders):
            self.log_signal.emit(
                f"\n--- 正在处理 ({idx+1}/{total}): {os.path.basename(folder)} ---"
            )

            # 使用 GUI 版选择回调
            process_patch(
                folder,
                self.jflash_dir,
                select_callback=lambda f, p=self.parent_widget: select_folder_gui(f, p),
                backup=self.backup,
                log_func=self.log_signal.emit,
            )

            self.progress_signal.emit(int((idx + 1) / total * 100))

        self.log_signal.emit("\n所有操作完成！")
        self.log_signal.emit("提示：如果 JFlash 正在运行，请重启程序以使设备列表生效。")
        self.finished_signal.emit()


class OptionsDialog(QDialog):
    """选项设置对话框"""

    def __init__(self, parent=None, backup_enabled=True):
        super().__init__(parent)
        self.setWindowTitle("选项设置")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 复选框
        self.backup_checkbox = QCheckBox("自动备份 JLinkDevices.xml")
        self.backup_checkbox.setChecked(backup_enabled)
        layout.addWidget(self.backup_checkbox)

        layout.addStretch()

        # 按钮（确定/取消）
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def is_backup_enabled(self):
        """获取备份选项状态"""
        return self.backup_checkbox.isChecked()


# ----------------------------------------------------------------------
# 主窗口
# ----------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JFlash 设备补丁工具 (GUI)")
        self.setMinimumSize(900, 700)

        self.worker_thread = None
        self.worker = None
        self.backup_enabled = True  # 默认开启备份

        self.init_ui()
        self.create_menu()
        self.load_default_jflash_path()
        self.setStyleSheet(ModernTheme.STYLESHEET)
        default_patch_dir = os.path.dirname(os.path.abspath(__file__))
        self.patch_root_edit.setText(default_patch_dir + "/patchs")
        self.scan_patches()

    def init_ui(self):
        """初始化用户界面（左右分栏：左侧补丁列表，右侧日志）"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ===== 1. JFlash 安装目录组 =====
        jlink_group = QGroupBox("JFlash 安装目录")
        jlink_layout = QHBoxLayout()
        jlink_layout.setContentsMargins(12, 16, 12, 12)

        self.jlink_path_edit = QLineEdit()
        self.jlink_path_edit.setPlaceholderText("请选择或自动检测...")
        self.jlink_path_edit.setReadOnly(True)
        self.jlink_browse_btn = QPushButton("浏览...")
        self.jlink_browse_btn.setObjectName("Secondary")
        self.jlink_browse_btn.clicked.connect(self.browse_jlink_path)
        self.jlink_detect_btn = QPushButton("自动检测")
        self.jlink_detect_btn.setObjectName("Secondary")
        self.jlink_detect_btn.clicked.connect(self.detect_jflash_path)

        jlink_layout.addWidget(self.jlink_path_edit, 1)
        jlink_layout.addWidget(self.jlink_browse_btn)
        jlink_layout.addWidget(self.jlink_detect_btn)
        jlink_group.setLayout(jlink_layout)
        main_layout.addWidget(jlink_group)

        # ===== 2. MCU 补丁根目录组 =====
        patch_root_group = QGroupBox("MCU 补丁根目录")
        patch_root_layout = QHBoxLayout()
        patch_root_layout.setContentsMargins(12, 16, 12, 12)

        self.patch_root_edit = QLineEdit()
        self.patch_root_edit.setPlaceholderText("包含多个 MCU 补丁文件夹的目录...")
        self.patch_root_edit.setReadOnly(True)
        self.patch_root_browse_btn = QPushButton("浏览...")
        self.patch_root_browse_btn.setObjectName("Secondary")
        self.patch_root_browse_btn.clicked.connect(self.browse_patch_root)
        self.scan_btn = QPushButton("扫描补丁")
        self.scan_btn.setObjectName("Secondary")
        self.scan_btn.clicked.connect(self.scan_patches)

        patch_root_layout.addWidget(self.patch_root_edit, 1)
        patch_root_layout.addWidget(self.patch_root_browse_btn)
        patch_root_layout.addWidget(self.scan_btn)
        patch_root_group.setLayout(patch_root_layout)
        main_layout.addWidget(patch_root_group)

        # ===== 3. 创建水平分割器（左侧补丁列表，右侧日志）=====
        from PySide6.QtWidgets import QSplitter
        from PySide6.QtCore import Qt

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)  # 禁止完全折叠

        # ----- 左侧：日志组 -----
        log_group = QGroupBox("操作日志")
        log_group.setMinimumWidth(350)
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(12, 10, 12, 12)
        log_layout.setSpacing(8)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        log_layout.addWidget(self.progress_bar)

        log_group.setLayout(log_layout)

        # ----- 右侧：补丁列表组 -----
        patch_group = QGroupBox("可用的 MCU 补丁")
        patch_layout = QVBoxLayout()
        patch_layout.setContentsMargins(12, 10, 12, 12)
        patch_layout.setSpacing(8)

        self.patch_list = QListWidget()
        self.patch_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        patch_layout.addWidget(self.patch_list)

        # 全选/取消按钮（右对齐）
        select_btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setObjectName("Secondary")
        self.select_all_btn.clicked.connect(self.select_all)
        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.setObjectName("Secondary")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        select_btn_layout.addStretch()
        select_btn_layout.addWidget(self.select_all_btn)
        select_btn_layout.addWidget(self.deselect_all_btn)
        patch_layout.addLayout(select_btn_layout)

        patch_group.setLayout(patch_layout)

        splitter.addWidget(log_group)
        splitter.addWidget(patch_group)
        # 设置初始宽度比例：左侧70%，右侧30%（可自由拖动）
        splitter.setStretchFactor(0, 7)  # 补丁列表
        splitter.setStretchFactor(1, 3)  # 日志
        splitter.setChildrenCollapsible(False)  # 禁止完全折叠

        # 将分割器加入主布局，并设置拉伸因子为1（占满剩余空间）
        main_layout.addWidget(splitter, 1)

        # ===== 4. 底部选项和开始按钮 =====
        option_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始打补丁")
        self.start_btn.clicked.connect(self.start_patch)
        self.start_btn.setEnabled(False)
        option_layout.addWidget(self.start_btn)

        main_layout.addLayout(option_layout)

    def create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        # ----- 选项菜单 -----
        options_action = QAction("选项", self)
        options_action.triggered.connect(self.show_options_dialog)
        menubar.addAction(options_action)
        # 关于动作
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        menubar.addAction(about_action)

    def show_options_dialog(self):
        """显示选项设置对话框"""
        dialog = OptionsDialog(self, backup_enabled=self.backup_enabled)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.backup_enabled = dialog.is_backup_enabled()
            # 可在此添加状态栏提示（可选）
            # self.statusBar().showMessage(f"备份选项已{'开启' if self.backup_enabled else '关闭'}", 2000)

    def show_about(self):
        """显示关于对话框"""
        about_text = f"""
        <h2>JFlash 设备补丁工具</h2>
        <p><b>版本:</b> {__version__}</p>
        <p><b>作者:</b> {__author__}</p>
        <p><b>说明:</b> 用于向 JFlash 添加自定义 MCU 设备补丁。</p>
        <p><b>核心功能:</b> 合并 JLinkDevices.xml，复制设备算法文件夹。</p>
        <p><b>{__deepseek__}</b></p>
        <p>此软件使用 PySide6 开发，遵循 MIT 许可证。</p>
        <hr>
        <p><i>感谢 DeepSeek 提供 AI 辅助编码支持以及主题设计。</i></p>
        """
        QMessageBox.about(self, "关于", about_text)

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------
    def load_default_jflash_path(self):
        path = find_jflash_path()
        if path:
            self.jlink_path_edit.setText(path)

    def browse_jlink_path(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择 JFlash 安装目录", self.jlink_path_edit.text()
        )
        if dir_path:
            self.jlink_path_edit.setText(dir_path)

    def detect_jflash_path(self):
        path = find_jflash_path()
        if path:
            self.jlink_path_edit.setText(path)
            self.log(f"自动检测到 JFlash 目录: {path}")
        else:
            QMessageBox.warning(
                self, "未找到", "无法自动定位 JFlash 目录，请手动选择。"
            )

    def browse_patch_root(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择 MCU 补丁根目录", self.patch_root_edit.text()
        )
        if dir_path:
            self.patch_root_edit.setText(dir_path)
            self.scan_patches()

    def scan_patches(self):
        patch_root = self.patch_root_edit.text().strip()
        if not patch_root or not os.path.isdir(patch_root):
            QMessageBox.warning(self, "无效目录", "请先选择有效的补丁根目录。")
            return

        self.patch_list.clear()
        folders = get_mcu_folders(patch_root)
        if not folders:
            self.log(f"在 {patch_root} 下未找到有效的 MCU 补丁文件夹。")
            self.start_btn.setEnabled(False)
            return

        for folder in folders:
            item = QListWidgetItem(os.path.basename(folder))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, folder)
            self.patch_list.addItem(item)

        self.log(f"扫描完成，共找到 {len(folders)} 个补丁。")
        self.start_btn.setEnabled(True)

    def select_all(self):
        for i in range(self.patch_list.count()):
            item = self.patch_list.item(i)
            item.setCheckState(Qt.CheckState.Checked)

    def deselect_all(self):
        for i in range(self.patch_list.count()):
            item = self.patch_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)

    def log(self, message):
        self.log_text.append(message)
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def start_patch(self):
        jflash_dir = self.jlink_path_edit.text().strip()
        if not jflash_dir or not os.path.isdir(jflash_dir):
            QMessageBox.warning(self, "无效目录", "请先选择有效的 JFlash 安装目录。")
            return

        selected_folders = []
        for i in range(self.patch_list.count()):
            item = self.patch_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                folder_path = item.data(Qt.ItemDataRole.UserRole)
                selected_folders.append(folder_path)

        if not selected_folders:
            QMessageBox.warning(self, "无选中", "请至少勾选一个要打的补丁。")
            return

        reply = QMessageBox.question(
            self,
            "确认",
            f"准备打 {len(selected_folders)} 个补丁到目录：\n{jflash_dir}\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.start_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()

        self.worker_thread = QThread()
        self.worker = PatchWorker(
            jflash_dir, selected_folders, backup=self.backup_enabled
        )
        self.worker.set_parent_widget(self)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.worker_thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self.on_patch_finished)

        self.worker_thread.start()

    def on_patch_finished(self):
        self.start_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "完成", "补丁操作已全部完成！")


# ----------------------------------------------------------------------
# 程序入口
# ----------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

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
    QSplitter,
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


def auto_select_device_folder(mcu_folder, parent_widget=None):
    """
    自动选择设备子文件夹（无用户交互）
    规则：优先 JLinkDevices -> Devices -> 唯一子文件夹 -> 多个子文件夹时选择第一个
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

    # 多个子文件夹：选择第一个并记录警告（通过日志）
    # 注意：这里无法直接输出日志，将在 run 中处理
    return str(subdirs[0]), True


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
        self._is_running = True

    def stop(self):
        self._is_running = False

    def set_parent_widget(self, widget):
        self.parent_widget = widget

    @staticmethod
    def auto_select_device_folder(mcu_folder):
        """自动选择设备子文件夹，无交互"""
        from pathlib import Path

        subdirs = [d for d in Path(mcu_folder).iterdir() if d.is_dir()]
        subdir_names = [d.name for d in subdirs]

        if not subdirs:
            return None, False

        if "JLinkDevices" in subdir_names:
            idx = subdir_names.index("JLinkDevices")
            return str(subdirs[idx]), True

        if "Devices" in subdir_names:
            idx = subdir_names.index("Devices")
            return str(subdirs[idx]), True

        if len(subdirs) == 1:
            return str(subdirs[0]), True

        # 多个子文件夹，选择第一个（并记录日志，将在 run 中处理）
        return str(subdirs[0]), True

    @Slot()
    def run(self):
        total = len(self.selected_folders)
        for idx, folder in enumerate(self.selected_folders):
            if not self._is_running:  # 检查停止标志
                self.log_signal.emit("用户中断操作，停止处理。")
                break
            self.log_signal.emit(
                f"\n--- 正在处理 ({idx+1}/{total}): {os.path.basename(folder)} ---"
            )

            # 自动选择设备子文件夹
            selected_path, found = self.auto_select_device_folder(folder)
            if not found:
                self.log_signal.emit(
                    f"  错误：{os.path.basename(folder)} 下无有效子文件夹，跳过"
                )
                continue

            # 检查是否为多选且自动选择了第一个，记录提示
            subdirs = [d.name for d in Path(folder).iterdir() if d.is_dir()]
            if (
                len(subdirs) > 1
                and "JLinkDevices" not in subdirs
                and "Devices" not in subdirs
            ):
                self.log_signal.emit(
                    f"  检测到多个子文件夹，自动选择第一个：{selected_path}"
                )

            # 使用 process_patch，传入固定结果的回调
            process_patch(
                folder,
                self.jflash_dir,
                select_callback=lambda f, p=None: (selected_path, True),
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
        self.jflash_valid = False  # JFlash 安装目录是否有效
        self.patch_root_valid = False  # MCU 补丁根目录是否有效

        self.init_ui()
        self.create_menu()
        self.load_default_jflash_path()
        self.set_default_patch_root()
        self.update_start_button_state()
        self.setStyleSheet(ModernTheme.STYLESHEET)

    def init_ui(self):
        """初始化用户界面（左右分栏：左侧补丁列表，右侧日志）"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)
        button_width = 85
        # ===== 1. JFlash 安装目录组 =====
        jlink_group = QGroupBox("JFlash 安装目录")
        jlink_layout = QHBoxLayout()
        jlink_layout.setContentsMargins(12, 16, 12, 12)

        self.jlink_path_edit = QLineEdit()
        self.jlink_path_edit.setPlaceholderText("请选择或自动检测...")
        self.jlink_path_edit.setReadOnly(True)
        self.jlink_status_label = QLabel()  # 新增状态标签
        self.jlink_status_label.setFixedSize(20, 20)  # 固定大小
        self.jlink_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.jlink_browse_btn = QPushButton("浏览...")
        self.jlink_browse_btn.setObjectName("Secondary")
        self.jlink_browse_btn.setFixedWidth(button_width)
        self.jlink_browse_btn.clicked.connect(self.browse_jlink_path)

        jlink_layout.addWidget(self.jlink_path_edit, 1)
        jlink_layout.addWidget(self.jlink_status_label)  # 新增
        jlink_layout.addWidget(self.jlink_browse_btn)
        jlink_group.setLayout(jlink_layout)
        main_layout.addWidget(jlink_group)

        # ===== 2. MCU 补丁根目录组 =====
        patch_root_group = QGroupBox("MCU 补丁根目录")
        patch_root_layout = QHBoxLayout()
        patch_root_layout.setContentsMargins(12, 16, 12, 12)

        self.patch_root_edit = QLineEdit()
        self.patch_root_edit.setPlaceholderText("包含多个 MCU 补丁文件夹的目录...")
        self.patch_root_edit.setReadOnly(True)
        self.patch_root_status_label = QLabel()  # 状态标签
        self.patch_root_status_label.setFixedSize(20, 20)
        self.patch_root_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.patch_root_browse_btn = QPushButton("浏览...")
        self.patch_root_browse_btn.setObjectName("Secondary")
        self.patch_root_browse_btn.setFixedWidth(button_width)
        self.patch_root_browse_btn.clicked.connect(self.browse_patch_root)

        patch_root_layout.addWidget(self.patch_root_edit, 1)
        patch_root_layout.addWidget(self.patch_root_status_label)  # 新增
        patch_root_layout.addWidget(self.patch_root_browse_btn)
        patch_root_group.setLayout(patch_root_layout)
        main_layout.addWidget(patch_root_group)

        # ===== 3. 创建水平分割器（左侧补丁列表，右侧日志）=====

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
    # 验证函数
    # ------------------------------------------------------------------
    def _check_jflash_exe(self, path):
        """检查 JFlash 可执行文件是否存在"""
        if not path or not os.path.isdir(path):
            return False
        is_windows = sys.platform.startswith("win")
        exe_name = "jflash.exe" if is_windows else "JFlashExe"
        exe_path = os.path.join(path, exe_name)
        exe_exists = os.path.isfile(exe_path)
        return exe_exists

    def validate_jflash_path(self, path=None):
        if path is None:
            path = self.jlink_path_edit.text().strip()
        is_valid = self._check_jflash_exe(path)
        self.jflash_valid = is_valid
        self.jlink_status_label.setText("✓" if is_valid else "✗")
        self.jlink_status_label.setProperty("valid", is_valid)
        self.jlink_path_edit.setProperty("valid", is_valid)
        # 强制刷新样式
        self.jlink_status_label.style().unpolish(self.jlink_status_label)
        self.jlink_status_label.style().polish(self.jlink_status_label)
        self.jlink_path_edit.style().unpolish(self.jlink_path_edit)
        self.jlink_path_edit.style().polish(self.jlink_path_edit)

        return is_valid

    def validate_patch_root(self, path=None):
        """验证 MCU 根目录下是否存在有效补丁包，更新状态图标"""
        if path is None:
            path = self.patch_root_edit.text().strip()

        if not path or not os.path.isdir(path):
            # 路径无效或不存在
            self.patch_root_status_label.setText("✗")
            self.patch_root_status_label.setProperty("valid", False)
            self.patch_root_edit.setProperty("valid", False)
            return False

        # 调用核心函数检查有效补丁
        folders = get_mcu_folders(path)
        has_valid = len(folders) > 0
        self.patch_root_valid = has_valid
        self.patch_root_edit.setProperty("valid", has_valid)
        self.patch_root_status_label.setProperty("valid", has_valid)
        self.patch_root_status_label.setText("✓" if has_valid else "✗")
        # 强制刷新样式
        self.patch_root_edit.style().unpolish(self.patch_root_edit)
        self.patch_root_edit.style().polish(self.patch_root_edit)
        self.patch_root_status_label.style().unpolish(self.patch_root_status_label)
        self.patch_root_status_label.style().polish(self.patch_root_status_label)

        return has_valid

    def is_directory_writable(self, path):
        """通过实际尝试写入测试目录是否可写（准确，无长时间阻塞）"""
        test_file = os.path.join(path, "__jflash_patch_test.tmp")
        try:
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return True
        except (OSError, IOError, PermissionError):
            return False

    def update_start_button_state(self):
        """更新开始按钮状态：两个目录都有效时才启用"""
        self.start_btn.setEnabled(self.jflash_valid and self.patch_root_valid)

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------
    def load_default_jflash_path(self):
        path = find_jflash_path()
        if path:
            self.jlink_path_edit.setText(path)
            self.jflash_valid = self.validate_jflash_path(path)
            self.log(f"自动检测到 JFlash 目录: {path}")
        else:
            self.log("未检测到 JFlash 目录，请手动选择。")

    def set_default_patch_root(self):
        """启动时从候选路径列表中查找第一个包含有效补丁的目录，并自动扫描"""
        # 候选路径列表（按优先级排序）
        candidate_paths = [
            os.path.dirname(os.path.abspath(__file__)),  # GUI 所在目录
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "../patchs"),
            os.getcwd(),  # 当前工作目录
            os.path.join(os.getcwd(), "patchs"),
        ]

        selected_path = None
        for path in candidate_paths:
            if not os.path.isdir(path):
                continue
            # 检查是否包含有效补丁
            folders = get_mcu_folders(path)
            if folders:
                selected_path = path
                break
        if selected_path is None:
            # 回退到GUI所在目录（即使无效）
            selected_path = os.path.dirname(os.path.abspath(__file__))
        # 设置到输入框并验证/扫描
        self.patch_root_edit.setText(selected_path)
        self.scan_patches()

    def browse_jlink_path(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择 JFlash 安装目录", self.jlink_path_edit.text()
        )
        if dir_path:
            self.jflash_valid = self.validate_jflash_path(dir_path)  # 手动调用验证
            if self.jflash_valid:
                self.log(f"JFlash 目录验证通过: {dir_path}")
            else:
                self.log(f"JFlash 目录验证失败: {dir_path}")
            self.jlink_path_edit.setText(dir_path)
            self.update_start_button_state()

    def browse_patch_root(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择 MCU 补丁根目录", self.patch_root_edit.text()
        )
        if dir_path:
            self.patch_root_edit.setText(dir_path)
            self.scan_patches()
            self.update_start_button_state()

    def scan_patches(self):
        patch_root = self.patch_root_edit.text().strip()
        # 先验证并更新状态
        self.patch_root_valid = self.validate_patch_root(patch_root)
        self.patch_list.clear()
        folders = get_mcu_folders(patch_root)
        if not folders:
            self.log(f"在 {patch_root} 下未找到有效的 MCU 补丁文件夹。")
            return

        for folder in folders:
            item = QListWidgetItem(os.path.basename(folder))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, folder)
            self.patch_list.addItem(item)

        self.log(f"扫描完成，共找到 {len(folders)} 个补丁。")

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
        # ===== 新增：检查目录写权限 =====
        if not self.is_directory_writable(jflash_dir):
            reply = QMessageBox.critical(
                self,
                "权限不足",
                f"JFlash 安装目录位于系统保护位置：\n{jflash_dir}\n\n"
                "当前程序没有写入权限。\n"
                "请以管理员身份重新运行此程序。",
                QMessageBox.StandardButton.Ok,
            )
            return False  # 终止操作
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
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "完成", "补丁操作已全部完成！")

    def closeEvent(self, event):
        """重写关闭事件，确保线程安全退出"""
        if self.worker_thread and self.worker_thread.isRunning():
            # 询问用户是否中断操作
            reply = QMessageBox.question(
                self,
                "确认退出",
                "正在执行补丁操作，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                # 通知工作线程停止
                if self.worker:
                    self.worker.stop()
                self.worker_thread.quit()
                # 等待线程结束，超时2秒
                if not self.worker_thread.wait(2000):
                    # 超时则强制终止（不推荐，但作为最后手段）
                    self.worker_thread.terminate()
                    self.worker_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


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

class ModernTheme:
    """
    JFlash 补丁工具专属主题
    - 固定像素设计，不依赖系统缩放
    - 颜色：蓝白灰专业风格
    - 尺寸：全局12px，控件紧凑有序
    - 适用于 PySide6
    """

    # ---------- 颜色系统 ----------
    BG_MAIN = "#F8FAFC"  # 主背景（极浅灰蓝）
    BG_CARD = "#FFFFFF"  # 卡片/控件背景（纯白）
    TEXT_PRIMARY = "#0F172A"  # 主要文本（深灰蓝）
    TEXT_SECONDARY = "#475569"  # 辅助文本（中灰）
    BORDER = "#E2E8F0"  # 边框色（浅灰）
    BORDER_FOCUS = "#94A3B8"  # 聚焦边框（中灰）
    PRIMARY = "#2563EB"  # 主色调（蓝）
    PRIMARY_HOVER = "#1D4ED8"  # 主色悬停（深蓝）
    PRIMARY_PRESSED = "#1E3A8A"  # 主色按下（更深蓝）
    SELECTED_BG = "#EFF6FF"  # 选中背景（淡蓝）
    HOVER_BG = "#F1F5F9"  # 悬停背景（极淡灰）
    DISABLED_BG = "#F1F5F9"  # 禁用背景
    DISABLED_TEXT = "#94A3B8"  # 禁用文本
    PROGRESS_BG = "#E2E8F0"  # 进度条背景
    SCROLLBAR_HANDLE = "#CBD5E1"  # 滚动条滑块
    SCROLLBAR_HOVER = "#94A3B8"  # 滚动条滑块悬停
    # 验证图标样式
    VALID_COLOR = "#10B981"  # 绿色（成功）
    INVALID_COLOR = "#EF4444"  # 红色（错误）
    ICON_SIZE = 16  # 图标字体大小（px）
    # ---------- 样式表 ----------
    STYLESHEET = f"""
        /* ========== 全局基础 ========== */
        QMainWindow, QDialog {{
            background-color: {BG_MAIN};
        }}
        QWidget {{
            font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif;
            font-size: 12px;
            color: {TEXT_PRIMARY};
        }}

        /* ========== 输入框 ========== */
        QLineEdit {{
            padding: 7px 12px;
            border: 1px solid {BORDER};
            border-radius: 6px;
            background-color: {BG_CARD};
            selection-background-color: {PRIMARY};
            selection-color: white;
        }}
        QLineEdit:focus {{
            border: 1px solid {BORDER_FOCUS};
        }}
        QLineEdit:disabled {{
            background-color: {DISABLED_BG};
            color: {DISABLED_TEXT};
        }}
        QLineEdit[valid="true"] {{
            border: 1px solid #10B981;   /* 绿色边框 */
        }}
        QLineEdit[valid="false"] {{
            border: 1px solid #EF4444;   /* 红色边框 */
        }}

        /* ========== 按钮 ========== */
        QPushButton {{
            padding: 7px 16px;
            background-color: {PRIMARY};
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {PRIMARY_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {PRIMARY_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {DISABLED_BG};
            color: {DISABLED_TEXT};
        }}
        /* 次按钮（浏览/自动检测等） */
        QPushButton#Secondary {{
            background-color: white;
            color: {PRIMARY};
            border: 1px solid {BORDER};
            font-weight: 500;
        }}
        QPushButton#Secondary:hover {{
            background-color: {HOVER_BG};
            border-color: {PRIMARY};
        }}
        QPushButton#Secondary:pressed {{
            background-color: {SELECTED_BG};
        }}

        /* ========== 分组框（合理紧凑）========== */
        QGroupBox {{
            background-color: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: 8px;
            margin-top: 6px;
            padding-top: 3px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {TEXT_PRIMARY};
        }}

        /* ========== 列表控件（带复选框）========== */
        QListWidget {{
            background-color: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: 8px;
            outline: none;
            padding: 2px;
        }}
        QListWidget::item {{
            padding: 4px 6px;
            border-radius: 4px;
            margin: 1px 0;
        }}
        QListWidget::item:hover {{
            background-color: {HOVER_BG};
        }}
        QListWidget::item:selected {{
            background-color: {SELECTED_BG};
            color: {PRIMARY};
        }}

        /* ---------- 复选框（位于列表内）---------- */
        QCheckBox {{
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 12px;
            height: 12px;
            border: 1px solid {BORDER};
            border-radius: 4px;
            background-color: white;
        }}
        QCheckBox::indicator:checked {{
            background-color: {PRIMARY};
            border-color: {PRIMARY};
            image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24'%3E%3Cpath fill='white' d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z'/%3E%3C/svg%3E");
        }}
        QCheckBox::indicator:hover {{
            border-color: {PRIMARY};
        }}
        QCheckBox::indicator:disabled {{
            background-color: {DISABLED_BG};
            border-color: {BORDER};
        }}

        /* ========== 日志文本框 ========== */
        QTextEdit {{
            background-color: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 10px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.5;
        }}
        QTextEdit:focus {{
            border: 1px solid {BORDER_FOCUS};
        }}

        /* ========== 进度条 ========== */
        QProgressBar {{
            border: none;
            background-color: {PROGRESS_BG};
            border-radius: 4px;
            height: 8px;
            text-align: right;
            color: {TEXT_SECONDARY};
            font-size: 11px;
        }}
        QProgressBar::chunk {{
            background-color: {PRIMARY};
            border-radius: 4px;
        }}

        /* ========== 菜单栏（“关于”）========== */
        QMenuBar {{
            background-color: {BG_CARD};
            border-bottom: 1px solid {BORDER};
            padding: 2px 2px;
        }}
        QMenuBar::item {{
            padding: 4px 10px;
            border-radius: 4px;
            background-color: transparent;
        }}
        QMenuBar::item:selected {{
            background-color: {HOVER_BG};
        }}
        QMenuBar::item:pressed {{
            background-color: {SELECTED_BG};
        }}
        QMenu {{
            background-color: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 6px;
        }}
        QMenu::item {{
            padding: 6px 24px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: {HOVER_BG};
            color: {PRIMARY};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {BORDER};
            margin: 6px 0;
        }}

        /* ========== 消息对话框 ========== */
        QMessageBox {{
            background-color: {BG_CARD};
        }}
        QMessageBox QLabel {{
            color: {TEXT_PRIMARY};
            font-size: 12px;
        }}
        QMessageBox QPushButton {{
            min-width: 80px;
        }}

        /* ========== 滚动条（美观细条）========== */
        QScrollBar:vertical {{
            border: none;
            background-color: {BG_MAIN};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {SCROLLBAR_HANDLE};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {SCROLLBAR_HOVER};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        QScrollBar:horizontal {{
            border: none;
            background-color: {BG_MAIN};
            height: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {SCROLLBAR_HANDLE};
            border-radius: 4px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {SCROLLBAR_HOVER};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: none;
        }}

        /* ========== 标签 ========== */
        QLabel {{
            color: {TEXT_PRIMARY};
        }}
        QLabel[note="true"] {{
            color: {TEXT_SECONDARY};
            font-size: 11px;
        }}
        QLabel[valid="true"] {{ 
            color: {VALID_COLOR}; 
            font-weight: bold; 
            font-size: {ICON_SIZE}px; 
        }}
        QLabel[valid="false"] {{ 
            color:{INVALID_COLOR}; 
            font-weight: bold; 
            font-size: {ICON_SIZE}px;
        }}
        /* ========== 分割条 ========== */
        QSplitter::handle {{
            background-color: {BORDER};
            margin: 0px 1px;
        }}
        QSplitter::handle:hover {{
            background-color: {TEXT_SECONDARY};
        }}
        QSplitter::handle:horizontal {{
            margin-top: 10px;
            margin-bottom: 4px;
        }}
        QSplitter::handle:vertical {{
            height: 4px;
        }}
        QSplitter::handle:pressed {{
            background-color: {BORDER_FOCUS};   /* 按压时变蓝 */
        }}
    """

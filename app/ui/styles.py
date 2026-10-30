"""Shared visual tokens and application stylesheet."""

STYLESHEET = """
* { font-family: 'Segoe UI', 'Arial'; font-size: 13px; color: #d9e0ec; }
QMainWindow, QWidget#root, QWidget#page { background: #101319; }
QWidget { outline: none; }
QFrame#sidebar { background: #151922; border-right: 1px solid #272d39; }
QFrame#topbar { background: #13171e; border-bottom: 1px solid #272d39; }
QLabel { background: transparent; border: none; }
QLabel#brand { font-size: 23px; font-weight: 700; color: #f4f7fd; }
QLabel#brandSub { color: #718096; font-size: 11px; }
QLabel#eyebrow { color: #748198; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#pageTitle { font-size: 25px; font-weight: 650; color: #f5f7fb; }
QLabel#sectionTitle { font-size: 19px; font-weight: 650; color: #edf2fb; }
QLabel#cardTitle { font-size: 14px; font-weight: 600; color: #edf2fb; }
QLabel#muted { color: #8793a8; }
QLabel#small { color: #7e8ba1; font-size: 11px; }
QLabel#metric { font-size: 31px; font-weight: 650; color: #f3f6fc; }
QLabel#metricLabel { color: #a4afc0; font-size: 12px; }
QLabel#badge { background: #202b43; color: #97b9ff; border: 1px solid #2b4167; border-radius: 5px; padding: 3px 8px; font-size: 10px; font-weight: 700; }
QLabel#statusDot { color: #6fd5ae; font-size: 11px; }
QFrame#card, QFrame#tableCard { background: #191e27; border: 1px solid #2b3341; border-radius: 12px; }
QFrame#tableCard { background: #161b23; }
QFrame#notice { background: #192438; border: 1px solid #293e60; border-radius: 9px; }
QFrame#sideNote { background: #1b2230; border: 1px solid #2c3749; border-radius: 10px; }
QPushButton { background: #222a37; color: #d9e2f2; border: 1px solid #354052; border-radius: 7px; padding: 9px 14px; font-weight: 550; }
QPushButton:hover { background: #2b3647; border-color: #536581; }
QPushButton:pressed { background: #182233; }
QPushButton:disabled { background: #1c222c; color: #526075; border-color: #29313e; }
QPushButton#primary { background: #4d7cfa; color: white; border: 1px solid #5c88ff; }
QPushButton#primary:hover { background: #638dff; }
QPushButton#primary:pressed { background: #3d67dc; }
QPushButton#primary:disabled { background: #263655; border-color: #2c3b58; color: #697d9f; }
QPushButton#ghost { background: transparent; border-color: transparent; color: #9ab9fb; }
QPushButton#ghost:hover { background: #222d40; }
QPushButton#danger { color: #dca4a9; }
QPushButton#danger:disabled, QPushButton#ghost:disabled { color: #526075; }
QPushButton#nav { text-align: left; background: transparent; border: 1px solid transparent; color: #8f9bb0; padding: 12px 15px; border-radius: 8px; font-size: 13px; }
QPushButton#nav:hover { background: #202734; color: #dce4f4; }
QPushButton#nav:checked { background: #223251; color: #a8c4ff; border-color: #2d4470; }
QPushButton:focus-visible { border: 1px solid #8eb1ff; }
QTableView, QTableWidget { background: #161b23; alternate-background-color: #191f29; border: none; color: #c6d0e0; selection-background-color: #293e64; selection-color: #eaf0ff; gridline-color: #242d3b; }
QTableView::item { padding: 0px 14px; border: none; border-bottom: 1px solid #222a37; }
QTableView::item:selected { background: #283c60; }
QHeaderView { background: #1e2531; }
QHeaderView::section { background: #1e2531; color: #8d9bb1; border: none; border-bottom: 1px solid #303b4c; padding: 11px 14px; font-size: 11px; font-weight: 650; }
QTableCornerButton::section { background: #1e2531; border: none; }
QScrollBar:vertical { background: #151a22; width: 10px; margin: 3px; }
QScrollBar::handle:vertical { background: #39465a; min-height: 35px; border-radius: 3px; }
QScrollBar:horizontal { background: #151a22; height: 10px; margin: 3px; }
QScrollBar::handle:horizontal { background: #39465a; min-width: 35px; border-radius: 3px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QLineEdit, QComboBox, QSpinBox { background: #121720; border: 1px solid #354157; border-radius: 6px; padding: 9px; selection-background-color: #3f64ac; }
QLineEdit:focus, QComboBox:focus { border-color: #648dff; }
QComboBox::drop-down { border: none; width: 25px; }
QComboBox QAbstractItemView { background: #202837; border: 1px solid #3e4d65; selection-background-color: #344b78; }
QDialog, QMessageBox, QInputDialog { background: #191e28; }
QListWidget { background: #141922; border: 1px solid #2b3545; border-radius: 8px; padding: 4px; }
QListWidget::item { padding: 12px 8px; border-radius: 6px; margin: 2px; }
QListWidget::item:selected { background: #253b60; color: #dbe9ff; }
QListWidget::item:hover { background: #222e42; }
QProgressBar { border: none; background: #1d2a40; border-radius: 2px; max-height: 3px; }
QProgressBar::chunk { background: #638dff; border-radius: 2px; }
QStatusBar { background: #12161d; color: #7c8ba3; border-top: 1px solid #252d3a; font-size: 11px; }
QStatusBar::item { border: none; }
QToolTip { background: #253148; color: #e2ebfc; border: 1px solid #465b7e; padding: 6px; }
QCheckBox { spacing: 8px; }
"""

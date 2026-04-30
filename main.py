"""
파일명 수정 도우미 - 앱 진입점
"""

import sys
from app.ui.main_window import MainWindow


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()

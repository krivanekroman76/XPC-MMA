from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                               QStackedWidget, QFrame, QLabel, QSlider)
from PySide6.QtCore import Qt

from core import tr, LanguageSelector

# Here you will gradually uncomment other pages as you create them
from GUI_windows.admin_tools import AdminToolsPage
from GUI_windows.league_page import LeaguePage
from GUI_windows.race_page import RacePage
from GUI_windows.timing_page import TimingPage
from GUI_windows.leaderboard_page import LeaderboardPage

class DashboardWindow(QWidget):
    def __init__(self, db_service):
        super().__init__()
        self.db = db_service
        self.user_data = self.db.get_user_data(self.db.local_id)
        self.role = self.user_data.get("role", "user")

        self.setWindowTitle(f"{tr.t('app_title')} - {self.role.upper()}")
        self.setMinimumSize(1100, 700)

        self.nav_buttons = []
        self.page_widgets = {}

        self.setup_ui()

    def setup_ui(self):
        # Main horizontal layout (Sidebar | Content)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- SIDEBAR (Left panel) ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 10)

        # Logo / Title
        self.logo_label = QLabel("FireSport")
        self.logo_label.setObjectName("logo")
        self.sidebar_layout.addWidget(self.logo_label)
        self.sidebar_layout.addSpacing(30)

        # --- DYNAMIC MENU BUTTONS ---
        self.create_nav_menu()

        # Pushes the rest downwards
        self.sidebar_layout.addStretch() 

        # --- UX SETTINGS AT THE BOTTOM ---
        self.setup_ux_settings()

        # --- CONTENT FRAME (Right panel) ---
        self.pages = QStackedWidget()
        self.create_pages()

        # Assemble the main layout
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.pages)

    def get_allowed_pages(self):
        """Returns a list of allowed pages based on user role permissions."""
        role_permissions = {
            "super_admin": ["admin_tools", "leagues", "races", "timing", "leaderboard"],
            "admin": ["races", "timing", "leaderboard"],
            "writer": ["timing", "leaderboard"],
            "user": ["leaderboard"]
        }
        return role_permissions.get(self.role, ["leaderboard"])

    def setup_ux_settings(self):
        """Sets up the bottom part of the sidebar with UX settings (Language, Scale)."""
        ux_frame = QFrame()
        ux_frame.setObjectName("ux_frame")
        ux_layout = QVBoxLayout(ux_frame)

        # Language Selector
        self.lang_selector = LanguageSelector(self)
        self.settings_label = QLabel(tr.t("menu_settings"))
        ux_layout.addWidget(self.settings_label)
        ux_layout.addWidget(self.lang_selector)

        self.scale_label = QLabel(tr.t("lbl_scale"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(50, 200)
        self.scale_slider.setValue(100)
        ux_layout.addWidget(self.scale_label)
        ux_layout.addWidget(self.scale_slider)

        self.sidebar_layout.addWidget(ux_frame)

    def create_nav_menu(self):
        """Renders navigation buttons in the sidebar based on the user's role."""
        pages_to_show = self.get_allowed_pages()

        for page_id in pages_to_show:
            btn = QPushButton(tr.t(f"menu_{page_id}"))
            btn.setProperty("page_id", page_id) # Important for translation identification
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda checked, p=page_id: self.switch_page(p))
            
            self.sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            
        # Automatically select the first available button and switch to its page
        if self.nav_buttons and pages_to_show:
            self.nav_buttons[0].setChecked(True)
            self.switch_page(pages_to_show[0])

    def create_pages(self):
        """Instantiates pages for the QStackedWidget based on hierarchy/permissions."""
        allowed_pages = self.get_allowed_pages()

        if "admin_tools" in allowed_pages:
            self.page_widgets["admin_tools"] = AdminToolsPage(self.db, self)
            
        if "leagues" in allowed_pages:
            self.page_widgets["leagues"] = LeaguePage(self.db, self) 

        if "races" in allowed_pages:
            self.page_widgets["races"] = RacePage(self.db, self)

        if "timing" in allowed_pages:
            self.page_widgets["timing"] = TimingPage(self.db, self)
            
        if "leaderboard" in allowed_pages:
            self.page_widgets["leaderboard"] = LeaderboardPage(self.db, self)

        # Add instantiated widgets to the stacked widget
        for page_id in allowed_pages:
            if page_id in self.page_widgets:
                self.pages.addWidget(self.page_widgets[page_id])
                
    def switch_page(self, page_id):
        """Switches the displayed page and syncs the highlighted sidebar button."""
        widget = self.page_widgets.get(page_id)
        if widget:
            self.pages.setCurrentWidget(widget)
            
        # Visually synchronize the menu button if the page was switched programmatically
        for btn in self.nav_buttons:
            if btn.property("page_id") == page_id:
                btn.setChecked(True)
                break

    def retranslate_ui(self):
        """Updates UI text in the Dashboard and cascades to all its subpages."""
        # 1. Dashboard translations
        self.setWindowTitle(f"{tr.t('app_title')} - {self.role.upper()}")
        self.settings_label.setText(tr.t("menu_settings"))
        self.scale_label.setText(tr.t("lbl_scale"))
        
        # Sidebar buttons translations
        for btn in self.nav_buttons:
            page_id = btn.property("page_id")
            if page_id:
                btn.setText(tr.t(f"menu_{page_id}"))

        # 2. Cascade translation update to active subpages in QStackedWidget
        for i in range(self.pages.count()):
            page_widget = self.pages.widget(i)
            if hasattr(page_widget, "retranslate_ui"):
                page_widget.retranslate_ui()
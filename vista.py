import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFrame, QCheckBox, QDialog,
                             QProgressBar, QLineEdit, QStackedWidget, QFormLayout, QSpinBox, QComboBox)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

# =============================================================================
# TEMAS: Oscuro y Claro
# =============================================================================

CSS_OSCURO = """
    QMainWindow, QStackedWidget, QWidget#central_widget, QWidget#page_dash, QWidget#page_graficas, QWidget#page_parametros {
        background-color: #0B1120;
    }
    QLabel { background: transparent; color: #E2EAF4; font-family: 'Segoe UI', Arial; font-size: 13px; border: none; }

    QFrame#sidebar {
        background-color: #141E2E;
        border-right: 2px solid #1E3048;
    }
    QFrame#top_bar {
        background-color: #141E2E;
        border-bottom: 2px solid #1E3048;
    }
    QFrame#card {
        background-color: #162032;
        border-radius: 14px;
        border: 1px solid #1E3048;
    }
    QFrame#card_inner {
        background-color: #1A2840;
        border-radius: 10px;
        border: 1px solid #243450;
    }

    QComboBox {
        background-color: #0B1120; color: #E2EAF4;
        border: 1.5px solid #1E3048;
        border-radius: 8px; padding: 6px 12px; font-size: 13px; font-weight: 600;
    }
    QComboBox:focus { border: 1.5px solid #0EA5E9; }
    QComboBox::drop-down { border: none; width: 24px; }
    QComboBox QAbstractItemView {
        background-color: #141E2E; color: #E2EAF4;
        selection-background-color: #0EA5E9; selection-color: white;
        border: 1px solid #1E3048; border-radius: 6px; padding: 4px;
    }

    QPushButton.nav_btn {
        background-color: transparent; color: #7A90A8;
        font-size: 13px; font-weight: 600;
        text-align: left; padding: 11px 12px;
        border-radius: 8px; border: none;
    }
    QPushButton.nav_btn:hover { background-color: #1E3048; color: #56CFE1; }
    QPushButton.nav_btn:pressed { background-color: #243450; }

    QPushButton.nav_btn_activo {
        background-color: #1E3048; color: #56CFE1;
        font-size: 13px; font-weight: 700;
        text-align: left; padding: 11px 12px;
        border-radius: 8px; border-left: 3px solid #56CFE1;
    }

    QPushButton.btn_accion {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0369A1, stop:1 #0EA5E9);
        color: white; border-radius: 8px; padding: 10px 16px;
        font-weight: 700; font-size: 13px; border: none;
    }
    QPushButton.btn_accion:hover {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0284C7, stop:1 #38BDF8);
    }
    QPushButton.btn_accion:pressed { background-color: #075985; }

    QPushButton.btn_peligro {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #B91C1C, stop:1 #EF4444);
        color: white; border-radius: 8px; padding: 10px 16px;
        font-weight: 700; font-size: 13px; border: none;
    }
    QPushButton.btn_peligro:hover {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #DC2626, stop:1 #F87171);
    }

    QPushButton.btn_toggle {
        background-color: #1E3048; color: #CBD5E1;
        border-radius: 8px; padding: 8px 12px;
        font-size: 12px; font-weight: 600; border: 1px solid #243450;
        text-align: left;
    }
    QPushButton.btn_toggle:hover { background-color: #243450; color: #E2EAF4; }

    QTableWidget {
        background-color: #162032; color: #E2EAF4;
        font-size: 13px; font-family: 'Segoe UI', Arial;
        border-radius: 8px; border: 1px solid #1E3048;
        gridline-color: #1E3048;
        selection-background-color: #0EA5E9;
        selection-color: white;
        alternate-background-color: #1A2840;
    }
    QHeaderView::section {
        background-color: #0B1120; color: #56CFE1;
        font-weight: 700; font-size: 12.5px;
        border: none; border-bottom: 2px solid #1E3048;
        padding: 9px 6px;
    }
    QTableWidget::item { padding: 6px 6px; border: none; }
    QTableWidget::item:selected { background-color: #0EA5E9; color: white; }

    QLineEdit, QSpinBox {
        background-color: #0B1120; color: #E2EAF4;
        border: 1.5px solid #1E3048;
        border-radius: 8px; padding: 9px 12px; font-size: 13px;
    }
    QLineEdit:focus, QSpinBox:focus { border: 1.5px solid #0EA5E9; }
    QLineEdit::placeholder { color: #4A6280; }
    QSpinBox::up-button, QSpinBox::down-button { width: 18px; }

    QPushButton:disabled {
        background-color: #1E293B; color: #475569; border: 1px solid #334155;
    }
    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
        background-color: #0B1120; color: #64748B; border: 1.5px solid #1E293B;
    }

    QProgressBar {
        border: none; background-color: #1E3048;
        border-radius: 7px; height: 14px;
        text-align: center; color: transparent;
    }
    QProgressBar#prog_hum::chunk {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #F59E0B, stop:1 #EF4444);
        border-radius: 7px;
    }
    QProgressBar#prog_adc::chunk {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #06B6D4, stop:1 #3B82F6);
        border-radius: 7px;
    }

    QScrollBar:vertical {
        background: #0B1120; width: 8px; border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background: #1E3048; border-radius: 4px; min-height: 30px;
    }
    QScrollBar::handle:vertical:hover { background: #0EA5E9; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

    QScrollBar:horizontal {
        background: #0B1120; height: 8px; border-radius: 4px;
    }
    QScrollBar::handle:horizontal {
        background: #1E3048; border-radius: 4px; min-width: 30px;
    }
    QScrollBar::handle:horizontal:hover { background: #0EA5E9; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""

CSS_CLARO = """
    QMainWindow, QStackedWidget, QWidget#central_widget, QWidget#page_dash, QWidget#page_graficas, QWidget#page_parametros {
        background-color: #F0F4F8;
    }
    QLabel { background: transparent; color: #1E2D3D; font-family: 'Segoe UI', Arial; font-size: 13px; border: none; }

    QFrame#sidebar {
        background-color: #FFFFFF;
        border-right: 2px solid #DDE6EF;
    }
    QFrame#top_bar {
        background-color: #FFFFFF;
        border-bottom: 2px solid #DDE6EF;
    }
    QFrame#card {
        background-color: #FFFFFF;
        border-radius: 14px;
        border: 1px solid #DDE6EF;
    }
    QFrame#card_inner {
        background-color: #F7FAFC;
        border-radius: 10px;
        border: 1px solid #DDE6EF;
    }

    QComboBox {
        background-color: #F0F4F8; color: #1E2D3D;
        border: 1.5px solid #DDE6EF;
        border-radius: 8px; padding: 6px 12px; font-size: 13px; font-weight: 600;
    }
    QComboBox:focus { border: 1.5px solid #0284C7; }
    QComboBox::drop-down { border: none; width: 24px; }
    QComboBox QAbstractItemView {
        background-color: #FFFFFF; color: #1E2D3D;
        selection-background-color: #EBF4FF; selection-color: #0284C7;
        border: 1px solid #DDE6EF; border-radius: 6px; padding: 4px;
    }

    QPushButton.nav_btn {
        background-color: transparent; color: #64748B;
        font-size: 13px; font-weight: 600;
        text-align: left; padding: 11px 12px;
        border-radius: 8px; border: none;
    }
    QPushButton.nav_btn:hover { background-color: #EBF4FF; color: #0284C7; }
    QPushButton.nav_btn:pressed { background-color: #DBEAFE; }

    QPushButton.nav_btn_activo {
        background-color: #EBF4FF; color: #0284C7;
        font-size: 13px; font-weight: 700;
        text-align: left; padding: 11px 12px;
        border-radius: 8px; border-left: 3px solid #0284C7;
    }

    QPushButton.btn_accion {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0369A1, stop:1 #0EA5E9);
        color: white; border-radius: 8px; padding: 10px 16px;
        font-weight: 700; font-size: 13px; border: none;
    }
    QPushButton.btn_accion:hover {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0284C7, stop:1 #38BDF8);
    }

    QPushButton.btn_peligro {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #B91C1C, stop:1 #EF4444);
        color: white; border-radius: 8px; padding: 10px 16px;
        font-weight: 700; font-size: 13px; border: none;
    }
    QPushButton.btn_peligro:hover {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #DC2626, stop:1 #F87171);
    }

    QPushButton.btn_toggle {
        background-color: #EBF4FF; color: #1E2D3D;
        border-radius: 8px; padding: 8px 12px;
        font-size: 12px; font-weight: 600; border: 1px solid #DDE6EF;
        text-align: left;
    }
    QPushButton.btn_toggle:hover { background-color: #DBEAFE; color: #0369A1; }

    QTableWidget {
        background-color: #FFFFFF; color: #1E2D3D;
        font-size: 13px; font-family: 'Segoe UI', Arial;
        border-radius: 8px; border: 1px solid #DDE6EF;
        gridline-color: #EFF2F5;
        selection-background-color: #0EA5E9;
        selection-color: white;
        alternate-background-color: #F7FAFC;
    }
    QHeaderView::section {
        background-color: #EBF4FF; color: #0369A1;
        font-weight: 700; font-size: 12.5px;
        border: none; border-bottom: 2px solid #DDE6EF;
        padding: 9px 6px;
    }
    QTableWidget::item { padding: 6px 6px; border: none; }
    QTableWidget::item:selected { background-color: #0EA5E9; color: white; }

    QLineEdit, QSpinBox {
        background-color: #F0F4F8; color: #1E2D3D;
        border: 1.5px solid #DDE6EF;
        border-radius: 8px; padding: 9px 12px; font-size: 13px;
    }
    QLineEdit:focus, QSpinBox:focus { border: 1.5px solid #0284C7; }
    QLineEdit::placeholder { color: #94A3B8; }
    QSpinBox::up-button, QSpinBox::down-button { width: 18px; }

    QPushButton:disabled {
        background-color: #E2E8F0; color: #94A3B8; border: 1px solid #CBD5E1;
    }
    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
        background-color: #F8FAFC; color: #94A3B8; border: 1.5px solid #E2E8F0;
    }

    QProgressBar {
        border: none; background-color: #DDE6EF;
        border-radius: 7px; height: 14px;
        text-align: center; color: transparent;
    }
    QProgressBar#prog_hum::chunk {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #F59E0B, stop:1 #EF4444);
        border-radius: 7px;
    }
    QProgressBar#prog_adc::chunk {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #06B6D4, stop:1 #3B82F6);
        border-radius: 7px;
    }

    QScrollBar:vertical {
        background: #F0F4F8; width: 8px; border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background: #CBD5E1; border-radius: 4px; min-height: 30px;
    }
    QScrollBar::handle:vertical:hover { background: #0EA5E9; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

    QScrollBar:horizontal {
        background: #F0F4F8; height: 8px; border-radius: 4px;
    }
    QScrollBar::handle:horizontal {
        background: #CBD5E1; border-radius: 4px; min-width: 30px;
    }
    QScrollBar::handle:horizontal:hover { background: #0EA5E9; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""

_WIDGET_ESTILOS = {
    "oscuro": {
        "titulo":      "font-size: 21px; font-weight: 800; color: #E2EAF4; margin-bottom: 4px; background: transparent;",
        "subtitulo":   "color: #56A0C0; font-size: 13px; background: transparent;",
        "lbl_card":    "color: #7A90A8; font-weight: 600; font-size: 12px; letter-spacing: 0.5px; background: transparent;",
        "lbl_admin":   "color: #4A6280; font-size: 11px; font-weight: 600; padding: 8px;"
                       " background: #0B1120; border-radius: 8px;",
        "separador":   "background: #1E3048; max-height: 1px; margin: 6px 0;",
        "logo":        "font-size: 17px; font-weight: 900; color: #10B981; margin-left: 2px; background: transparent;",
        "lbl_sector":  "color: #7A90A8; font-weight: 700; background: transparent;",
        "lbl_hint":    "color: #4A6280; font-size: 11px; background: transparent;",
    },
    "claro": {
        "titulo":      "font-size: 21px; font-weight: 800; color: #1E2D3D; margin-bottom: 4px; background: transparent;",
        "subtitulo":   "color: #0369A1; font-size: 13px; background: transparent;",
        "lbl_card":    "color: #64748B; font-weight: 600; font-size: 12px; letter-spacing: 0.5px; background: transparent;",
        "lbl_admin":   "color: #64748B; font-size: 11px; font-weight: 600; padding: 8px;"
                       " background: #EBF4FF; border-radius: 8px;",
        "separador":   "background: #DDE6EF; max-height: 1px; margin: 6px 0;",
        "logo":        "font-size: 17px; font-weight: 900; color: #10B981; margin-left: 2px; background: transparent;",
        "lbl_sector":  "color: #1E2D3D; font-weight: 700; background: transparent;",
        "lbl_hint":    "color: #64748B; font-size: 11px; background: transparent;",
    }
}


# =============================================================================
# CLASE GRÁFICA
# =============================================================================

class LienzoGrafica(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.patch.set_facecolor('#0B1120')
        self.axes, self.axes2 = fig.subplots(2, 1)
        fig.subplots_adjust(hspace=0.48, left=0.08, right=0.98, top=0.92, bottom=0.14)
        for ax in [self.axes, self.axes2]:
            ax.set_facecolor('#162032')
            ax.tick_params(colors='#CBD5E1')
            for spine in ax.spines.values():
                spine.set_color('#1E3048')
        super().__init__(fig)

    def aplicar_tema(self, oscuro: bool):
        bg_fig  = '#0B1120' if oscuro else '#F0F4F8'
        bg_axes = '#162032' if oscuro else '#FFFFFF'
        tick_c  = '#CBD5E1' if oscuro else '#64748B'
        spine_c = '#1E3048' if oscuro else '#DDE6EF'
        self.axes.get_figure().patch.set_facecolor(bg_fig)
        for ax in [self.axes, self.axes2]:
            ax.set_facecolor(bg_axes)
            ax.tick_params(colors=tick_c)
            for spine in ax.spines.values():
                spine.set_color(spine_c)
        self.draw()


# =============================================================================
# MENÚ LATERAL ANIMADO
# =============================================================================

class MenuLateral(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ancho_expandido = 225
        self.ancho_colapsado = 58
        self.setMinimumWidth(self.ancho_colapsado)
        self.setMaximumWidth(self.ancho_colapsado)

    def enterEvent(self, event):
        """Se ejecuta cuando el mouse ENTRA a la barra"""
        self.animar_ancho(self.ancho_expandido)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Se ejecuta cuando el mouse SALE de la barra"""
        self.animar_ancho(self.ancho_colapsado)
        super().leaveEvent(event)

    def animar_ancho(self, ancho_final):
        """Lógica para la animación fluida"""
        self.anim_min = QPropertyAnimation(self, b"minimumWidth")
        self.anim_max = QPropertyAnimation(self, b"maximumWidth")
        for anim in [self.anim_min, self.anim_max]:
            anim.setDuration(220)
            anim.setStartValue(self.width())
            anim.setEndValue(ancho_final)
            anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            anim.start()


# =============================================================================
# VENTANA PRINCIPAL
# =============================================================================

class VistaRiego(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartVivero - Panel de Control")
        self.resize(1280, 780)
        self._modo_oscuro = True
        # Lista de (widget, css_oscuro, css_claro) para actualizaciones de tema
        self._reg_tema: list[tuple] = []

        self.setStyleSheet(CSS_OSCURO)

        widget_central = QWidget()
        widget_central.setObjectName("central_widget")
        self.layout_maestro = QHBoxLayout()
        self.layout_maestro.setContentsMargins(0, 0, 0, 0)
        self.layout_maestro.setSpacing(0)
        widget_central.setLayout(self.layout_maestro)
        self.setCentralWidget(widget_central)

        self._crear_sidebar()

        # Contenedor derecho (Barra Superior Global Fija + Paginador)
        contenedor_derecho = QWidget()
        layout_derecho = QVBoxLayout(contenedor_derecho)
        layout_derecho.setContentsMargins(0, 0, 0, 0)
        layout_derecho.setSpacing(0)

        self._crear_barra_superior(layout_derecho)

        self.paginador = QStackedWidget()
        self.paginador.setObjectName("paginador")
        layout_derecho.addWidget(self.paginador)

        self.layout_maestro.addWidget(contenedor_derecho)

        self._crear_pantalla_dashboard()
        self._crear_pantalla_graficas()
        self._crear_pantalla_parametros()
        self._crear_pantalla_usuarios()

    # -------------------------------------------------------------------------
    # Helpers de tema
    # -------------------------------------------------------------------------

    def _reg(self, widget, css_oscuro: str, css_claro: str):
        """Registra un widget para que cambie de estilo al alternar tema."""
        widget.setStyleSheet(css_oscuro)
        self._reg_tema.append((widget, css_oscuro, css_claro))
        return widget

    def toggle_tema(self):
        """Alterna entre modo oscuro y modo claro."""
        self._modo_oscuro = not self._modo_oscuro
        self.setStyleSheet(CSS_OSCURO if self._modo_oscuro else CSS_CLARO)
        self.canvas_grafica.aplicar_tema(self._modo_oscuro)
        for widget, css_o, css_c in self._reg_tema:
            widget.setStyleSheet(css_o if self._modo_oscuro else css_c)
        etiqueta = "☀️   Modo Claro" if self._modo_oscuro else "🌙   Modo Oscuro"
        self.btn_toggle_tema.setText(etiqueta)

    def _e(self, clave: str) -> tuple[str, str]:
        """Devuelve (css_oscuro, css_claro) para una clave de estilo."""
        return _WIDGET_ESTILOS["oscuro"][clave], _WIDGET_ESTILOS["claro"][clave]

    # -------------------------------------------------------------------------
    # Sidebar
    # -------------------------------------------------------------------------

    def _crear_sidebar(self):
        self.sidebar = MenuLateral()
        self.sidebar.setObjectName("sidebar")
        layout_side = QVBoxLayout(self.sidebar)
        layout_side.setContentsMargins(10, 22, 10, 18)
        layout_side.setSpacing(6)

        # Logo
        lbl_logo = QLabel("🌱 SmartVivero")
        self._reg(lbl_logo, *self._e("logo"))
        layout_side.addWidget(lbl_logo)
        layout_side.addSpacing(14)

        # Separador visual
        sep = QFrame()
        sep.setFixedHeight(1)
        self._reg(sep, *self._e("separador"))
        layout_side.addWidget(sep)
        layout_side.addSpacing(8)

        # Botones de navegación
        self.btn_nav_home     = QPushButton("🏠   Panel Principal")
        self.btn_nav_graph    = QPushButton("📈   Análisis Gráfico")
        self.btn_nav_settings = QPushButton("⚙️   Configuración")
        self.btn_nav_users    = QPushButton("👥   Personal & Roles")
        self.btn_nav_docs     = QPushButton("📄   Exportar PDF")

        for btn in [self.btn_nav_home, self.btn_nav_graph,
                    self.btn_nav_settings, self.btn_nav_users, self.btn_nav_docs]:
            btn.setProperty("class", "nav_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout_side.addWidget(btn)

        layout_side.addStretch()

        # Separador inferior
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        self._reg(sep2, *self._e("separador"))
        layout_side.addWidget(sep2)
        layout_side.addSpacing(8)

        # Botón toggle tema
        self.btn_toggle_tema = QPushButton("☀️   Modo Claro")
        self.btn_toggle_tema.setProperty("class", "btn_toggle")
        self.btn_toggle_tema.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_tema.clicked.connect(self.toggle_tema)
        layout_side.addWidget(self.btn_toggle_tema)
        layout_side.addSpacing(8)

        # Footer
        lbl_admin = QLabel("👨‍💻 Desarrollado por:\nGRUPO 3")
        self._reg(lbl_admin, *self._e("lbl_admin"))
        layout_side.addWidget(lbl_admin)

        self.layout_maestro.addWidget(self.sidebar)

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------

    def _crear_pantalla_dashboard(self):
        page_dash = QWidget()
        page_dash.setObjectName("page_dash")
        layout_principal = QVBoxLayout(page_dash)
        layout_principal.setContentsMargins(28, 28, 28, 28)
        layout_principal.setSpacing(18)

        # Título
        lbl_dash = QLabel("Panel de Control en Tiempo Real")
        self._reg(lbl_dash, *self._e("titulo"))
        layout_principal.addWidget(lbl_dash)

        # --- Tarjetas métricas ---
        layout_tarjetas = QHBoxLayout()
        layout_tarjetas.setSpacing(16)

        # Tarjeta Humedad
        frame_temp = QFrame()
        frame_temp.setObjectName("card")
        l_temp = QVBoxLayout(frame_temp)
        l_temp.setContentsMargins(20, 18, 20, 18)
        l_temp.setSpacing(8)
        lbl_t = QLabel("💧  HUMEDAD ACTUAL")
        self._reg(lbl_t, *self._e("lbl_card"))
        self.lbl_valor_temp = QLabel("-- %")
        self.lbl_valor_temp.setStyleSheet("font-size: 40px; font-weight: 800; color: #F59E0B;")
        self.progreso_temp = QProgressBar()
        self.progreso_temp.setObjectName("prog_hum")
        self.progreso_temp.setRange(0, 100)
        l_temp.addWidget(lbl_t)
        l_temp.addWidget(self.lbl_valor_temp)
        l_temp.addWidget(self.progreso_temp)

        # Tarjeta ADC
        frame_turb = QFrame()
        frame_turb.setObjectName("card")
        l_turb = QVBoxLayout(frame_turb)
        l_turb.setContentsMargins(20, 18, 20, 18)
        l_turb.setSpacing(8)
        lbl_tu = QLabel("🎛️  NIVEL ADC CRUDO")
        self._reg(lbl_tu, *self._e("lbl_card"))
        self.lbl_valor_turb = QLabel("--")
        self.lbl_valor_turb.setStyleSheet("font-size: 40px; font-weight: 800; color: #38BDF8;")
        self.progreso_turb = QProgressBar()
        self.progreso_turb.setObjectName("prog_adc")
        self.progreso_turb.setRange(0, 4095)
        l_turb.addWidget(lbl_tu)
        l_turb.addWidget(self.lbl_valor_turb)
        l_turb.addWidget(self.progreso_turb)

        # Tarjeta Control Manual
        frame_ctrl = QFrame()
        frame_ctrl.setObjectName("card")
        l_ctrl = QVBoxLayout(frame_ctrl)
        l_ctrl.setContentsMargins(20, 18, 20, 18)
        l_ctrl.setSpacing(8)
        lbl_ctrl = QLabel("\U0001f4a7  CONTROL MANUAL")
        self._reg(lbl_ctrl, *self._e("lbl_card"))

        self.btn_forzar_riego = QPushButton("\U0001f4a7  Forzar Riego")
        self.btn_forzar_riego.setStyleSheet(
            "background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #065F46,stop:1 #10B981);"
            "color: white; border-radius: 8px; padding: 10px 16px;"
            "font-weight: 800; font-size: 14px; border: none;"
        )
        self.btn_forzar_riego.setCursor(Qt.CursorShape.PointingHandCursor)

        lbl_dur = QLabel("Duración (seg):")
        self._reg(lbl_dur, *self._e("lbl_card"))
        self.spin_duracion_riego = QSpinBox()
        self.spin_duracion_riego.setRange(5, 600)
        self.spin_duracion_riego.setValue(30)
        self.spin_duracion_riego.setSuffix(" seg")
        self.spin_duracion_riego.setFixedWidth(110)

        self.lbl_estado_riego = QLabel("")
        self.lbl_estado_riego.setStyleSheet("font-size: 12px; font-weight: 700; background: transparent;")
        self.lbl_estado_riego.setWordWrap(True)

        l_ctrl.addWidget(lbl_ctrl)
        l_ctrl.addWidget(self.btn_forzar_riego)
        l_ctrl.addWidget(lbl_dur)
        l_ctrl.addWidget(self.spin_duracion_riego)
        l_ctrl.addWidget(self.lbl_estado_riego)
        l_ctrl.addStretch()

        layout_tarjetas.addWidget(frame_temp)
        layout_tarjetas.addWidget(frame_turb)
        layout_tarjetas.addWidget(frame_ctrl)
        layout_principal.addLayout(layout_tarjetas)

        # --- Tablas ---
        layout_tablas = QHBoxLayout()
        layout_tablas.setSpacing(16)

        # Panel Alertas
        frame_alertas = QFrame()
        frame_alertas.setObjectName("card")
        v_alertas = QVBoxLayout(frame_alertas)
        v_alertas.setContentsMargins(16, 14, 16, 14)
        v_alertas.setSpacing(10)

        lbl_alertas_titulo = QLabel("⚠️  ÚLTIMAS ALERTAS")
        lbl_alertas_titulo.setStyleSheet("font-weight: 700; font-size: 12px; color: #EF4444; letter-spacing: 0.5px;")
        v_alertas.addWidget(lbl_alertas_titulo)

        self.txt_buscar_alertas = QLineEdit()
        self.txt_buscar_alertas.setPlaceholderText("🔍  Buscar alertas...")
        v_alertas.addWidget(self.txt_buscar_alertas)

        self.tabla_alertas = QTableWidget(0, 6)
        self.tabla_alertas.setHorizontalHeaderLabels(["", "Fecha / Hora", "Tipo", "Sensor", "Valor", "Estado"])
        self.tabla_alertas.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tabla_alertas.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        header_alertas = self.tabla_alertas.horizontalHeader()
        header_alertas.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tabla_alertas.setColumnWidth(0, 36)
        header_alertas.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_alertas.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_alertas.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_alertas.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_alertas.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tabla_alertas.setAlternatingRowColors(True)
        self.tabla_alertas.verticalHeader().setVisible(False)
        self.tabla_alertas.setShowGrid(True)
        v_alertas.addWidget(self.tabla_alertas)

        # Barra inferior alertas: seleccionar todo + eliminar
        barra_alertas = QHBoxLayout()
        barra_alertas.setSpacing(8)

        self.btn_sel_todo_alertas = QPushButton("\u2611\ufe0f  Seleccionar Todo")
        self.btn_sel_todo_alertas.setProperty("class", "btn_toggle")
        self.btn_sel_todo_alertas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sel_todo_alertas.setCheckable(True)
        barra_alertas.addWidget(self.btn_sel_todo_alertas)

        self.btn_eliminar_alerta = QPushButton("\U0001f5d1\ufe0f  Eliminar Seleccionadas")
        self.btn_eliminar_alerta.setProperty("class", "btn_peligro")
        self.btn_eliminar_alerta.setCursor(Qt.CursorShape.PointingHandCursor)
        barra_alertas.addWidget(self.btn_eliminar_alerta)

        v_alertas.addLayout(barra_alertas)

        # Panel Historial
        frame_historial = QFrame()
        frame_historial.setObjectName("card")
        v_historial = QVBoxLayout(frame_historial)
        v_historial.setContentsMargins(16, 14, 16, 14)
        v_historial.setSpacing(10)

        lbl_hist_titulo = QLabel("🗄️  HISTORIAL COMPLETO")
        lbl_hist_titulo.setStyleSheet("font-weight: 700; font-size: 12px; color: #10B981; letter-spacing: 0.5px;")
        v_historial.addWidget(lbl_hist_titulo)

        self.txt_buscar_historial = QLineEdit()
        self.txt_buscar_historial.setPlaceholderText("🔍  Buscar en el historial...")
        v_historial.addWidget(self.txt_buscar_historial)

        self.tabla_historial = QTableWidget(0, 7)
        self.tabla_historial.setHorizontalHeaderLabels(
            ["", "ID", "Fecha / Hora", "Ubicación", "Humedad (%)", "Valor ADC", "Sensor"])
        self.tabla_historial.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tabla_historial.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        header_historial = self.tabla_historial.horizontalHeader()
        header_historial.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tabla_historial.setColumnWidth(0, 36)
        header_historial.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_historial.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_historial.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_historial.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_historial.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header_historial.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.tabla_historial.setAlternatingRowColors(True)
        self.tabla_historial.verticalHeader().setVisible(False)
        self.tabla_historial.setShowGrid(True)
        v_historial.addWidget(self.tabla_historial)

        # Barra inferior historial: seleccionar todo + eliminar
        barra_historial = QHBoxLayout()
        barra_historial.setSpacing(8)

        self.btn_sel_todo_historial = QPushButton("\u2611\ufe0f  Seleccionar Todo")
        self.btn_sel_todo_historial.setProperty("class", "btn_toggle")
        self.btn_sel_todo_historial.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sel_todo_historial.setCheckable(True)
        barra_historial.addWidget(self.btn_sel_todo_historial)

        self.btn_eliminar_medicion = QPushButton("\U0001f5d1\ufe0f  Eliminar Seleccionadas")
        self.btn_eliminar_medicion.setProperty("class", "btn_peligro")
        self.btn_eliminar_medicion.setCursor(Qt.CursorShape.PointingHandCursor)
        barra_historial.addWidget(self.btn_eliminar_medicion)

        v_historial.addLayout(barra_historial)

        layout_tablas.addWidget(frame_alertas, 1)
        layout_tablas.addWidget(frame_historial, 1)
        layout_principal.addLayout(layout_tablas)
        self.paginador.addWidget(page_dash)

    # -------------------------------------------------------------------------
    # Pantalla Gráficas
    # -------------------------------------------------------------------------

    def _crear_pantalla_graficas(self):
        self.page_graficas = QWidget()
        self.page_graficas.setObjectName("page_graficas")
        layout = QVBoxLayout(self.page_graficas)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        lbl_titulo = QLabel("📊  Análisis Gráfico de Sensores")
        self._reg(lbl_titulo, *self._e("titulo"))
        layout.addWidget(lbl_titulo)

        frame_grafica = QFrame()
        frame_grafica.setObjectName("card")
        v_grafica = QVBoxLayout(frame_grafica)
        v_grafica.setContentsMargins(12, 12, 12, 12)
        self.canvas_grafica = LienzoGrafica(self, width=8, height=6, dpi=100)
        v_grafica.addWidget(self.canvas_grafica)
        layout.addWidget(frame_grafica)

        self.paginador.addWidget(self.page_graficas)

    # -------------------------------------------------------------------------
    # Pantalla Configuración
    # -------------------------------------------------------------------------

    def _crear_pantalla_parametros(self):
        self.page_parametros = QWidget()
        self.page_parametros.setObjectName("page_parametros")
        layout = QVBoxLayout(self.page_parametros)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        lbl_titulo = QLabel("⚙️  Panel de Configuración — Umbrales de Riego")
        self._reg(lbl_titulo, *self._e("titulo"))
        layout.addWidget(lbl_titulo)

        lbl_sub = QLabel("Configura los umbrales de humedad que controlan el riego automático del ESP32.")
        self._reg(lbl_sub, *self._e("subtitulo"))
        layout.addWidget(lbl_sub)

        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(36, 32, 36, 32)
        form_layout.setSpacing(20)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Sector
        lbl_sector = QLabel("Sector (ID):")
        self._reg(lbl_sector, *self._e("lbl_sector"))
        self.spin_sector = QSpinBox()
        self.spin_sector.setRange(1, 10)
        self.spin_sector.setValue(1)
        self.spin_sector.setFixedWidth(120)
        self.btn_cargar_umbral = QPushButton("🔄  Cargar valores actuales")
        self.btn_cargar_umbral.setProperty("class", "btn_accion")
        self.btn_cargar_umbral.setFixedWidth(210)
        self.btn_cargar_umbral.setCursor(Qt.CursorShape.PointingHandCursor)
        sector_row = QHBoxLayout()
        sector_row.addWidget(self.spin_sector)
        sector_row.addWidget(self.btn_cargar_umbral)
        sector_row.addStretch()
        form_layout.addRow(lbl_sector, sector_row)

        # Humedad mín
        lbl_min = QLabel("Humedad Mín. ON (%):")
        lbl_min.setStyleSheet("color: #F59E0B; font-weight: 700; background: transparent;")
        self.input_hum_min = QSpinBox()
        self.input_hum_min.setRange(0, 100)
        self.input_hum_min.setValue(30)
        self.input_hum_min.setFixedWidth(120)
        self.input_hum_min.setSuffix(" %")
        lbl_hint_min = QLabel("  ← Por debajo de este valor, el riego se ENCIENDE")
        self._reg(lbl_hint_min, *self._e("lbl_hint"))
        row_min = QHBoxLayout()
        row_min.addWidget(self.input_hum_min)
        row_min.addWidget(lbl_hint_min)
        row_min.addStretch()
        form_layout.addRow(lbl_min, row_min)

        # Humedad máx
        lbl_max = QLabel("Humedad Máx. OFF (%):")
        lbl_max.setStyleSheet("color: #10B981; font-weight: 700; background: transparent;")
        self.input_hum_max = QSpinBox()
        self.input_hum_max.setRange(0, 100)
        self.input_hum_max.setValue(70)
        self.input_hum_max.setFixedWidth(120)
        self.input_hum_max.setSuffix(" %")
        lbl_hint_max = QLabel("  ← Por encima de este valor, el riego se APAGA")
        self._reg(lbl_hint_max, *self._e("lbl_hint"))
        row_max = QHBoxLayout()
        row_max.addWidget(self.input_hum_max)
        row_max.addWidget(lbl_hint_max)
        row_max.addStretch()
        form_layout.addRow(lbl_max, row_max)

        # Tiempo máx
        lbl_tiempo = QLabel("Tiempo Máx. Riego (seg):")
        lbl_tiempo.setStyleSheet("color: #38BDF8; font-weight: 700; background: transparent;")
        self.input_tiempo_max = QSpinBox()
        self.input_tiempo_max.setRange(10, 3600)
        self.input_tiempo_max.setValue(180)
        self.input_tiempo_max.setFixedWidth(120)
        self.input_tiempo_max.setSuffix(" seg")
        lbl_hint_tiempo = QLabel("  ← Tiempo máximo continuo antes de forzar apagado")
        self._reg(lbl_hint_tiempo, *self._e("lbl_hint"))
        row_tiempo = QHBoxLayout()
        row_tiempo.addWidget(self.input_tiempo_max)
        row_tiempo.addWidget(lbl_hint_tiempo)
        row_tiempo.addStretch()
        form_layout.addRow(lbl_tiempo, row_tiempo)

        # Guardar
        self.btn_guardar_params = QPushButton("💾  Guardar en la API")
        self.btn_guardar_params.setProperty("class", "btn_accion")
        self.btn_guardar_params.setFixedWidth(190)
        self.btn_guardar_params.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_estado_params = QLabel("")
        self.lbl_estado_params.setStyleSheet("font-size: 13px; font-weight: 700;")
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_guardar_params)
        btn_row.addWidget(self.lbl_estado_params)
        btn_row.addStretch()
        form_layout.addRow("", btn_row)

        layout.addWidget(form_frame)
        layout.addStretch()
        self.paginador.addWidget(self.page_parametros)

    # -------------------------------------------------------------------------
    # Barra Superior Global Permanente
    # -------------------------------------------------------------------------

    def _crear_barra_superior(self, layout_padre):
        self.frame_top_bar = QFrame()
        self.frame_top_bar.setObjectName("top_bar")
        self.frame_top_bar.setFixedHeight(68)

        layout_top = QHBoxLayout(self.frame_top_bar)
        layout_top.setContentsMargins(24, 8, 24, 8)
        layout_top.setSpacing(14)

        # 1. Selector de Sector
        lbl_sec = QLabel("📍 Sector:")
        lbl_sec.setStyleSheet("font-weight: 800; font-size: 13px;")
        self._reg(lbl_sec, "color: #E2EAF4; font-weight: 800; font-size: 13px;", "color: #1E2D3D; font-weight: 800; font-size: 13px;")

        self.combo_sector = QComboBox()
        self.combo_sector.setFixedWidth(240)
        self.combo_sector.setCursor(Qt.CursorShape.PointingHandCursor)

        # 2. Información del Miembro Encargado
        v_encargado = QVBoxLayout()
        v_encargado.setSpacing(2)
        self.lbl_top_encargado = QLabel("👨‍🌾 Encargado: Diego Charry (Administrador General)")
        self.lbl_top_encargado.setStyleSheet("font-weight: 700; font-size: 13px; color: #56CFE1;")
        self.lbl_top_correo = QLabel("📧 diego.charry@vivero.com  |  🌱 Cultivo: Orquídeas y Suculentas")
        self.lbl_top_correo.setStyleSheet("font-size: 11.5px; color: #7A90A8;")
        v_encargado.addWidget(self.lbl_top_encargado)
        v_encargado.addWidget(self.lbl_top_correo)

        # 3. Selector de Estado de Presencia y Botón Interactivo de Sesión
        self.combo_estado_usuario = QComboBox()
        self.combo_estado_usuario.setFixedWidth(145)
        self.combo_estado_usuario.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_estado_usuario.addItem("🟢  En Línea", "EN_LINEA")
        self.combo_estado_usuario.addItem("🟡  Ausente", "AUSENTE")
        self.combo_estado_usuario.addItem("🔴  En Campo", "EN_CAMPO")
        self.actualizar_estilo_estado("EN_LINEA")

        self.btn_badge_sesion = QPushButton("👤  Diego Charry (ADMINISTRADOR)  ▾")
        self.btn_badge_sesion.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_badge_sesion.setToolTip("Haz clic para cambiar de cuenta o iniciar sesión")
        self.btn_badge_sesion.setStyleSheet(
            "QPushButton {"
            "   background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3048, stop:1 #243450);"
            "   color: #38BDF8; font-size: 11.5px; font-weight: 700;"
            "   padding: 6px 14px; border-radius: 12px; border: 1px solid #0284C7;"
            "}"
            "QPushButton:hover {"
            "   background: #0284C7; color: white; border: 1px solid #38BDF8;"
            "}"
        )

        layout_top.addWidget(lbl_sec)
        layout_top.addWidget(self.combo_sector)
        layout_top.addSpacing(10)
        layout_top.addLayout(v_encargado)
        layout_top.addStretch()
        layout_top.addWidget(self.combo_estado_usuario)
        layout_top.addWidget(self.btn_badge_sesion)

        layout_padre.addWidget(self.frame_top_bar)

    def actualizar_estilo_estado(self, estado: str = "EN_LINEA"):
        """Actualiza los colores y el estilo del selector de presencia según el estado."""
        estilos = {
            "EN_LINEA": (
                "QComboBox {"
                "   background: #064E3B; color: #34D399; font-size: 11.5px; font-weight: 700;"
                "   padding: 5px 10px; border-radius: 12px; border: 1px solid #059669;"
                "}"
                "QComboBox QAbstractItemView {"
                "   background-color: #141E2E; color: #E2EAF4; selection-background-color: #064E3B;"
                "}"
            ),
            "AUSENTE": (
                "QComboBox {"
                "   background: #451A03; color: #FBBF24; font-size: 11.5px; font-weight: 700;"
                "   padding: 5px 10px; border-radius: 12px; border: 1px solid #D97706;"
                "}"
                "QComboBox QAbstractItemView {"
                "   background-color: #141E2E; color: #E2EAF4; selection-background-color: #451A03;"
                "}"
            ),
            "EN_CAMPO": (
                "QComboBox {"
                "   background: #450A0A; color: #F87171; font-size: 11.5px; font-weight: 700;"
                "   padding: 5px 10px; border-radius: 12px; border: 1px solid #DC2626;"
                "}"
                "QComboBox QAbstractItemView {"
                "   background-color: #141E2E; color: #E2EAF4; selection-background-color: #450A0A;"
                "}"
            ),
        }
        self.combo_estado_usuario.setStyleSheet(estilos.get(estado, estilos["EN_LINEA"]))

    # -------------------------------------------------------------------------
    # Pantalla Gestión de Personal y Roles
    # -------------------------------------------------------------------------

    def _crear_pantalla_usuarios(self):
        self.page_usuarios = QWidget()
        self.page_usuarios.setObjectName("page_usuarios")
        layout = QVBoxLayout(self.page_usuarios)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        lbl_titulo = QLabel("👥  Gestión de Personal y Control de Roles")
        self._reg(lbl_titulo, *self._e("titulo"))
        layout.addWidget(lbl_titulo)

        lbl_sub = QLabel("Registra al equipo agrónomo, asigna roles de acceso y audita permisos en el sistema.")
        self._reg(lbl_sub, *self._e("subtitulo"))
        layout.addWidget(lbl_sub)

        # Formulario registro
        form_frame = QFrame()
        form_frame.setObjectName("card")
        f_layout = QVBoxLayout(form_frame)
        f_layout.setContentsMargins(20, 18, 20, 18)
        f_layout.setSpacing(12)

        self.lbl_form_usuario_titulo = QLabel("➕  Registrar Nuevo Miembro del Equipo")
        self.lbl_form_usuario_titulo.setStyleSheet("font-weight: 700; font-size: 13px; color: #38BDF8;")
        f_layout.addWidget(self.lbl_form_usuario_titulo)

        h_inputs = QHBoxLayout()
        h_inputs.setSpacing(12)

        self.txt_user_nombre = QLineEdit()
        self.txt_user_nombre.setPlaceholderText("Nombre completo (ej. Diego Charry)")

        self.txt_user_correo = QLineEdit()
        self.txt_user_correo.setPlaceholderText("Correo electrónico")

        self.txt_user_pass = QLineEdit()
        self.txt_user_pass.setPlaceholderText("Contraseña (Opcional al editar)")
        self.txt_user_pass.setEchoMode(QLineEdit.EchoMode.Password)

        self.combo_user_rol = QComboBox()
        self.combo_user_rol.addItems(["ADMINISTRADOR", "OPERADOR", "AGRONOMO", "VISUALIZADOR", "TECNICO_IOT"])
        self.combo_user_rol.setFixedWidth(160)

        self.btn_guardar_usuario = QPushButton("💾  Registrar")
        self.btn_guardar_usuario.setProperty("class", "btn_accion")
        self.btn_guardar_usuario.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guardar_usuario.setFixedWidth(160)

        self.btn_cancelar_edicion = QPushButton("❌ Cancelar")
        self.btn_cancelar_edicion.setProperty("class", "btn_toggle")
        self.btn_cancelar_edicion.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancelar_edicion.setFixedWidth(110)
        self.btn_cancelar_edicion.setVisible(False)

        h_inputs.addWidget(self.txt_user_nombre, 2)
        h_inputs.addWidget(self.txt_user_correo, 2)
        h_inputs.addWidget(self.txt_user_pass, 2)
        h_inputs.addWidget(self.combo_user_rol, 1)
        h_inputs.addWidget(self.btn_guardar_usuario)
        h_inputs.addWidget(self.btn_cancelar_edicion)
        f_layout.addLayout(h_inputs)

        self.lbl_estado_usuarios = QLabel("")
        self.lbl_estado_usuarios.setStyleSheet("font-size: 12px; font-weight: 700;")
        f_layout.addWidget(self.lbl_estado_usuarios)
        layout.addWidget(form_frame)

        # Tabla de usuarios
        frame_tabla = QFrame()
        frame_tabla.setObjectName("card")
        v_tab = QVBoxLayout(frame_tabla)
        v_tab.setContentsMargins(16, 14, 16, 14)
        v_tab.setSpacing(10)

        lbl_tab_title = QLabel("📋  Personal Registrado en el Sistema")
        lbl_tab_title.setStyleSheet("font-weight: 700; font-size: 12px; color: #10B981; letter-spacing: 0.5px;")
        v_tab.addWidget(lbl_tab_title)

        self.tabla_usuarios = QTableWidget(0, 7)
        self.tabla_usuarios.setHorizontalHeaderLabels(["", "ID", "Nombre", "Correo", "Rol", "Estado", "Fecha Registro"])
        self.tabla_usuarios.setColumnWidth(0, 42)
        self.tabla_usuarios.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tabla_usuarios.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tabla_usuarios.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tabla_usuarios.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header_u = self.tabla_usuarios.horizontalHeader()
        header_u.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header_u.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_u.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_u.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header_u.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_u.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header_u.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_usuarios.setAlternatingRowColors(True)
        self.tabla_usuarios.verticalHeader().setVisible(False)
        self.tabla_usuarios.setShowGrid(True)
        v_tab.addWidget(self.tabla_usuarios)

        # Botones de Acción sobre la Tabla
        h_btn_tab = QHBoxLayout()
        self.btn_sel_todo_usuarios = QPushButton("☑️  Seleccionar Todo")
        self.btn_sel_todo_usuarios.setCheckable(True)
        self.btn_sel_todo_usuarios.setProperty("class", "btn_toggle")
        self.btn_sel_todo_usuarios.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sel_todo_usuarios.setFixedWidth(170)

        self.btn_editar_usuario = QPushButton("✏️  Editar Seleccionado")
        self.btn_editar_usuario.setProperty("class", "btn_accion")
        self.btn_editar_usuario.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_editar_usuario.setFixedWidth(180)

        self.btn_eliminar_usuario = QPushButton("🗑️  Eliminar Seleccionado")
        self.btn_eliminar_usuario.setProperty("class", "btn_peligro")
        self.btn_eliminar_usuario.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eliminar_usuario.setFixedWidth(190)

        self.btn_refrescar_usuarios = QPushButton("🔄  Refrescar Lista")
        self.btn_refrescar_usuarios.setProperty("class", "btn_toggle")
        self.btn_refrescar_usuarios.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refrescar_usuarios.setFixedWidth(150)

        h_btn_tab.addWidget(self.btn_sel_todo_usuarios)
        h_btn_tab.addWidget(self.btn_editar_usuario)
        h_btn_tab.addWidget(self.btn_eliminar_usuario)
        h_btn_tab.addWidget(self.btn_refrescar_usuarios)
        h_btn_tab.addStretch()
        v_tab.addLayout(h_btn_tab)

        layout.addWidget(frame_tabla)
        self.paginador.addWidget(self.page_usuarios)


# =============================================================================
# DIÁLOGO CAMBIAR DE CUENTA / INICIAR SESIÓN
# =============================================================================

class DialogoCambiarCuenta(QDialog):
    def __init__(self, parent=None, usuarios=None, modo_oscuro=True):
        super().__init__(parent)
        self.setWindowTitle("🔐 Cambiar de Cuenta - SmartVivero")
        self.setFixedSize(430, 390)
        self.usuario_seleccionado = None

        bg_color = "#141E2E" if modo_oscuro else "#FFFFFF"
        text_color = "#E2EAF4" if modo_oscuro else "#1E2D3D"
        card_bg = "#0B1120" if modo_oscuro else "#F0F4F8"
        border_color = "#1E3048" if modo_oscuro else "#DDE6EF"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_color}; }}
            QLabel {{ color: {text_color}; font-size: 13px; font-family: 'Segoe UI', Arial; }}
            QLineEdit, QComboBox {{
                background-color: {card_bg}; color: {text_color};
                border: 1.5px solid {border_color}; border-radius: 8px;
                padding: 9px 12px; font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus {{ border: 1.5px solid #0EA5E9; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)

        lbl_titulo = QLabel("👤  Cambiar de Usuario Activo")
        lbl_titulo.setStyleSheet("font-size: 17px; font-weight: 800; color: #38BDF8;")
        layout.addWidget(lbl_titulo)

        lbl_sub = QLabel("Selecciona un perfil registrado o introduce tus credenciales:")
        lbl_sub.setStyleSheet("font-size: 12px; color: #7A90A8;")
        lbl_sub.setWordWrap(True)
        layout.addWidget(lbl_sub)

        # 1. Selector rápido de usuarios
        lbl_sel = QLabel("Seleccionar perfil registrado:")
        lbl_sel.setStyleSheet("font-weight: 700; font-size: 12px; margin-top: 4px;")
        self.combo_perfiles = QComboBox()
        if usuarios:
            for u in usuarios:
                self.combo_perfiles.addItem(f"👤 {u['nombre']} — [{u.get('rol', 'OPERADOR')}]", u)

        layout.addWidget(lbl_sel)
        layout.addWidget(self.combo_perfiles)

        # Separador visual
        lbl_o = QLabel("── O ingresa con correo ──")
        lbl_o.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_o.setStyleSheet("color: #4A6280; font-size: 11px; font-weight: 600; margin: 4px 0;")
        layout.addWidget(lbl_o)

        self.txt_correo = QLineEdit()
        self.txt_correo.setPlaceholderText("Correo electrónico")

        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("Contraseña (opcional para cambio rápido)")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)

        # Al cambiar selector, actualizar el correo
        self.combo_perfiles.currentIndexChanged.connect(self._al_cambiar_perfil)
        if usuarios and len(usuarios) > 0:
            self.txt_correo.setText(usuarios[0].get("correo", ""))

        layout.addWidget(self.txt_correo)
        layout.addWidget(self.txt_pass)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.lbl_error)

        # Botones de Acción
        h_btn = QHBoxLayout()
        h_btn.setSpacing(10)

        self.btn_login = QPushButton("🔓  Cambiar Cuenta")
        self.btn_login.setStyleSheet(
            "background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369A1, stop:1 #0EA5E9);"
            "color: white; border-radius: 8px; padding: 10px 18px; font-weight: 800; font-size: 13px; border: none;"
        )
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setStyleSheet(
            "background-color: #1E3048; color: #CBD5E1; border-radius: 8px; padding: 10px 16px; font-weight: 600; font-size: 13px; border: none;"
        )
        self.btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self.reject)

        h_btn.addWidget(self.btn_login)
        h_btn.addWidget(self.btn_cancelar)
        layout.addLayout(h_btn)

    def _al_cambiar_perfil(self, idx):
        data = self.combo_perfiles.currentData()
        if data:
            self.txt_correo.setText(data.get("correo", ""))
            self.txt_pass.clear()
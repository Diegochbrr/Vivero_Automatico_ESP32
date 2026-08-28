import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTableWidget, QHeaderView, QFrame,
                             QProgressBar, QLineEdit, QStackedWidget, QFormLayout, QSpinBox)
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
        background-color: #FFFFFF; color: #1E2D3D;
        border: 1.5px solid #DDE6EF;
        border-radius: 8px; padding: 9px 12px; font-size: 13px;
    }
    QLineEdit:focus, QSpinBox:focus { border: 1.5px solid #0EA5E9; }
    QLineEdit::placeholder { color: #94A3B8; }
    QSpinBox::up-button, QSpinBox::down-button { width: 18px; }

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

        self.paginador = QStackedWidget()
        self.paginador.setObjectName("paginador")
        self.layout_maestro.addWidget(self.paginador)

        self._crear_pantalla_dashboard()
        self._crear_pantalla_graficas()
        self._crear_pantalla_parametros()

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
        self.btn_nav_docs     = QPushButton("📄   Exportar PDF")

        for btn in [self.btn_nav_home, self.btn_nav_graph,
                    self.btn_nav_settings, self.btn_nav_docs]:
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
        lbl_admin = QLabel("👨‍💻 Desarrollado por:\nIntegrantes Grupo 3")
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

        layout_tarjetas.addWidget(frame_temp)
        layout_tarjetas.addWidget(frame_turb)
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

        self.tabla_alertas = QTableWidget(0, 5)
        self.tabla_alertas.setHorizontalHeaderLabels(["Fecha / Hora", "Tipo", "Sensor", "Valor", "Estado"])
        self.tabla_alertas.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tabla_alertas.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        header_alertas = self.tabla_alertas.horizontalHeader()
        header_alertas.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_alertas.setStretchLastSection(True)
        self.tabla_alertas.setAlternatingRowColors(True)
        self.tabla_alertas.verticalHeader().setVisible(False)
        self.tabla_alertas.setShowGrid(True)
        v_alertas.addWidget(self.tabla_alertas)

        self.btn_eliminar_alerta = QPushButton("🗑️  Eliminar Seleccionada")
        self.btn_eliminar_alerta.setProperty("class", "btn_peligro")
        self.btn_eliminar_alerta.setCursor(Qt.CursorShape.PointingHandCursor)
        v_alertas.addWidget(self.btn_eliminar_alerta)

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

        self.tabla_historial = QTableWidget(0, 6)
        self.tabla_historial.setHorizontalHeaderLabels(
            ["ID", "Fecha / Hora", "Ubicación", "Humedad (%)", "Valor ADC", "Sensor"])
        self.tabla_historial.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tabla_historial.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        header_historial = self.tabla_historial.horizontalHeader()
        header_historial.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_historial.setStretchLastSection(True)
        self.tabla_historial.setAlternatingRowColors(True)
        self.tabla_historial.verticalHeader().setVisible(False)
        self.tabla_historial.setShowGrid(True)
        v_historial.addWidget(self.tabla_historial)

        self.btn_eliminar_medicion = QPushButton("🗑️  Eliminar Seleccionada")
        self.btn_eliminar_medicion.setProperty("class", "btn_peligro")
        self.btn_eliminar_medicion.setCursor(Qt.CursorShape.PointingHandCursor)
        v_historial.addWidget(self.btn_eliminar_medicion)

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
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTableWidget, QHeaderView, QFrame, 
                             QProgressBar, QLineEdit, QStackedWidget, QFormLayout, QSpinBox)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

# --- Clase para la Gráfica ---
class LienzoGrafica(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.patch.set_facecolor('#0F172A')
        self.axes = fig.add_subplot(111)
        self.axes.set_facecolor('#1E293B')
        self.axes.tick_params(colors='#CBD5E1')
        for spine in self.axes.spines.values():
            spine.set_color('#334155')
        super().__init__(fig)

# --- NUEVA CLASE: Menú Lateral Animado ---
class MenuLateral(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ancho_expandido = 220  # Ancho cuando está abierto
        self.ancho_colapsado = 55   # Ancho cuando está escondido (solo íconos)
        
        # Empezamos con el menú colapsado por defecto
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
        # Animamos el mínimo y máximo al mismo tiempo para empujar el layout
        self.anim_min = QPropertyAnimation(self, b"minimumWidth")
        self.anim_max = QPropertyAnimation(self, b"maximumWidth")
        
        for anim in [self.anim_min, self.anim_max]:
            anim.setDuration(250) # Milisegundos que dura la animación
            anim.setStartValue(self.width())
            anim.setEndValue(ancho_final)
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad) # Suavizado
            anim.start()


class VistaRiego(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartVivero - Panel de Control")
        self.resize(1200, 750)
        
        self.setStyleSheet("""
            QMainWindow { background-color: #0F172A; }
            QLabel { color: #F8FAFC; font-family: 'Segoe UI', Arial; }
            
            QFrame#sidebar { background-color: #1E293B; border-right: 1px solid #334155; }
            QFrame#card { background-color: #1E293B; border-radius: 12px; border: 1px solid #334155; }
            
            QPushButton.nav_btn { 
                background-color: transparent; color: #94A3B8; font-size: 14px; font-weight: bold;
                text-align: left; padding: 12px 10px; border-radius: 8px; border: none;
            }
            QPushButton.nav_btn:hover { background-color: #334155; color: #38BDF8; }
            
            QPushButton.btn_accion { 
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0EA5E9); 
                color: white; border-radius: 6px; padding: 10px; font-weight: bold; font-size: 13px;
            }
            QPushButton.btn_accion:hover { background-color: #0369A1; }
            
            QTableWidget { 
                background-color: #1E293B; color: #F8FAFC; border-radius: 8px; 
                border: 1px solid #334155; gridline-color: #334155; selection-background-color: #38BDF8;
            }
            QHeaderView::section { background-color: #0F172A; color: #38BDF8; font-weight: bold; border: none; padding: 8px; }
            
            QLineEdit, QSpinBox { 
                background-color: #0F172A; color: white; border: 1px solid #334155; 
                border-radius: 6px; padding: 8px; font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #38BDF8; }
            
            QProgressBar { border: none; background-color: #334155; border-radius: 6px; text-align: center; color: transparent; height: 12px;}
            QProgressBar#prog_hum::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F59E0B, stop:1 #EF4444); border-radius: 6px; }
            QProgressBar#prog_adc::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06B6D4, stop:1 #3B82F6); border-radius: 6px; }
        """)
        
        widget_central = QWidget()
        self.layout_maestro = QHBoxLayout() 
        self.layout_maestro.setContentsMargins(0, 0, 0, 0)
        self.layout_maestro.setSpacing(0)
        widget_central.setLayout(self.layout_maestro)
        self.setCentralWidget(widget_central)
        
        self._crear_sidebar()
        
        self.paginador = QStackedWidget()
        self.layout_maestro.addWidget(self.paginador)
        
        self._crear_pantalla_dashboard()
        self._crear_pantalla_graficas()
        self._crear_pantalla_parametros()

    def _crear_sidebar(self):
        # Usamos nuestra nueva clase con animación
        self.sidebar = MenuLateral()
        self.sidebar.setObjectName("sidebar")
        layout_side = QVBoxLayout(self.sidebar)
        layout_side.setContentsMargins(10, 20, 10, 20)
        layout_side.setSpacing(10)
        
        lbl_logo = QLabel("🌱 SmartVivero")
        lbl_logo.setStyleSheet("font-size: 18px; font-weight: 900; color: #10B981; margin-bottom: 20px; margin-left: 5px;")
        layout_side.addWidget(lbl_logo)
        
        # Opciones del menú (espacios para asegurar que el icono quede visible al colapsar)
        self.btn_nav_home = QPushButton("🏠    Panel Principal")
        self.btn_nav_graph = QPushButton("📈    Análisis Gráfico")
        self.btn_nav_settings = QPushButton("⚙️    Configuración")
        self.btn_nav_docs = QPushButton("📄    Exportar PDF")
        
        for btn in [self.btn_nav_home, self.btn_nav_graph, self.btn_nav_settings, self.btn_nav_docs]:
            btn.setProperty("class", "nav_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout_side.addWidget(btn)
            
        layout_side.addStretch()
        
        lbl_admin = QLabel("👨‍💻 Desarrollado por:\nIntegrantes Grupo 3")
        lbl_admin.setStyleSheet("color: #64748B; font-size: 11px; font-weight: bold; padding: 8px; background: #0F172A; border-radius: 8px;")
        layout_side.addWidget(lbl_admin)
        
        self.layout_maestro.addWidget(self.sidebar)

    def _crear_pantalla_dashboard(self):
        page_dash = QWidget()
        layout_principal = QVBoxLayout(page_dash)
        layout_principal.setContentsMargins(25, 25, 25, 25)
        
        lbl_dash = QLabel("Bienvenido al Panel de Control en Tiempo Real")
        lbl_dash.setStyleSheet("font-size: 20px; font-weight: bold; color: #F8FAFC; margin-bottom: 10px;")
        layout_principal.addWidget(lbl_dash)
        
        layout_tarjetas = QHBoxLayout()
        
        frame_temp = QFrame()
        frame_temp.setObjectName("card")
        l_temp = QVBoxLayout(frame_temp)
        self.lbl_valor_temp = QLabel("-- %")
        self.lbl_valor_temp.setStyleSheet("font-size: 36px; font-weight: bold; color: #F59E0B;")
        self.progreso_temp = QProgressBar()
        self.progreso_temp.setObjectName("prog_hum")
        self.progreso_temp.setRange(0, 100)
        lbl_t = QLabel("💧 Humedad Actual")
        lbl_t.setStyleSheet("color: #94A3B8; font-weight: bold;")
        l_temp.addWidget(lbl_t)
        l_temp.addWidget(self.lbl_valor_temp)
        l_temp.addWidget(self.progreso_temp)
        
        frame_turb = QFrame()
        frame_turb.setObjectName("card")
        l_turb = QVBoxLayout(frame_turb)
        self.lbl_valor_turb = QLabel("--")
        self.lbl_valor_turb.setStyleSheet("font-size: 36px; font-weight: bold; color: #38BDF8;")
        self.progreso_turb = QProgressBar()
        self.progreso_turb.setObjectName("prog_adc")
        self.progreso_turb.setRange(0, 4095)
        lbl_tu = QLabel("🎛️ Nivel ADC Crudo")
        lbl_tu.setStyleSheet("color: #94A3B8; font-weight: bold;")
        l_turb.addWidget(lbl_tu)
        l_turb.addWidget(self.lbl_valor_turb)
        l_turb.addWidget(self.progreso_turb)
        
        layout_tarjetas.addWidget(frame_temp)
        layout_tarjetas.addWidget(frame_turb)
        layout_principal.addLayout(layout_tarjetas)
        
        layout_tablas = QHBoxLayout()
        layout_tablas.setContentsMargins(0, 20, 0, 0)
        
        panel_alertas = QVBoxLayout()
        panel_alertas.addWidget(QLabel("⚠️ Últimas Alertas Registradas", styleSheet="font-weight: bold; color: #EF4444;"))
        self.txt_buscar_alertas = QLineEdit()
        self.txt_buscar_alertas.setPlaceholderText("Buscar en alertas...")
        panel_alertas.addWidget(self.txt_buscar_alertas)
        self.tabla_alertas = QTableWidget(0, 5)
        self.tabla_alertas.setHorizontalHeaderLabels(["Hora", "Tipo", "Sensor", "Valor", "Estado"])
        self.tabla_alertas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        panel_alertas.addWidget(self.tabla_alertas)
        
        panel_historial = QVBoxLayout()
        panel_historial.addWidget(QLabel("🗄️ Historial Completo", styleSheet="font-weight: bold; color: #10B981;"))
        self.txt_buscar_historial = QLineEdit()
        self.txt_buscar_historial.setPlaceholderText("Buscar en el historial de datos...")
        panel_historial.addWidget(self.txt_buscar_historial)
        self.tabla_historial = QTableWidget(0, 6)
        self.tabla_historial.setHorizontalHeaderLabels(["ID", "Fecha/Hora", "Ubicación", "Humedad (%)", "Valor ADC", "Sensor"])
        self.tabla_historial.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        panel_historial.addWidget(self.tabla_historial)
        
        layout_tablas.addLayout(panel_alertas, 4)
        layout_tablas.addLayout(panel_historial, 6)
        
        layout_principal.addLayout(layout_tablas)
        self.paginador.addWidget(page_dash)

    def _crear_pantalla_graficas(self):
        self.page_graficas = QWidget()
        layout = QVBoxLayout(self.page_graficas)
        layout.setContentsMargins(25, 25, 25, 25)
        
        lbl_titulo = QLabel("📊 Análisis Gráfico de Sensores")
        lbl_titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #F8FAFC;")
        layout.addWidget(lbl_titulo)
        
        self.canvas_grafica = LienzoGrafica(self, width=8, height=6, dpi=100)
        layout.addWidget(self.canvas_grafica)
        self.paginador.addWidget(self.page_graficas)
        
    def _crear_pantalla_parametros(self):
        self.page_parametros = QWidget()
        layout = QVBoxLayout(self.page_parametros)
        layout.setContentsMargins(25, 25, 25, 25)
        
        lbl_titulo = QLabel("⚙️ Panel de Configuración")
        lbl_titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #F8FAFC;")
        layout.addWidget(lbl_titulo)
        
        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(30, 30, 30, 30)
        
        self.input_temp_max = QSpinBox()
        self.input_temp_max.setRange(0, 100)
        self.input_temp_max.setValue(35)
        self.input_temp_max.setFixedWidth(150)
        
        self.btn_guardar_params = QPushButton("💾 Aplicar Cambios")
        self.btn_guardar_params.setProperty("class", "btn_accion")
        self.btn_guardar_params.setFixedWidth(150)
        
        form_layout.addRow(QLabel("Límite Crítico Humedad (%):"), self.input_temp_max)
        form_layout.addRow(QLabel(""), self.btn_guardar_params)
        
        layout.addWidget(form_frame)
        layout.addStretch()
        self.paginador.addWidget(self.page_parametros)
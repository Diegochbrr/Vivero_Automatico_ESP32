from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QMarginsF
from PyQt6.QtWidgets import QTableWidgetItem, QFileDialog, QMessageBox, QCheckBox, QWidget, QHBoxLayout
from PyQt6.QtGui import QTextDocument, QPdfWriter, QPageSize, QPageLayout
from modelo import ModeloRiego
from vista import VistaRiego, DialogoCambiarCuenta

class HiloActualizacionDatos(QThread):
    """Hilo secundario para consultar la API en segundo plano sin congelar la interfaz."""
    datos_obtenidos = pyqtSignal(list, list)  # (historial, alertas)

    def __init__(self, modelo: ModeloRiego, id_sector: int = 1, intervalo_segundos: int = 3):
        super().__init__()
        self.modelo = modelo
        self.id_sector = id_sector
        self.intervalo = intervalo_segundos
        self._ejecutando = True

    def set_sector(self, id_sector: int):
        self.id_sector = id_sector

    def run(self):
        while self._ejecutando:
            historial = self.modelo.obtener_historial(self.id_sector)
            alertas = self.modelo.obtener_alertas()
            self.datos_obtenidos.emit(historial, alertas)
            # Pausa en milisegundos en el hilo secundario
            self.msleep(self.intervalo * 1000)

    def detener(self):
        self._ejecutando = False
        self.wait(1000)


class ControladorRiego:
    def __init__(self, vista: VistaRiego, modelo: ModeloRiego):
        self.vista = vista
        self.modelo = modelo
        self.historial_cache = []
        self.alertas_cache = []
        self.sectores_cache = []
        self.usuarios_cache = []
        self.sector_activo = 1
        self.usuario_sesion = {
            "id_usuario": 0,
            "nombre": "Invitado",
            "correo": "invitado@vivero.com",
            "rol": "INVITADO"
        }
        
        # Conectar botones del Menú Lateral
        self.vista.btn_nav_home.clicked.connect(self.ir_a_home)
        self.vista.btn_nav_graph.clicked.connect(self.ir_a_graficas)
        self.vista.btn_nav_settings.clicked.connect(lambda: self.vista.paginador.setCurrentIndex(2))
        self.vista.btn_nav_users.clicked.connect(self.ir_a_usuarios)
        self.vista.btn_nav_docs.clicked.connect(self.exportar_reporte)
        
        # Barra Superior Global: Selector de Sector y Botón de Cuenta
        self.vista.combo_sector.currentIndexChanged.connect(self.cambiar_sector_activo)
        self.vista.btn_badge_sesion.clicked.connect(self.abrir_dialogo_cambiar_cuenta)

        # Botones de Acción
        self.vista.btn_guardar_params.clicked.connect(self.guardar_parametros)
        
        # Buscadores en vivo
        self.vista.txt_buscar_alertas.textChanged.connect(self.filtrar_tabla_alertas)
        self.vista.txt_buscar_historial.textChanged.connect(self.filtrar_tabla_historial)

        # Botones de Eliminación
        self.vista.btn_eliminar_medicion.clicked.connect(self.eliminar_mediciones_seleccionadas)
        self.vista.btn_eliminar_alerta.clicked.connect(self.eliminar_alertas_seleccionadas)
        self.vista.btn_sel_todo_alertas.toggled.connect(self._toggle_sel_todo_alertas)
        self.vista.btn_sel_todo_historial.toggled.connect(self._toggle_sel_todo_historial)

        # Botón Forzar Riego
        self.vista.btn_forzar_riego.clicked.connect(self.forzar_riego_manual)

        # Botones de Configuración de Umbrales
        self.vista.btn_cargar_umbral.clicked.connect(self.cargar_umbral)

        # Botones de Gestión de Usuarios
        self.id_usuario_editando = None
        self.vista.btn_guardar_usuario.clicked.connect(self.guardar_nuevo_usuario)
        self.vista.btn_cancelar_edicion.clicked.connect(self.cancelar_edicion_usuario)
        self.vista.btn_editar_usuario.clicked.connect(self.iniciar_edicion_usuario)
        self.vista.btn_eliminar_usuario.clicked.connect(self.eliminar_usuario_seleccionado)
        self.vista.btn_refrescar_usuarios.clicked.connect(self.cargar_tabla_usuarios)
        self.vista.tabla_usuarios.cellDoubleClicked.connect(lambda row, col: self.iniciar_edicion_usuario())

        # Iniciar Carga de Sectores y Usuarios
        self.cargar_sectores_iniciales()
        self.cargar_tabla_usuarios()

        # Aplicar restricciones de seguridad del rol inicial (Modo Invitado)
        self.aplicar_permisos_rol(self.usuario_sesion.get("rol", "INVITADO"))
        self.vista.btn_badge_sesion.setText(f"👤  {self.usuario_sesion['nombre']} ({self.usuario_sesion['rol']})  ▾")

        # Iniciar Hilo en Segundo Plano (Asíncrono - Cero lag en la interfaz)
        self.hilo = HiloActualizacionDatos(self.modelo, id_sector=self.sector_activo, intervalo_segundos=3)
        self.hilo.datos_obtenidos.connect(self.actualizar_interfaz)
        self.hilo.start()

    def ir_a_home(self):
        self.vista.paginador.setCurrentIndex(0)

    def ir_a_graficas(self):
        self.vista.paginador.setCurrentIndex(1)
        self.actualizar_grafica_matplotlib()

    def ir_a_usuarios(self):
        self.vista.paginador.setCurrentIndex(3)
        self.cargar_tabla_usuarios()

    def actualizar_interfaz(self, historial, alertas):
        self.historial_cache = historial
        self.alertas_cache = alertas

        # 1. Actualizar Tarjetas Modernas con la última lectura
        if historial and len(historial) > 0:
            ultimo = historial[0]
            humedad = float(str(ultimo[3]).replace('%', ''))
            adc = int(ultimo[4])
            self.vista.lbl_valor_temp.setText(f"{humedad:.1f} %")
            self.vista.progreso_temp.setValue(int(humedad))
            self.vista.lbl_valor_turb.setText(f"{adc}")
            self.vista.progreso_turb.setValue(adc)
        else:
            self.vista.lbl_valor_temp.setText("-- %")
            self.vista.lbl_valor_turb.setText("--")

        # 2. Actualizar Tablas
        self.actualizar_tablas()

        # 3. Actualizar Gráfica si el usuario está en esa pestaña
        if self.vista.paginador.currentIndex() == 1:
            self.actualizar_grafica_matplotlib()

    def _make_chk_widget(self):
        """Crea un QCheckBox perfectamente centrado dentro de un widget contenedor."""
        contenedor = QWidget()
        layout_chk = QHBoxLayout(contenedor)
        layout_chk.setContentsMargins(0, 0, 0, 0)
        layout_chk.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chk = QCheckBox()
        layout_chk.addWidget(chk)
        return contenedor, chk

    def actualizar_tablas(self):
        filtro_hist = self.vista.txt_buscar_historial.text()
        filtro_alert = self.vista.txt_buscar_alertas.text()

        self.vista.tabla_historial.setRowCount(0)
        for fila_idx, fila_datos in enumerate(self.historial_cache):
            self.vista.tabla_historial.insertRow(fila_idx)

            # Columna 0: checkbox centrado
            contenedor_h, _ = self._make_chk_widget()
            self.vista.tabla_historial.setCellWidget(fila_idx, 0, contenedor_h)

            for col_idx, dato in enumerate(fila_datos):
                item = QTableWidgetItem(str(dato))
                item.setToolTip(str(dato))
                # Centrar ID, Humedad y ADC (ahora en cols 1, 4, 5)
                if col_idx in [0, 3, 4]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.vista.tabla_historial.setItem(fila_idx, col_idx + 1, item)
        
        self.vista.tabla_alertas.setRowCount(0)
        for fila_idx, fila_datos in enumerate(self.alertas_cache):
            self.vista.tabla_alertas.insertRow(fila_idx)

            # Columna 0: checkbox centrado
            contenedor_a, _ = self._make_chk_widget()
            self.vista.tabla_alertas.setCellWidget(fila_idx, 0, contenedor_a)

            for col_idx, dato in enumerate(fila_datos):
                item = QTableWidgetItem(str(dato))
                item.setToolTip(str(dato))
                # Centrar Tipo, Valor y Estado (ahora en cols 2, 4, 5)
                if col_idx in [1, 3, 4]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.vista.tabla_alertas.setItem(fila_idx, col_idx + 1, item)
                
        self.filtrar_tabla_historial(filtro_hist)
        self.filtrar_tabla_alertas(filtro_alert)

        # Ajustar ancho de columnas al contenido completo sin recortar nada
        self.vista.tabla_historial.resizeColumnsToContents()
        self.vista.tabla_historial.setColumnWidth(0, 36)  # mantener ancho del checkbox
        self.vista.tabla_alertas.resizeColumnsToContents()
        self.vista.tabla_alertas.setColumnWidth(0, 36)  # mantener ancho del checkbox

        # Resetear botón Seleccionar Todo al refrescar (historial)
        self.vista.btn_sel_todo_historial.blockSignals(True)
        self.vista.btn_sel_todo_historial.setChecked(False)
        self.vista.btn_sel_todo_historial.setText("\u2611\ufe0f  Seleccionar Todo")
        self.vista.btn_sel_todo_historial.blockSignals(False)

        # Resetear botón Seleccionar Todo al refrescar (alertas)
        self.vista.btn_sel_todo_alertas.blockSignals(True)
        self.vista.btn_sel_todo_alertas.setChecked(False)
        self.vista.btn_sel_todo_alertas.setText("\u2611\ufe0f  Seleccionar Todo")
        self.vista.btn_sel_todo_alertas.blockSignals(False)
        
    def actualizar_grafica_matplotlib(self):
        if not self.historial_cache:
            return

        # Colores según el tema activo
        oscuro   = self.vista._modo_oscuro
        tick_c   = '#94A3B8' if oscuro else '#64748B'
        grid_c   = '#1E3048' if oscuro else '#DDE6EF'
        title_c  = '#E2EAF4' if oscuro else '#1E2D3D'
        label_c  = '#7A90A8' if oscuro else '#64748B'
        leg_face = '#162032' if oscuro else '#FFFFFF'
        leg_edge = '#1E3048' if oscuro else '#DDE6EF'
        leg_lbl  = '#E2EAF4' if oscuro else '#1E2D3D'

        # Colores diferenciados para Fecha y Hora
        c_hora   = '#F59E0B' if oscuro else '#D97706'  # Ámbar/Naranja para la Hora
        c_fecha  = '#38BDF8' if oscuro else '#0284C7'  # Azul Celeste para la Fecha

        datos = self.historial_cache[:20][::-1]  # últimas 20 lecturas, orden cronológico

        # Extraer fecha (DD/MM/AAAA) y hora (HH:MM:SS)
        fechas_lista = []
        horas_lista  = []
        for d in datos:
            s = str(d[1]).strip()
            partes = s.split()
            f_str, h_str = "", ""
            if len(partes) >= 2:
                fp = partes[0].split('-')
                f_str = f"{fp[2]}/{fp[1]}/{fp[0]}" if len(fp) == 3 else partes[0]
                h_str = partes[1][:8]
            elif len(partes) == 1:
                h_str = partes[0][:8]
            fechas_lista.append(f_str)
            horas_lista.append(h_str)

        humedades  = [float(str(d[3]).replace('%', '')) for d in datos]
        adcs       = [int(d[4]) for d in datos]
        indices    = list(range(len(datos)))

        ax1 = self.vista.canvas_grafica.axes
        ax2 = self.vista.canvas_grafica.axes2
        fig = ax1.get_figure()

        ax1.clear()
        ax2.clear()

        # ── Subgráfica 1: Humedad ────────────────────────────────────────────
        ax1.plot(indices, humedades, color='#F59E0B', marker='o',
                 linewidth=2.5, markersize=5, label='Humedad (%)', zorder=3)
        ax1.fill_between(indices, humedades, 0, color='#F59E0B', alpha=0.12)

        # Líneas de umbral de riego
        hum_min = self.vista.input_hum_min.value()
        hum_max = self.vista.input_hum_max.value()
        ax1.axhline(y=hum_min, color='#EF4444', linestyle='--', linewidth=1.5,
                    alpha=0.85, label=f'Umbral mín. ON = {hum_min}%', zorder=2)
        ax1.axhline(y=hum_max, color='#10B981', linestyle='--', linewidth=1.5,
                    alpha=0.85, label=f'Umbral máx. OFF = {hum_max}%', zorder=2)

        ax1.set_title('Humedad del Suelo (%)', color=title_c, fontsize=11,
                      fontweight='bold', pad=6, loc='left')
        ax1.set_ylabel('Humedad (%)', color=label_c, fontsize=9.5)
        ax1.set_ylim(-2, 108)
        ax1.set_xticks(indices)
        ax1.set_xticklabels(horas_lista, rotation=35, ha='right', fontsize=7.5, color=c_hora)
        ax1.tick_params(axis='x', colors=tick_c)
        ax1.tick_params(axis='y', colors=tick_c, labelsize=9)
        ax1.grid(True, linestyle='--', color=grid_c, alpha=0.55, zorder=0)
        ax1.legend(facecolor=leg_face, edgecolor=leg_edge,
                   labelcolor=leg_lbl, fontsize=8.5, loc='upper right')

        # ── Subgráfica 2: Señal ADC ──────────────────────────────────────────
        ax2.plot(indices, adcs, color='#0EA5E9', marker='s', linestyle='-',
                 linewidth=2, markersize=5, label='ADC Crudo (0-4095)', zorder=3)
        ax2.fill_between(indices, adcs, 0, color='#0EA5E9', alpha=0.12)

        ax2.set_title('Señal ADC del Sensor Capacitivo (0-4095)', color=title_c, fontsize=11,
                      fontweight='bold', pad=6, loc='left')
        ax2.set_ylabel('Valor ADC', color=label_c, fontsize=9.5)
        ax2.set_ylim(-50, 4200)
        ax2.set_xticks(indices)
        ax2.set_xticklabels(horas_lista, rotation=35, ha='right', fontsize=7.5, color=c_hora)
        ax2.tick_params(axis='x', colors=tick_c)
        ax2.tick_params(axis='y', colors=tick_c, labelsize=9)
        ax2.grid(True, linestyle='--', color=grid_c, alpha=0.55, zorder=0)
        ax2.legend(facecolor=leg_face, edgecolor=leg_edge,
                   labelcolor=leg_lbl, fontsize=8.5, loc='upper right')

        # ── Mostrar la Fecha SOLO cuando cambia o al inicio (sin saturar) ───
        ultima_fecha = None
        fechas_unicas = set(f for f in fechas_lista if f)

        # Si hay cambio de día entre lecturas, marcarlo debajo del punto de cambio
        for i, fecha in enumerate(fechas_lista):
            if fecha and fecha != ultima_fecha:
                # Si hay más de un día en los datos, marcamos el cambio
                if len(fechas_unicas) > 1:
                    ax2.text(i, -0.28, f"Fecha: {fecha}", transform=ax2.get_xaxis_transform(),
                             ha='left', va='top', fontsize=7.5, color=c_fecha, fontweight='bold')
                ultima_fecha = fecha

        # Título general de la figura con la fecha principal y sector activo
        nombre_sec = f"Sector {self.sector_activo}"
        encargado_sec = ""
        for s in self.sectores_cache:
            if s.get("id_sector") == self.sector_activo:
                nombre_sec = s.get("nombre_sector", nombre_sec)
                encargado_sec = f" · Encargado: {s.get('encargado_nombre', '')}"
                break

        fecha_cabecera = f" · Fecha: {fechas_lista[0]}" if fechas_lista and fechas_lista[0] else ""
        if len(fechas_unicas) > 1:
            fecha_cabecera = f" · Fechas: {min(fechas_unicas)} a {max(fechas_unicas)}"

        fig.suptitle(f'SmartVivero — Últimas {len(datos)} lecturas · {nombre_sec}{encargado_sec}{fecha_cabecera}',
                     color=title_c, fontsize=10.5, fontweight='bold', y=0.98)

        self.vista.canvas_grafica.draw()


    def filtrar_tabla_historial(self, texto):
        texto = texto.lower()
        for fila in range(self.vista.tabla_historial.rowCount()):
            coincide = False
            for col in range(1, self.vista.tabla_historial.columnCount()):  # saltar col 0 (checkbox)
                item = self.vista.tabla_historial.item(fila, col)
                if item and texto in item.text().lower(): coincide = True; break
            self.vista.tabla_historial.setRowHidden(fila, not coincide)

    def filtrar_tabla_alertas(self, texto):
        texto = texto.lower()
        for fila in range(self.vista.tabla_alertas.rowCount()):
            coincide = False
            for col in range(1, self.vista.tabla_alertas.columnCount()):  # saltar col 0 (checkbox)
                item = self.vista.tabla_alertas.item(fila, col)
                if item and texto in item.text().lower(): coincide = True; break
            self.vista.tabla_alertas.setRowHidden(fila, not coincide)
            
    def cargar_umbral(self):
        """Carga los valores actuales del umbral desde la API y los rellena en el formulario."""
        id_sector = self.vista.spin_sector.value()
        self.vista.lbl_estado_params.setText("⏳ Cargando...")
        self.vista.lbl_estado_params.setStyleSheet("color: #38BDF8; font-size: 13px; font-weight: bold;")
        umbral = self.modelo.obtener_umbral(id_sector)
        if umbral:
            self.vista.input_hum_min.setValue(int(umbral.get("humedad_min_on", 30)))
            self.vista.input_hum_max.setValue(int(umbral.get("humedad_max_off", 70)))
            self.vista.input_tiempo_max.setValue(int(umbral.get("tiempo_max_riego_seg", 180)))
            self.vista.lbl_estado_params.setText(f"✅ Valores del Sector {id_sector} cargados.")
            self.vista.lbl_estado_params.setStyleSheet("color: #10B981; font-size: 13px; font-weight: bold;")
        else:
            self.vista.lbl_estado_params.setText(f"❌ No se encontró umbral para el Sector {id_sector}.")
            self.vista.lbl_estado_params.setStyleSheet("color: #EF4444; font-size: 13px; font-weight: bold;")

    def guardar_parametros(self):
        """Guarda los umbrales de riego en la API para el sector seleccionado."""
        id_sector = self.vista.spin_sector.value()
        hum_min = self.vista.input_hum_min.value()
        hum_max = self.vista.input_hum_max.value()
        tiempo = self.vista.input_tiempo_max.value()

        if hum_min >= hum_max:
            QMessageBox.warning(
                self.vista, "Valores Inválidos",
                f"⚠️ La humedad mínima ({hum_min}%) debe ser menor que la máxima ({hum_max}%)."
            )
            return

        self.vista.lbl_estado_params.setText("⏳ Guardando...")
        self.vista.lbl_estado_params.setStyleSheet("color: #38BDF8; font-size: 13px; font-weight: bold;")

        id_user = self.usuario_sesion.get("id_usuario", 1)
        exito = self.modelo.actualizar_umbral(id_sector, hum_min, hum_max, tiempo, id_usuario=id_user)
        if exito:
            self.vista.lbl_estado_params.setText(f"✅ Sector {id_sector} actualizado correctamente.")
            self.vista.lbl_estado_params.setStyleSheet("color: #10B981; font-size: 13px; font-weight: bold;")
        else:
            self.vista.lbl_estado_params.setText("❌ Error al guardar. Verifica la conexión con la API.")
            self.vista.lbl_estado_params.setStyleSheet("color: #EF4444; font-size: 13px; font-weight: bold;")

    def forzar_riego_manual(self):
        """Envía comando de riego forzado a la API para que el ESP32 lo recoja en su próximo ciclo de polling."""
        duracion = self.vista.spin_duracion_riego.value()
        self.vista.lbl_estado_riego.setText("⏳ Enviando comando...")
        self.vista.lbl_estado_riego.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: bold; background: transparent;")
        exito = self.modelo.forzar_riego(id_sector=self.sector_activo, duracion_seg=duracion)
        if exito:
            self.vista.lbl_estado_riego.setText(
                f"✅ Comando enviado a Sector {self.sector_activo}.\nEl ESP32 regará {duracion}s en su próximo ciclo."
            )
            self.vista.lbl_estado_riego.setStyleSheet("color: #10B981; font-size: 12px; font-weight: bold; background: transparent;")
        else:
            self.vista.lbl_estado_riego.setText("❌ Error al enviar el comando.\nVerifica la conexión con la API.")
            self.vista.lbl_estado_riego.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold; background: transparent;")

    # =========================================================================
    # GESTIÓN DE SECTORES Y ENCARGADOS
    # =========================================================================

    def cargar_sectores_iniciales(self):
        """Carga los sectores desde la API y los agrega al combo de la barra superior permanente."""
        self.sectores_cache = self.modelo.obtener_sectores()
        self.vista.combo_sector.blockSignals(True)
        self.vista.combo_sector.clear()
        for sec in self.sectores_cache:
            item_text = f"Sector {sec['id_sector']}: {sec['nombre_sector']}"
            self.vista.combo_sector.addItem(item_text, sec['id_sector'])
        self.vista.combo_sector.blockSignals(False)
        self.actualizar_info_encargado_topbar()

    def cambiar_sector_activo(self, index: int):
        """Se activa al seleccionar otro sector en el combo de la barra superior."""
        if index < 0 or index >= len(self.sectores_cache):
            return
        sec = self.sectores_cache[index]
        self.sector_activo = sec["id_sector"]
        self.hilo.set_sector(self.sector_activo)

        # Actualizar datos del encargado en el header superior
        self.actualizar_info_encargado_topbar()

        # Sincronizar el selector de sector en la página de parámetros
        self.vista.spin_sector.setValue(self.sector_activo)

        # Notificar a la API para sincronizar con el ESP32 / Wokwi
        self.modelo.fijar_sector_activo(self.sector_activo)

        # Forzar actualización inmediata de telemetría y tablas
        nuevo_historial = self.modelo.obtener_historial(self.sector_activo)
        self.actualizar_interfaz(nuevo_historial, self.alertas_cache)

    def actualizar_info_encargado_topbar(self):
        """Actualiza las etiquetas del miembro encargado en la barra superior fija."""
        sec_actual = None
        for s in self.sectores_cache:
            if s.get("id_sector") == self.sector_activo:
                sec_actual = s
                break
        if sec_actual:
            nombre = sec_actual.get("encargado_nombre", "Sin Asignar")
            rol = sec_actual.get("encargado_rol", "Técnico")
            correo = sec_actual.get("encargado_correo", "contacto@vivero.com")
            cultivo = sec_actual.get("tipo_cultivo", "General")
            self.vista.lbl_top_encargado.setText(f"👨‍🌾 Encargado: {nombre} ({rol})")
            self.vista.lbl_top_correo.setText(f"📧 {correo}  |  🌱 Cultivo: {cultivo}")
            self.vista.btn_badge_sesion.setText(f"👤  {self.usuario_sesion['nombre']} ({self.usuario_sesion['rol']})  ▾")

    # =========================================================================
    # CAMBIO DE CUENTA Y AUTENTICACIÓN
    # =========================================================================

    def abrir_dialogo_cambiar_cuenta(self):
        """Abre la ventana modal para cambiar de cuenta o autenticarse con contraseña."""
        if not self.usuarios_cache:
            self.usuarios_cache = self.modelo.obtener_usuarios()

        dlg = DialogoCambiarCuenta(self.vista, usuarios=self.usuarios_cache, modo_oscuro=self.vista._modo_oscuro)

        def procesar_login():
            correo = dlg.txt_correo.text().strip()
            contrasena = dlg.txt_pass.text().strip()

            if contrasena:
                user_auth = self.modelo.autenticar_usuario(correo, contrasena)
                if user_auth:
                    self.establecer_usuario_sesion(user_auth)
                    dlg.accept()
                    QMessageBox.information(self.vista, "Sesión Iniciada", f"✅ Bienvenido/a, {user_auth['nombre']}.")
                else:
                    dlg.lbl_error.setText("❌ Contraseña o correo incorrectos.")
            else:
                perfil = dlg.combo_perfiles.currentData()
                if perfil:
                    self.establecer_usuario_sesion(perfil)
                    dlg.accept()
                    if perfil.get("rol") == "INVITADO":
                        QMessageBox.information(self.vista, "Modo Invitado", "👤 Has cambiado al Modo Invitado (Solo Lectura).")
                    else:
                        QMessageBox.information(self.vista, "Cuenta Cambiada", f"👤 Sesión cambiada a: {perfil['nombre']} ({perfil.get('rol', 'OPERADOR')}).")
                else:
                    dlg.lbl_error.setText("⚠️ Selecciona un perfil o ingresa tu contraseña.")

        dlg.btn_login.clicked.connect(procesar_login)
        dlg.exec()

    def establecer_usuario_sesion(self, user: dict):
        """Actualiza el usuario activo de la sesión y refresca el badge del header."""
        self.usuario_sesion = {
            "id_usuario": user.get("id_usuario", 1),
            "nombre": user.get("nombre", "Usuario"),
            "correo": user.get("correo", ""),
            "rol": user.get("rol", "OPERADOR")
        }
        self.vista.btn_badge_sesion.setText(f"👤  {self.usuario_sesion['nombre']} ({self.usuario_sesion['rol']})  ▾")

        # Auto-seleccionar automáticamente el sector asignado al miembro
        correo_u = self.usuario_sesion.get("correo", "").strip().lower()
        nombre_u = self.usuario_sesion.get("nombre", "").strip().lower()
        sector_encontrado_idx = -1

        for idx, s in enumerate(self.sectores_cache):
            sec_correo = s.get("encargado_correo", "").strip().lower()
            sec_nombre = s.get("encargado_nombre", "").strip().lower()
            if (correo_u and correo_u == sec_correo) or (nombre_u and (nombre_u in sec_nombre or sec_nombre in nombre_u)):
                sector_encontrado_idx = idx
                break

        if sector_encontrado_idx >= 0 and sector_encontrado_idx != self.vista.combo_sector.currentIndex():
            self.vista.combo_sector.setCurrentIndex(sector_encontrado_idx)

        # Aplicar restricciones de permisos del nuevo rol activo
        self.aplicar_permisos_rol(self.usuario_sesion["rol"])

    def aplicar_permisos_rol(self, rol: str):
        """
        Aplica la matriz de permisos de seguridad según el rol del usuario activo:
          - INVITADO / VISUALIZADOR: Solo lectura (Dashboard, Gráficas y Reportes). Todas las acciones destructivas y de control bloqueadas.
          - OPERADOR / TECNICO_IOT: Forzar riego y monitoreo. Umbrales, eliminación y personal bloqueados.
          - AGRONOMO: Configuración de umbrales y forzar riego. Sin permisos de eliminación ni gestión de personal.
          - ADMINISTRADOR: Control total (Umbrales, Forzar Riego, Eliminar Alertas/Historial, Gestión de Personal).
        """
        rol = str(rol).upper()
        es_admin = (rol == "ADMINISTRADOR")
        es_agronomo = (rol in ["ADMINISTRADOR", "AGRONOMO"])
        es_operador = (rol in ["ADMINISTRADOR", "AGRONOMO", "OPERADOR", "TECNICO_IOT"])

        # 1. Eliminación de datos históricos y alertas (Solo Administrador)
        self.vista.btn_eliminar_medicion.setEnabled(es_admin)
        self.vista.btn_eliminar_alerta.setEnabled(es_admin)
        self.vista.btn_sel_todo_alertas.setEnabled(es_admin)
        self.vista.btn_sel_todo_historial.setEnabled(es_admin)
        tooltip_elim = "Eliminar registros seleccionados" if es_admin else f"🔒 Bloqueado: Rol {rol}. Solo Administradores pueden eliminar registros históricos."
        self.vista.btn_eliminar_medicion.setToolTip(tooltip_elim)
        self.vista.btn_eliminar_alerta.setToolTip(tooltip_elim)

        # 2. Configuración y Guardado de Umbrales (Administrador y Agrónomo)
        self.vista.btn_guardar_params.setEnabled(es_agronomo)
        self.vista.input_hum_min.setEnabled(es_agronomo)
        self.vista.input_hum_max.setEnabled(es_agronomo)
        self.vista.input_tiempo_max.setEnabled(es_agronomo)
        if not es_agronomo:
            msg_params = "🔒 Modo Invitado (Solo Lectura): Inicia sesión para modificar umbrales." if rol == "INVITADO" else f"🔒 Rol {rol}: Solo lectura. No tienes permisos para modificar umbrales."
            self.vista.lbl_estado_params.setText(msg_params)
            self.vista.lbl_estado_params.setStyleSheet("color: #F59E0B; font-size: 12px; font-weight: bold;")
            self.vista.btn_guardar_params.setToolTip("🔒 Bloqueado: Requiere rol ADMINISTRADOR o AGRÓNOMO.")
        else:
            self.vista.lbl_estado_params.setText("")
            self.vista.btn_guardar_params.setToolTip("Guardar parámetros de riego en la base de datos")

        # 3. Control Manual (Forzar Riego) - Administrador, Agrónomo, Operador y Técnico IoT
        self.vista.btn_forzar_riego.setEnabled(es_operador)
        self.vista.spin_duracion_riego.setEnabled(es_operador)
        if not es_operador:
            msg_riego = "Modo Invitado: Inicia sesión para activar riego manual." if rol == "INVITADO" else "Rol VISUALIZADOR en modo solo lectura."
            self.vista.btn_forzar_riego.setToolTip(f"🔒 Bloqueado: {msg_riego}")
            self.vista.lbl_estado_riego.setText(f"🔒 {msg_riego}")
            self.vista.lbl_estado_riego.setStyleSheet("color: #F59E0B; font-size: 11.5px; font-weight: bold; background: transparent;")
        else:
            self.vista.btn_forzar_riego.setToolTip("Activar bomba de riego de forma manual")
            self.vista.lbl_estado_riego.setText("")

        # 4. Gestión de Personal (Solo Administrador)
        self.vista.btn_guardar_usuario.setEnabled(es_admin)
        self.vista.btn_editar_usuario.setEnabled(es_admin)
        self.vista.btn_eliminar_usuario.setEnabled(es_admin)
        self.vista.txt_user_nombre.setEnabled(es_admin)
        self.vista.txt_user_correo.setEnabled(es_admin)
        self.vista.txt_user_pass.setEnabled(es_admin)
        self.vista.combo_user_rol.setEnabled(es_admin)
        tooltip_edit = "Editar el usuario marcado en la tabla" if es_admin else f"🔒 Bloqueado: Rol {rol}. Solo Administradores pueden registrar o editar personal."
        self.vista.btn_editar_usuario.setToolTip(tooltip_edit)
        if not es_admin:
            msg_user = "🔒 Modo Invitado: Solo consulta. Inicia sesión como Administrador para gestionar personal." if rol == "INVITADO" else f"🔒 Rol {rol}: Solo consulta. Solo Administradores pueden registrar, editar o eliminar miembros."
            self.vista.lbl_estado_usuarios.setText(msg_user)
            self.vista.lbl_estado_usuarios.setStyleSheet("color: #F59E0B; font-size: 12px; font-weight: bold;")
        else:
            self.vista.lbl_estado_usuarios.setText("")

    # =========================================================================
    # GESTIÓN DE PERSONAL Y USUARIOS
    # =========================================================================

    def cargar_tabla_usuarios(self):
        """Obtiene la lista de usuarios de la API y puebla la tabla con selección individual exclusiva."""
        self.usuarios_cache = self.modelo.obtener_usuarios()
        self.vista.tabla_usuarios.setRowCount(0)
        for fila_idx, u in enumerate(self.usuarios_cache):
            self.vista.tabla_usuarios.insertRow(fila_idx)

            # Columna 0: Checkbox centrado con selección individual exclusiva
            contenedor_u, chk_u = self._make_chk_widget()
            chk_u.clicked.connect(lambda checked, c=chk_u: self._al_marcar_checkbox_usuario(checked, c))
            self.vista.tabla_usuarios.setCellWidget(fila_idx, 0, contenedor_u)

            id_item = QTableWidgetItem(str(u.get("id_usuario", "")))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            nom_item = QTableWidgetItem(str(u.get("nombre", "")))
            cor_item = QTableWidgetItem(str(u.get("correo", "")))
            rol_item = QTableWidgetItem(str(u.get("rol", "")))
            rol_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            est_str = "🟢 Activo" if u.get("activo", True) else "🔴 Inactivo"
            est_item = QTableWidgetItem(est_str)
            est_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            f_raw = str(u.get("creado_en", "")).split("T")[0]
            f_item = QTableWidgetItem(f_raw)
            f_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.vista.tabla_usuarios.setItem(fila_idx, 1, id_item)
            self.vista.tabla_usuarios.setItem(fila_idx, 2, nom_item)
            self.vista.tabla_usuarios.setItem(fila_idx, 3, cor_item)
            self.vista.tabla_usuarios.setItem(fila_idx, 4, rol_item)
            self.vista.tabla_usuarios.setItem(fila_idx, 5, est_item)
            self.vista.tabla_usuarios.setItem(fila_idx, 6, f_item)

        self.vista.tabla_usuarios.setColumnWidth(0, 42)

    def _al_marcar_checkbox_usuario(self, marcado: bool, chk_actual: QCheckBox):
        """Garantiza selección exclusiva (solo 1 usuario a la vez) para máxima seguridad."""
        if marcado:
            tabla = self.vista.tabla_usuarios
            for fila in range(tabla.rowCount()):
                widget = tabla.cellWidget(fila, 0)
                if widget:
                    chk = widget.findChild(QCheckBox)
                    if chk and chk is not chk_actual and chk.isChecked():
                        chk.blockSignals(True)
                        chk.setChecked(False)
                        chk.blockSignals(False)

    def _obtener_filas_usuarios_marcadas(self):
        """Devuelve la lista de índices de fila marcadas con checkbox."""
        filas = []
        tabla = self.vista.tabla_usuarios
        for r in range(tabla.rowCount()):
            widget = tabla.cellWidget(r, 0)
            if widget:
                chk = widget.findChild(QCheckBox)
                if chk and chk.isChecked():
                    filas.append(r)
        return filas

    def iniciar_edicion_usuario(self):
        """Carga los datos del usuario marcado con checkbox en el formulario."""
        marcadas = self._obtener_filas_usuarios_marcadas()
        if len(marcadas) == 0:
            QMessageBox.warning(self.vista, "Sin Selección", "⚠️ Marca la casilla del usuario que deseas editar.")
            return
        elif len(marcadas) > 1:
            QMessageBox.warning(self.vista, "Selección Múltiple No Permitida", "⚠️ Por seguridad, solo puedes seleccionar 1 usuario a la vez.")
            return

        fila = marcadas[0]
        user = self.usuarios_cache[fila]
        self.id_usuario_editando = user["id_usuario"]

        # Rellenar campos del formulario
        self.vista.lbl_form_usuario_titulo.setText(f"✏️  Editar Miembro del Equipo (ID: #{self.id_usuario_editando})")
        self.vista.lbl_form_usuario_titulo.setStyleSheet("font-weight: 700; font-size: 13px; color: #F59E0B;")
        self.vista.txt_user_nombre.setText(user.get("nombre", ""))
        self.vista.txt_user_correo.setText(user.get("correo", ""))
        self.vista.txt_user_correo.setPlaceholderText("Correo (Opcional - dejar igual)")
        self.vista.txt_user_pass.clear()
        self.vista.txt_user_pass.setPlaceholderText("Contraseña (Opcional - dejar vacía para conservar)")
        self.vista.combo_user_rol.setCurrentText(user.get("rol", "OPERADOR"))
        self.vista.btn_guardar_usuario.setText("💾  Guardar Cambios")
        self.vista.btn_cancelar_edicion.setVisible(True)
        self.vista.lbl_estado_usuarios.setText(f"ℹ️ Editando a '{user.get('nombre')}'. Modifica los datos y presiona Guardar Cambios.")
        self.vista.lbl_estado_usuarios.setStyleSheet("color: #38BDF8; font-weight: bold;")

    def cancelar_edicion_usuario(self):
        """Restaura el formulario al modo de registro de nuevo usuario."""
        self.id_usuario_editando = None
        self.vista.lbl_form_usuario_titulo.setText("➕  Registrar Nuevo Miembro del Equipo")
        self.vista.lbl_form_usuario_titulo.setStyleSheet("font-weight: 700; font-size: 13px; color: #38BDF8;")
        self.vista.txt_user_nombre.clear()
        self.vista.txt_user_nombre.setPlaceholderText("Nombre completo (ej. Diego Charry)")
        self.vista.txt_user_correo.clear()
        self.vista.txt_user_correo.setPlaceholderText("Correo electrónico")
        self.vista.txt_user_pass.clear()
        self.vista.txt_user_pass.setPlaceholderText("Contraseña")
        self.vista.btn_guardar_usuario.setText("💾  Registrar")
        self.vista.btn_cancelar_edicion.setVisible(False)
        self.vista.lbl_estado_usuarios.setText("")

    def guardar_nuevo_usuario(self):
        """Registra un nuevo usuario o actualiza el usuario si está en modo edición."""
        nom = self.vista.txt_user_nombre.text().strip()
        cor = self.vista.txt_user_correo.text().strip()
        pas = self.vista.txt_user_pass.text().strip()
        rol = self.vista.combo_user_rol.currentText()

        # MODO EDICIÓN
        if self.id_usuario_editando is not None:
            if not nom:
                QMessageBox.warning(self.vista, "Campo Requerido", "⚠️ El nombre del usuario no puede estar vacío.")
                return

            self.vista.lbl_estado_usuarios.setText("⏳ Actualizando usuario...")
            self.vista.lbl_estado_usuarios.setStyleSheet("color: #38BDF8; font-weight: bold;")

            exito = self.modelo.actualizar_usuario(
                id_usuario=self.id_usuario_editando,
                nombre=nom,
                correo=cor if cor else None,
                contrasena=pas if pas else None,
                rol=rol
            )
            if exito:
                QMessageBox.information(self.vista, "Usuario Actualizado", f"✅ Usuario '{nom}' modificado exitosamente.")
                self.cancelar_edicion_usuario()
                self.cargar_tabla_usuarios()
            else:
                self.vista.lbl_estado_usuarios.setText("❌ Error al actualizar el usuario. Verifica la conexión.")
                self.vista.lbl_estado_usuarios.setStyleSheet("color: #EF4444; font-weight: bold;")
            return

        # MODO REGISTRO NUEVO
        if not nom or not cor or not pas:
            QMessageBox.warning(self.vista, "Campos Incompletos", "⚠️ Para registrar un nuevo miembro, completa el nombre, correo y contraseña.")
            return

        self.vista.lbl_estado_usuarios.setText("⏳ Guardando usuario...")
        self.vista.lbl_estado_usuarios.setStyleSheet("color: #38BDF8; font-weight: bold;")

        exito = self.modelo.crear_usuario(nom, cor, pas, rol)
        if exito:
            self.vista.lbl_estado_usuarios.setText(f"✅ Miembro '{nom}' registrado exitosamente.")
            self.vista.lbl_estado_usuarios.setStyleSheet("color: #10B981; font-weight: bold;")
            self.vista.txt_user_nombre.clear()
            self.vista.txt_user_correo.clear()
            self.vista.txt_user_pass.clear()
            self.cargar_tabla_usuarios()
        else:
            self.vista.lbl_estado_usuarios.setText("❌ Error al registrar usuario. Verifica el correo o la conexión.")
            self.vista.lbl_estado_usuarios.setStyleSheet("color: #EF4444; font-weight: bold;")

    def eliminar_usuario_seleccionado(self):
        """Elimina el usuario que tenga su casilla de verificación marcada (solo 1 a la vez por seguridad)."""
        marcadas = self._obtener_filas_usuarios_marcadas()
        if len(marcadas) == 0:
            QMessageBox.warning(self.vista, "Sin Selección", "⚠️ Marca la casilla del usuario que deseas eliminar.")
            return
        elif len(marcadas) > 1:
            QMessageBox.warning(self.vista, "Selección Múltiple No Permitida", "⚠️ Por seguridad, solo se puede eliminar 1 usuario a la vez.")
            return

        fila = marcadas[0]
        user = self.usuarios_cache[fila]
        id_u = user["id_usuario"]
        nom_u = user["nombre"]

        resp = QMessageBox.question(
            self.vista, "⚠️ Confirmar Eliminación",
            f"¿Estás seguro de eliminar a '{nom_u}' (ID {id_u}) del sistema?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            if self.modelo.eliminar_usuario(id_u):
                QMessageBox.information(self.vista, "Usuario Eliminado", f"✅ Usuario '{nom_u}' eliminado del sistema correctamente.")
                self.cargar_tabla_usuarios()
            else:
                QMessageBox.critical(self.vista, "Error", "❌ No se pudo eliminar el usuario.")

    def _toggle_sel_todo_historial(self, marcado: bool):
        """Marca o desmarca todos los checkboxes visibles de la tabla de historial."""
        tabla = self.vista.tabla_historial
        for fila in range(tabla.rowCount()):
            if not tabla.isRowHidden(fila):
                contenedor = tabla.cellWidget(fila, 0)
                if contenedor:
                    chk = contenedor.findChild(QCheckBox)
                    if chk:
                        chk.setChecked(marcado)
        etiqueta = "\u2612\ufe0f  Deseleccionar Todo" if marcado else "\u2611\ufe0f  Seleccionar Todo"
        self.vista.btn_sel_todo_historial.setText(etiqueta)

    def eliminar_mediciones_seleccionadas(self):
        """Elimina todas las mediciones cuyo checkbox está marcado."""
        tabla = self.vista.tabla_historial
        filas_marcadas = []
        for fila in range(tabla.rowCount()):
            contenedor = tabla.cellWidget(fila, 0)
            if contenedor:
                chk = contenedor.findChild(QCheckBox)
                if chk and chk.isChecked() and not tabla.isRowHidden(fila):
                    filas_marcadas.append(fila)

        if not filas_marcadas:
            QMessageBox.warning(self.vista, "Sin Selección",
                                "⚠️ Marca al menos una medición con el checkbox primero.")
            return

        respuesta = QMessageBox.question(
            self.vista, "⚠️ Confirmar Eliminación",
            f"¿Estás seguro de eliminar {len(filas_marcadas)} medición(es) seleccionada(s)?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        eliminadas = 0
        errores = 0
        ids_eliminados = []
        for fila in filas_marcadas:
            # ID está ahora en columna 1
            id_item = tabla.item(fila, 1)
            if not id_item:
                continue
            id_lectura = id_item.text()
            if self.modelo.eliminar_medicion(int(id_lectura)):
                eliminadas += 1
                ids_eliminados.append(id_lectura)
            else:
                errores += 1

        if eliminadas > 0:
            self.historial_cache = [d for d in self.historial_cache
                                    if str(d[0]) not in ids_eliminados]
            self.actualizar_tablas()
            msg = f"✅ {eliminadas} medición(es) eliminada(s) correctamente."
            if errores:
                msg += f"\n⚠️ {errores} medición(es) no pudieron eliminarse."
            QMessageBox.information(self.vista, "Eliminación Completada", msg)
        else:
            QMessageBox.critical(self.vista, "Error",
                                 "❌ No se pudo eliminar ninguna medición. Verifica la conexión con la API.")

    def _toggle_sel_todo_alertas(self, marcado: bool):
        """Marca o desmarca todos los checkboxes visibles de la tabla de alertas."""
        tabla = self.vista.tabla_alertas
        for fila in range(tabla.rowCount()):
            if not tabla.isRowHidden(fila):
                contenedor = tabla.cellWidget(fila, 0)
                if contenedor:
                    chk = contenedor.findChild(QCheckBox)
                    if chk:
                        chk.setChecked(marcado)
        etiqueta = "\u2612\ufe0f  Deseleccionar Todo" if marcado else "\u2611\ufe0f  Seleccionar Todo"
        self.vista.btn_sel_todo_alertas.setText(etiqueta)

    def eliminar_alertas_seleccionadas(self):
        """Elimina todas las alertas cuyo checkbox está marcado."""
        tabla = self.vista.tabla_alertas
        filas_marcadas = []
        for fila in range(tabla.rowCount()):
            contenedor = tabla.cellWidget(fila, 0)
            if contenedor:
                chk = contenedor.findChild(QCheckBox)
                if chk and chk.isChecked() and not tabla.isRowHidden(fila):
                    filas_marcadas.append(fila)

        if not filas_marcadas:
            QMessageBox.warning(self.vista, "Sin Selección",
                                "⚠️ Marca al menos una alerta con el checkbox primero.")
            return

        respuesta = QMessageBox.question(
            self.vista, "⚠️ Confirmar Eliminación",
            f"¿Estás seguro de eliminar {len(filas_marcadas)} alerta(s) seleccionada(s)?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        alertas_raw_api = self.modelo.obtener_alertas_con_id()
        if not alertas_raw_api:
            QMessageBox.critical(self.vista, "Error", "❌ No se pudo obtener los IDs de las alertas.")
            return

        eliminadas = 0
        errores = 0
        for fila in filas_marcadas:
            if fila >= len(alertas_raw_api):
                continue
            id_alerta = alertas_raw_api[fila]["id_alerta"]
            if self.modelo.eliminar_alerta(id_alerta):
                eliminadas += 1
            else:
                errores += 1

        if eliminadas > 0:
            # Reconstruir cache quitando las filas eliminadas (de mayor a menor para no desfasar índices)
            for fila in sorted(filas_marcadas, reverse=True):
                if fila < len(self.alertas_cache):
                    self.alertas_cache.pop(fila)
            self.actualizar_tablas()
            msg = f"✅ {eliminadas} alerta(s) eliminada(s) correctamente."
            if errores:
                msg += f"\n⚠️ {errores} alerta(s) no pudieron eliminarse."
            QMessageBox.information(self.vista, "Eliminación Completada", msg)
        else:
            QMessageBox.critical(self.vista, "Error",
                                 "❌ No se pudo eliminar ninguna alerta. Verifica la conexión con la API.")

    def exportar_reporte(self):
        """Genera y exporta un informe técnico oficial completo en PDF con QPdfWriter nativo (cero cierres)."""
        try:
            sec_actual = None
            for s in self.sectores_cache:
                if s.get("id_sector") == self.sector_activo:
                    sec_actual = s
                    break

            nombre_sec = sec_actual.get("nombre_sector", f"Invernadero {self.sector_activo}") if sec_actual else f"Invernadero {self.sector_activo}"
            encargado = sec_actual.get("encargado_nombre", "Sin Asignar") if sec_actual else "Sin Asignar"
            rol_enc = sec_actual.get("encargado_rol", "Agrónomo") if sec_actual else "Agrónomo"
            correo_enc = sec_actual.get("encargado_correo", "contacto@vivero.com") if sec_actual else "contacto@vivero.com"
            cultivo = sec_actual.get("tipo_cultivo", "General") if sec_actual else "General"
            desc_sec = sec_actual.get("descripcion", "Sector de cultivo automatizado con sensores capacitivos y ESP32") if sec_actual else ""

            nombre_archivo_sugerido = f"Informe_SmartVivero_Sector_{self.sector_activo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            ruta_archivo, _ = QFileDialog.getSaveFileName(
                self.vista,
                "Guardar Informe Técnico Oficial",
                nombre_archivo_sugerido,
                "Archivos PDF (*.pdf)"
            )
            if not ruta_archivo:
                return

            # 1. Obtener Datos del Historial, Alertas y Umbrales
            datos = self.historial_cache if self.historial_cache else self.modelo.obtener_historial(self.sector_activo)
            umbral = self.modelo.obtener_umbral(self.sector_activo) or {}
            alertas = self.alertas_cache if self.alertas_cache else self.modelo.obtener_alertas()

            # 2. Datos del Auditor
            auditor_nombre = self.usuario_sesion.get("nombre", "Operador del Sistema")
            auditor_rol = self.usuario_sesion.get("rol", "OPERADOR")
            auditor_correo = self.usuario_sesion.get("correo", "usuario@vivero.com")
            fecha_emision = datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")

            # 3. Métricas y Estadísticas
            hum_min_config = float(umbral.get("humedad_min_on", 35.0))
            hum_max_config = float(umbral.get("humedad_max_off", 70.0))
            t_max_config = int(umbral.get("tiempo_max_riego_seg", 180))

            hum_valores = []
            for fila in datos:
                try:
                    h_val = float(str(fila[3]).replace("%", "").strip())
                    hum_valores.append(h_val)
                except (ValueError, IndexError):
                    pass

            total_muestras = len(datos)
            hum_promedio = f"{(sum(hum_valores) / len(hum_valores)):.1f}%" if hum_valores else "N/A"
            hum_minima = f"{min(hum_valores):.1f}%" if hum_valores else "N/A"
            hum_maxima = f"{max(hum_valores):.1f}%" if hum_valores else "N/A"
            hum_actual = f"{hum_valores[0]:.1f}%" if hum_valores else "N/A"

            # 4. Construcción del HTML con formato nativo compatible con QTextDocument
            html = f"""
            <table width="100%" cellpadding="6" cellspacing="0" style="background-color: #0F172A; font-family: 'Segoe UI', Arial, sans-serif;">
                <tr>
                    <td>
                        <font size="4" color="#38BDF8"><b>🌱 SmartVivero IoT &mdash; Informe Técnico Oficial</b></font><br>
                        <font size="1" color="#94A3B8">SISTEMA AUTOMATIZADO DE TELEMETRÍA ESP32 Y CONTROL DE CULTIVOS &middot; GRUPO 3</font>
                    </td>
                    <td align="right">
                        <font size="2" color="#34D399"><b>● SISTEMA EN LÍNEA</b></font>
                    </td>
                </tr>
            </table>

            <table width="100%" border="1" cellpadding="4" cellspacing="0" style="border-collapse: collapse; font-family: 'Segoe UI', Arial, sans-serif; font-size: 8.5pt; border-color: #CBD5E1; margin-top: 6px;">
                <tr style="background-color: #F1F5F9;">
                    <td width="22%"><b>◆ Sector Auditado:</b></td>
                    <td width="28%">{nombre_sec} (ID: {self.sector_activo})</td>
                    <td width="22%"><b>◆ Tipo de Cultivo:</b></td>
                    <td width="28%">{cultivo}</td>
                </tr>
                <tr>
                    <td><b>◆ Responsable Zona:</b></td>
                    <td>{encargado} ({rol_enc})</td>
                    <td><b>◆ Contacto Zona:</b></td>
                    <td>{correo_enc}</td>
                </tr>
                <tr style="background-color: #F1F5F9;">
                    <td><b>◆ Emitido / Auditado Por:</b></td>
                    <td><b>{auditor_nombre}</b> ({auditor_rol})</td>
                    <td><b>◆ Fecha / Hora:</b></td>
                    <td>{fecha_emision}</td>
                </tr>
                <tr>
                    <td><b>◆ Descripción:</b></td>
                    <td colspan="3">{desc_sec}</td>
                </tr>
            </table>

            <p style="margin: 6px 0 2px 0; font-family: 'Segoe UI', Arial, sans-serif;"><font size="2" color="#0F172A"><b>■ Resumen Operativo y Umbrales de Riego</b></font></p>
            <div style="height: 2px; background-color: #0284C7; margin-bottom: 4px;"></div>

            <table width="100%" border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; text-align: center; font-family: 'Segoe UI', Arial, sans-serif; border-color: #CBD5E1;">
                <tr style="background-color: #F8FAFC;">
                    <td width="25%">
                        <font size="1" color="#64748B"><b>HUMEDAD ACTUAL</b></font><br>
                        <font size="5" color="#0284C7"><b>{hum_actual}</b></font><br>
                        <font size="1" color="#059669">Última lectura en vivo</font>
                    </td>
                    <td width="25%">
                        <font size="1" color="#64748B"><b>HUMEDAD PROMEDIO</b></font><br>
                        <font size="5" color="#0284C7"><b>{hum_promedio}</b></font><br>
                        <font size="1" color="#64748B">Mín: {hum_minima} | Máx: {hum_maxima}</font>
                    </td>
                    <td width="25%">
                        <font size="1" color="#64748B"><b>UMBRAL DE RIEGO</b></font><br>
                        <font size="4" color="#059669"><b>{hum_min_config:.1f}% - {hum_max_config:.1f}%</b></font><br>
                        <font size="1" color="#64748B">Min ON / Max OFF</font>
                    </td>
                    <td width="25%">
                        <font size="1" color="#64748B"><b>TIEMPO MÁX. BOMBA</b></font><br>
                        <font size="4" color="#D97706"><b>{t_max_config} seg</b></font><br>
                        <font size="1" color="#64748B">Protección anti-desborde</font>
                    </td>
                </tr>
            </table>

            <p style="margin: 6px 0 2px 0; font-family: 'Segoe UI', Arial, sans-serif;"><font size="2" color="#0F172A"><b>■ Registro Detallado de Telemetría (Muestras Recientes: {total_muestras} totales)</b></font></p>
            <div style="height: 2px; background-color: #0284C7; margin-bottom: 4px;"></div>

            <table width="100%" border="1" cellpadding="4" cellspacing="0" style="border-collapse: collapse; font-family: 'Segoe UI', Arial, sans-serif; font-size: 8pt; border-color: #CBD5E1; text-align: center;">
                <tr style="background-color: #1E293B; color: #FFFFFF;">
                    <th width="10%" style="color: #FFFFFF;"><b>ID</b></th>
                    <th width="26%" style="color: #FFFFFF;"><b>Fecha / Hora</b></th>
                    <th width="22%" style="color: #FFFFFF;"><b>Ubicación / Sector</b></th>
                    <th width="16%" style="color: #FFFFFF;"><b>Humedad (%)</b></th>
                    <th width="13%" style="color: #FFFFFF;"><b>Valor ADC</b></th>
                    <th width="13%" style="color: #FFFFFF;"><b>Sensor</b></th>
                </tr>
            """

            if datos:
                for i, fila in enumerate(datos[:15]):
                    bg = "#F8FAFC" if i % 2 == 1 else "#FFFFFF"
                    id_reg = fila[0]
                    fecha_reg = fila[1]
                    ubi_reg = fila[2]
                    hum_reg = str(fila[3])
                    adc_reg = fila[4]
                    sen_reg = fila[5]
                    html += f"""
                    <tr style="background-color: {bg};">
                        <td><b>#{id_reg}</b></td>
                        <td>{fecha_reg}</td>
                        <td>{ubi_reg}</td>
                        <td><font color="#0284C7"><b>{hum_reg}</b></font></td>
                        <td>{adc_reg}</td>
                        <td>{sen_reg}</td>
                    </tr>
                    """
            else:
                html += "<tr><td colspan='6' align='center' style='padding: 6px;'><font color='#64748B'>No hay registros de telemetría disponibles en este sector.</font></td></tr>"

            html += f"""
            </table>

            <p style="margin: 6px 0 2px 0; font-family: 'Segoe UI', Arial, sans-serif;"><font size="2" color="#0F172A"><b>▲ Registro de Incidentes y Monitoreo de Reservorio</b></font></p>
            <div style="height: 2px; background-color: #0284C7; margin-bottom: 4px;"></div>

            <table width="100%" border="1" cellpadding="4" cellspacing="0" style="border-collapse: collapse; font-family: 'Segoe UI', Arial, sans-serif; font-size: 8pt; border-color: #CBD5E1; text-align: center;">
                <tr style="background-color: #1E293B; color: #FFFFFF;">
                    <th width="26%" style="color: #FFFFFF;"><b>Fecha / Hora</b></th>
                    <th width="18%" style="color: #FFFFFF;"><b>Tipo</b></th>
                    <th width="20%" style="color: #FFFFFF;"><b>Sensor</b></th>
                    <th width="18%" style="color: #FFFFFF;"><b>Nivel Detectado</b></th>
                    <th width="18%" style="color: #FFFFFF;"><b>Estado Bomba</b></th>
                </tr>
            """

            if alertas:
                for i, al in enumerate(alertas[:6]):
                    bg = "#F8FAFC" if i % 2 == 1 else "#FFFFFF"
                    f_al   = str(al[0]) if len(al) > 0 else ""
                    t_al   = str(al[1]) if len(al) > 1 else "CRÍTICO"
                    s_al   = str(al[2]) if len(al) > 2 else "Sensor Flotador"
                    val_al = str(al[3]) if len(al) > 3 else "NORMAL"
                    est_al = str(al[4]) if len(al) > 4 else "Activa"
                    html += f"""
                    <tr style="background-color: {bg};">
                        <td>{f_al}</td>
                        <td><font color="#DC2626"><b>{t_al}</b></font></td>
                        <td>{s_al}</td>
                        <td><b>{val_al}</b></td>
                        <td>{est_al}</td>
                    </tr>
                    """
            else:
                html += "<tr><td colspan='5' align='center' style='padding: 6px;'><font color='#059669'><b>● Reservorio óptimo. Sin alertas críticas registradas.</b></font></td></tr>"

            html += f"""
            </table>

            <table width="100%" cellpadding="6" cellspacing="0" style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 8.5pt; margin-top: 14px;">
                <tr>
                    <td width="45%" align="center" style="border-top: 1px solid #94A3B8;">
                        <b>{auditor_nombre}</b><br>
                        <font color="#64748B">{auditor_rol} &mdash; Auditor del Reporte</font><br>
                        <font size="1" color="#94A3B8">{auditor_correo}</font>
                    </td>
                    <td width="10%"></td>
                    <td width="45%" align="center" style="border-top: 1px solid #94A3B8;">
                        <b>{encargado}</b><br>
                        <font color="#64748B">{rol_enc} &mdash; Responsable del Sector</font><br>
                        <font size="1" color="#94A3B8">{correo_enc}</font>
                    </td>
                </tr>
            </table>

            <table width="100%" cellpadding="4" cellspacing="0" style="border-top: 1px solid #CBD5E1; font-family: 'Segoe UI', Arial, sans-serif; font-size: 7.5pt; color: #64748B; margin-top: 6px;">
                <tr>
                    <td>
                        <b>SmartVivero Cloud Engine</b> &middot; Base de Datos Neon PostgreSQL &middot; ESP32 MicroPython<br>
                        <i>Desarrollado y certificado por <b>GRUPO 3</b> &middot; Ingeniería de Software y Sistemas IoT</i>
                    </td>
                    <td align="right">
                        Documento Oficial de Auditoría Técnica
                    </td>
                </tr>
            </table>
            """

            # 5. Generar PDF usando QPdfWriter nativo
            doc = QTextDocument()
            doc.setHtml(html)

            writer = QPdfWriter(ruta_archivo)
            writer.setResolution(300)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageOrientation(QPageLayout.Orientation.Portrait)
            writer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
            
            doc.print(writer)
            QMessageBox.information(
                self.vista,
                "Reporte Generado Exitosamente",
                f"📄 El Informe Técnico Oficial del {nombre_sec} ha sido exportado en PDF correctamente:\n\n{ruta_archivo}"
            )
        except Exception as e:
            print(f"Error generando PDF: {e}")
            QMessageBox.critical(self.vista, "Error al Exportar PDF", f"❌ Ocurrió un error al generar el PDF:\n{str(e)}")
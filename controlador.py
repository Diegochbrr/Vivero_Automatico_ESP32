from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QTableWidgetItem, QFileDialog, QMessageBox
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from modelo import ModeloRiego
from vista import VistaRiego

class HiloActualizacionDatos(QThread):
    """Hilo secundario para consultar la API en segundo plano sin congelar la interfaz."""
    datos_obtenidos = pyqtSignal(list, list)  # (historial, alertas)

    def __init__(self, modelo: ModeloRiego, intervalo_segundos: int = 3):
        super().__init__()
        self.modelo = modelo
        self.intervalo = intervalo_segundos
        self._ejecutando = True

    def run(self):
        while self._ejecutando:
            historial = self.modelo.obtener_historial()
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
        
        # Conectar botones del Menú Lateral
        self.vista.btn_nav_home.clicked.connect(self.ir_a_home)
        self.vista.btn_nav_graph.clicked.connect(self.ir_a_graficas)
        self.vista.btn_nav_settings.clicked.connect(lambda: self.vista.paginador.setCurrentIndex(2))
        self.vista.btn_nav_docs.clicked.connect(self.exportar_reporte)
        
        # Botones de Acción
        self.vista.btn_guardar_params.clicked.connect(self.guardar_parametros)
        
        # Buscadores en vivo
        self.vista.txt_buscar_alertas.textChanged.connect(self.filtrar_tabla_alertas)
        self.vista.txt_buscar_historial.textChanged.connect(self.filtrar_tabla_historial)

        # Botones de Eliminación
        self.vista.btn_eliminar_medicion.clicked.connect(self.eliminar_medicion_seleccionada)
        self.vista.btn_eliminar_alerta.clicked.connect(self.eliminar_alerta_seleccionada)

        # Botones de Configuración de Umbrales
        self.vista.btn_cargar_umbral.clicked.connect(self.cargar_umbral)
        self.vista.btn_guardar_params.clicked.connect(self.guardar_parametros)

        # Iniciar Hilo en Segundo Plano (Asíncrono - Cero lag en la interfaz)
        self.hilo = HiloActualizacionDatos(self.modelo, intervalo_segundos=3)
        self.hilo.datos_obtenidos.connect(self.actualizar_interfaz)
        self.hilo.start()

    def ir_a_home(self):
        self.vista.paginador.setCurrentIndex(0)

    def ir_a_graficas(self):
        self.vista.paginador.setCurrentIndex(1)
        self.actualizar_grafica_matplotlib()

    def actualizar_interfaz(self, historial, alertas):
        self.historial_cache = historial
        self.alertas_cache = alertas

        # 1. Actualizar Tarjetas Modernas con la última lectura
        if historial and len(historial) > 0:
            ultimo = historial[0]
            humedad = float(ultimo[3])
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

    def actualizar_tablas(self):
        filtro_hist = self.vista.txt_buscar_historial.text()
        filtro_alert = self.vista.txt_buscar_alertas.text()

        self.vista.tabla_historial.setRowCount(0)
        for fila_idx, fila_datos in enumerate(self.historial_cache):
            self.vista.tabla_historial.insertRow(fila_idx)
            for col_idx, dato in enumerate(fila_datos):
                self.vista.tabla_historial.setItem(fila_idx, col_idx, QTableWidgetItem(str(dato)))
        
        self.vista.tabla_alertas.setRowCount(0)
        for fila_idx, fila_datos in enumerate(self.alertas_cache):
            self.vista.tabla_alertas.insertRow(fila_idx)
            for col_idx, dato in enumerate(fila_datos):
                self.vista.tabla_alertas.setItem(fila_idx, col_idx, QTableWidgetItem(str(dato)))
                
        self.filtrar_tabla_historial(filtro_hist)
        self.filtrar_tabla_alertas(filtro_alert)
        
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

        datos = self.historial_cache[:20][::-1]  # últimas 20 lecturas, orden cronológico

        # Etiquetas del eje X: fecha + hora
        def fmt(d):
            partes = str(d[1]).split()
            if len(partes) > 1:
                return f"{partes[0]}\n{partes[1][:5]}"
            return str(d[1])

        etiquetas  = [fmt(d) for d in datos]
        humedades  = [float(d[3]) for d in datos]
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
        ax1.fill_between(indices, humedades, 0, color='#F59E0B', alpha=0.10)

        # Líneas de umbral de riego
        hum_min = self.vista.input_hum_min.value()
        hum_max = self.vista.input_hum_max.value()
        ax1.axhline(y=hum_min, color='#EF4444', linestyle='--', linewidth=1.5,
                    alpha=0.85, label=f'Umbral mín. ON = {hum_min}%', zorder=2)
        ax1.axhline(y=hum_max, color='#10B981', linestyle='--', linewidth=1.5,
                    alpha=0.85, label=f'Umbral máx. OFF = {hum_max}%', zorder=2)

        ax1.set_title('Humedad del Suelo', color=title_c, fontsize=11,
                      fontweight='bold', pad=6, loc='left')
        ax1.set_ylabel('Humedad (%)', color=label_c, fontsize=10)
        ax1.set_ylim(-2, 108)
        ax1.set_xticks(indices)
        ax1.tick_params(axis='x', colors=tick_c, labelsize=8)
        ax1.tick_params(axis='y', colors=tick_c, labelsize=9)
        ax1.grid(True, linestyle='--', color=grid_c, alpha=0.55, zorder=0)
        ax1.legend(facecolor=leg_face, edgecolor=leg_edge,
                   labelcolor=leg_lbl, fontsize=8.5, loc='upper right')

        # ── Subgráfica 2: Señal ADC ──────────────────────────────────────────
        ax2.plot(indices, adcs, color='#0EA5E9', marker='s', linestyle='-',
                 linewidth=2, markersize=5, label='ADC Crudo (0-4095)', zorder=3)
        ax2.fill_between(indices, adcs, 0, color='#0EA5E9', alpha=0.10)

        ax2.set_title('Señal ADC del Sensor Capacitivo', color=title_c, fontsize=11,
                      fontweight='bold', pad=6, loc='left')
        ax2.set_ylabel('Valor ADC', color=label_c, fontsize=10)
        ax2.set_xlabel('Fecha / Hora de lectura', color=label_c, fontsize=10)
        ax2.set_ylim(-50, 4200)
        ax2.set_xticks(indices)
        ax2.set_xticklabels(etiquetas, rotation=30, ha='right', fontsize=7.5)
        ax2.tick_params(axis='x', colors=tick_c)
        ax2.tick_params(axis='y', colors=tick_c, labelsize=9)
        ax2.grid(True, linestyle='--', color=grid_c, alpha=0.55, zorder=0)
        ax2.legend(facecolor=leg_face, edgecolor=leg_edge,
                   labelcolor=leg_lbl, fontsize=8.5, loc='upper right')

        # Título general de la figura
        fig.suptitle(f'SmartVivero — Últimas {len(datos)} lecturas · Sector 1',
                     color=title_c, fontsize=12, fontweight='bold', y=0.97)

        self.vista.canvas_grafica.draw()


    def filtrar_tabla_historial(self, texto):
        texto = texto.lower()
        for fila in range(self.vista.tabla_historial.rowCount()):
            coincide = False
            for col in range(self.vista.tabla_historial.columnCount()):
                item = self.vista.tabla_historial.item(fila, col)
                if item and texto in item.text().lower(): coincide = True; break
            self.vista.tabla_historial.setRowHidden(fila, not coincide)

    def filtrar_tabla_alertas(self, texto):
        texto = texto.lower()
        for fila in range(self.vista.tabla_alertas.rowCount()):
            coincide = False
            for col in range(self.vista.tabla_alertas.columnCount()):
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

        exito = self.modelo.actualizar_umbral(id_sector, hum_min, hum_max, tiempo)
        if exito:
            self.vista.lbl_estado_params.setText(f"✅ Sector {id_sector} actualizado correctamente.")
            self.vista.lbl_estado_params.setStyleSheet("color: #10B981; font-size: 13px; font-weight: bold;")
        else:
            self.vista.lbl_estado_params.setText("❌ Error al guardar. Verifica la conexión con la API.")
            self.vista.lbl_estado_params.setStyleSheet("color: #EF4444; font-size: 13px; font-weight: bold;")

    def eliminar_medicion_seleccionada(self):
        """Elimina la medición seleccionada en la tabla de historial."""
        fila = self.vista.tabla_historial.currentRow()
        if fila < 0:
            QMessageBox.warning(self.vista, "Sin Selección", "⚠️ Selecciona una fila del historial primero.")
            return
        id_item = self.vista.tabla_historial.item(fila, 0)
        if not id_item:
            return
        id_lectura = id_item.text()
        respuesta = QMessageBox.question(
            self.vista, "⚠️ Confirmar Eliminación",
            f"¿Estás seguro de eliminar la medición con ID {id_lectura}?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if respuesta == QMessageBox.StandardButton.Yes:
            exito = self.modelo.eliminar_medicion(int(id_lectura))
            if exito:
                QMessageBox.information(self.vista, "Eliminado", f"✅ Medición ID {id_lectura} eliminada correctamente.")
                self.historial_cache = [d for d in self.historial_cache if str(d[0]) != id_lectura]
                self.actualizar_tablas()
            else:
                QMessageBox.critical(self.vista, "Error", "❌ No se pudo eliminar la medición. Verifica la conexión con la API.")

    def eliminar_alerta_seleccionada(self):
        """Elimina la alerta seleccionada en la tabla de alertas."""
        fila = self.vista.tabla_alertas.currentRow()
        if fila < 0:
            QMessageBox.warning(self.vista, "Sin Selección", "⚠️ Selecciona una fila de alertas primero.")
            return
        # La columna 0 de alertas es 'Hora' (usada como referencia visual)
        # El ID real viene del cache en la posición de la fila
        if fila >= len(self.alertas_cache):
            return
        alerta_raw = self.alertas_cache[fila]
        # alertas_cache contiene tuplas; necesitamos el id_alerta del raw de la API
        # Para eso re-consultamos directamente usando el índice del cache
        # NOTA: el cache de alertas no guarda el id directamente; lo obtenemos del modelo
        alertas_raw_api = self.modelo.obtener_alertas_con_id()
        if not alertas_raw_api or fila >= len(alertas_raw_api):
            QMessageBox.critical(self.vista, "Error", "❌ No se pudo obtener el ID de la alerta.")
            return
        id_alerta = alertas_raw_api[fila]["id_alerta"]
        respuesta = QMessageBox.question(
            self.vista, "⚠️ Confirmar Eliminación",
            f"¿Estás seguro de eliminar esta alerta?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if respuesta == QMessageBox.StandardButton.Yes:
            exito = self.modelo.eliminar_alerta(id_alerta)
            if exito:
                QMessageBox.information(self.vista, "Eliminado", f"✅ Alerta eliminada correctamente.")
                self.alertas_cache.pop(fila)
                self.actualizar_tablas()
            else:
                QMessageBox.critical(self.vista, "Error", "❌ No se pudo eliminar la alerta. Verifica la conexión con la API.")

    def exportar_reporte(self):
        ruta_archivo, _ = QFileDialog.getSaveFileName(self.vista, "Guardar Reporte", "Reporte_SmartVivero.pdf", "PDF Files (*.pdf)")
        if not ruta_archivo: return 
        datos = self.historial_cache if self.historial_cache else self.modelo.obtener_historial()
        
        html = """
        <h1 style='text-align: center; color: #0F172A; font-family: Arial;'>Reporte Operativo - SmartVivero</h1>
        <p style='text-align: center; font-family: Arial; color: #64748B;'><b>Generado por el sistema central</b></p>
        <hr>
        <table border='1' width='100%' cellspacing='0' cellpadding='8' style='font-family: Arial; border-collapse: collapse;'>
            <tr style='background-color: #1E293B; color: white;'>
                <th>ID</th><th>Fecha / Hora</th><th>Ubicación</th><th>Humedad (%)</th><th>Valor ADC</th><th>Sensor</th>
            </tr>
        """
        for fila in datos:
            html += "<tr>" + "".join(f"<td style='text-align: center;'>{d}</td>" for d in fila) + "</tr>"
        html += "</table>"
        
        doc = QTextDocument()
        doc.setHtml(html)
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(ruta_archivo)
        doc.print(printer)
        QMessageBox.information(self.vista, "Reporte Exitoso", f"📄 El documento PDF ha sido generado y guardado en tu equipo.")
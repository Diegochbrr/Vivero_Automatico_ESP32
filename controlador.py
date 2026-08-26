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
        
        datos_recientes = self.historial_cache[:15][::-1] 
        fechas = [d[1].split()[1] if len(d[1].split()) > 1 else d[1] for d in datos_recientes]
        humedades = [float(d[3]) for d in datos_recientes]
        adcs = [int(d[4]) for d in datos_recientes]
        
        self.vista.canvas_grafica.axes.clear()
        
        # Colores brillantes para destacar en el fondo oscuro
        self.vista.canvas_grafica.axes.plot(fechas, humedades, color='#F59E0B', marker='o', label='Humedad (%)', linewidth=2.5)
        self.vista.canvas_grafica.axes.plot(fechas, [a / 40.95 for a in adcs], color='#0EA5E9', marker='s', linestyle='--', label='ADC Normalizado (%)', linewidth=2)
        
        self.vista.canvas_grafica.axes.legend(facecolor='#1E293B', edgecolor='#334155', labelcolor='#F8FAFC')
        self.vista.canvas_grafica.axes.tick_params(axis='x', rotation=45, colors='#94A3B8')
        self.vista.canvas_grafica.axes.tick_params(axis='y', colors='#94A3B8')
        self.vista.canvas_grafica.axes.grid(True, linestyle='--', color='#334155', alpha=0.6)
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
            
    def guardar_parametros(self):
        limite = self.vista.input_temp_max.value()
        QMessageBox.information(self.vista, "Ajustes Aplicados", f"✅ El límite crítico de humedad se fijó en {limite}%.")

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
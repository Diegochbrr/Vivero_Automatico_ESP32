# Aplicación de Escritorio, Mediciones y Glosario — SmartVivero

## Aplicación de Escritorio (Dashboard PyQt6)

### Descripción General
La aplicación de escritorio SmartVivero es una interfaz gráfica moderna, reactiva y modular desarrollada en Python con PyQt6. Consume la API REST del sistema para supervisar en tiempo real la telemetría del suelo, controlar actuadores, auditar alertas, ajustar umbrales agronómicos y administrar usuarios mediante un esquema de control de acceso por roles (RBAC).

---

### Componentes del Patrón Arquitectónico MVC

#### 1. Modelo (`modelo.py` — Clase `ModeloRiego`)
- Actúa como cliente HTTP hacia la API REST en la nube usando `requests`.
- Métodos principales:
  - `obtener_historial(id_sector)`: Recupera lecturas de humedad con formato `(ID, Fecha/Hora, Ubicación, Humedad %, ADC, Sensor)`.
  - `obtener_alertas()`: Recupera alertas como tuplas `(Fecha/Hora, Tipo, Sensor, Nivel, Estado Bomba)`.
  - `obtener_alertas_con_id()`: Recupera alertas crudas en formato diccionario incluyendo `id_alerta` para eliminación.
  - `obtener_umbral(id_sector)` / `actualizar_umbral(...)`: Consulta y modifica umbrales de humedad y tiempo de bomba.
  - `forzar_riego(id_sector, duracion_seg)`: Envía órdenes de encendido forzado de bomba.
  - `obtener_sectores()` / `actualizar_sector(...)`: Gestiona los datos agronómicos de los 5 sectores.
  - `fijar_sector_activo(id_sector)`: Sincroniza el sector seleccionado con el ESP32 en Wokwi.
  - `obtener_usuarios()` / `crear_usuario(...)` / `actualizar_usuario(...)` / `eliminar_usuario(...)`: CRUD de personal.
- Configura timeouts de seguridad de 3 a 5 segundos para evitar bloqueos y provee datos de contingencia en caso de fallos de red.

#### 2. Vista (`vista.py` — Clase `VistaRiego`)
- Construida con `QMainWindow` y `QStackedWidget` para navegación fluida.
- **Secciones de la Interfaz:**
  - **Barra Superior Permanente:** Selector de sector activo, ficha del encargado de zona, indicador de presencia (`En Línea`, `Ausente`, `En Campo`) y botón modal de sesión.
  - **Página 0 — Home (Dashboard):** Tarjetas de métricas en vivo con barras de progreso animadas, botón de forzado de riego manual, tabla de telemetría con casillas checkbox y buscador, y tabla de incidentes de reservorio.
  - **Página 1 — Gráficas (Matplotlib):** Visualización temporal de humedad con líneas de corte para umbrales mínimo y máximo e histograma de distribución.
  - **Página 2 — Configuración:** Ajuste de parámetros de riego por sector (`Humedad Mínima ON`, `Humedad Máxima OFF`, `Tiempo Máximo de Bomba`).
  - **Página 3 — Gestión de Personal:** Tabla de usuarios registrados con selección exclusiva por checkbox, formulario de alta/edición y asignación de roles.
- **Temas Visuales:** Soporte para Modo Oscuro (*Slate Glassmorphism*) y Modo Claro con persistencia.

#### 3. Controlador (`controlador.py` — Clase `ControladorRiego`)
- Conecta el Modelo con la Vista y maneja eventos y señales.
- **Hilo Asíncrono (`HiloActualizacionDatos` — `QThread`):** Consulta la API cada 3 segundos y emite `datos_obtenidos(historial, alertas)` para actualizar la interfaz sin congelar la aplicación.
- **Motor de Permisos RBAC:** Valida el perfil del usuario activo (`ADMINISTRADOR`, `AGRONOMO`, `OPERADOR`, `TECNICO_IOT`, `VISUALIZADOR`) y habilita/bloquea dinámicamente controles, botones de eliminación y formularios.
- **Buscadores en Tiempo Real:** Filtrado instantáneo en tablas mediante `filtrar_tabla_historial` y `filtrar_tabla_alertas`.

---

### Motor de Generación de Informes Técnicos Oficiales en PDF

- **Clase Base:** `QTextDocument` y `QPdfWriter` nativo de Qt.
- **Resolución y Formato:** Configurado a **300 DPI** (`writer.setResolution(300)`), formato **A4 Portrait** y márgenes de **10 mm**.
- **Tipografía:** Tamaños definidos en puntos (`pt`) con fuentes `Segoe UI` / `Arial`, garantizando nitidez perfecta y legibilidad en una sola página.
- **Contenido del Informe:**
  1. Membrete oficial de SmartVivero IoT y certificación del **GRUPO 3** con badge de estado en línea.
  2. Ficha técnica del sector auditado (ID, Nombre, Cultivo, Responsable de Zona, Correo y Descripción).
  3. Datos de auditoría técnica (Auditor en sesión, Rol y Marca temporal exacta).
  4. Resumen operativo con KPIs destacados: Humedad actual, Humedad promedio (mínima y máxima), Rango de umbrales configurado y Tiempo máximo de bomba.
  5. Registro detallado de telemetría reciente con fondo de filas alternado.
  6. Registro de incidentes del reservorio de agua con estado de la electrobomba.
  7. Bloque de firmas formales para el Auditor y el Responsable del Sector.
  8. Pie de página de autenticidad institucional.

---

## Datos de Medición de Referencia

### Formato de Registro de Humedad
- `id_lectura`: Entero autoincremental (ej: `118`)
- `id_sensor`: Identificador de hardware (`SEN-CAP-S01`)
- `id_sector`: Sector evaluado (del `1` al `5`)
- `humedad_porcentaje`: Valor en porcentaje con dos decimales (ej: `60.71%`)
- `valor_adc_crudo`: Entero entre 0 y 4095 (ej: `2486`)
- `fecha_hora`: Timestamp ISO 8601 (ej: `2026-08-28T19:22:34.091577`)

### Ejemplos de Lecturas Típicas y Comportamiento del Sistema

| Escenario de Campo | Humedad (%) | Valor ADC | Estado de la Bomba | Acción del Sistema |
| :--- | :---: | :---: | :---: | :--- |
| **Suelo muy seco / Árido** | 12.5% | 512 | **ENCENDIDA** | Riego automático activado por umbral mínimo (<35%) |
| **Suelo seco** | 28.7% | 1175 | **ENCENDIDA** | Riego en progreso |
| **Umbral exacto alcanzado** | 35.0% | 1432 | **APAGADA** | Umbral satisfecho; la bomba se detiene |
| **Humedad normal de cultivo**| 55.3% | 2265 | **APAGADA** | Nivel óptimo |
| **Suelo húmedo** | 70.0% | 2866 | **APAGADA** | Límite superior de apagado alcanzado |
| **Suelo saturado / Encharcado**| 95.2% | 3899 | **APAGADA** | Sistema en reposo preventivo |

### Formato de Alerta de Nivel de Agua
- `id_alerta`: Entero autoincremental (ej: `18`)
- `id_sector`: Sector afectado (`2`)
- `nivel_detectado`: Estado crítico (`"CRITICO_VACIO"`)
- `bomba_bloqueada`: `true` (bloqueo preventivo de la electrobomba)
- `fecha_hora`: Timestamp ISO 8601 (`2026-08-28T19:22:46.006830`)
- `observacion`: `"Alerta de nivel de agua detectada por ESP32"`

---

## Preguntas Frecuentes del Sistema (FAQ para Qwen / RAG)

**¿Cuál es el umbral de humedad para activar la bomba de riego?**  
El firmware del ESP32 activa la bomba automáticamente cuando la humedad del suelo cae por debajo del 35.0% (o el umbral mínimo personalizado en la base de datos para el sector activo).

**¿Qué ocurre si el reservorio de agua se queda vacío?**  
El switch de nivel en GPIO18 detecta la ausencia de líquido (`LOW`). De inmediato se corta la alimentación de la electrobomba (GPIO2 = 0), se enciende el LED rojo de emergencia (GPIO4 = 1), el LCD muestra `ALERTA: Sin Agua` y se transmite una alerta crítica a la API en la nube con `nivel_detectado = "CRITICO_VACIO"`.

**¿Cómo se calcula el porcentaje de humedad a partir de la lectura ADC?**  
Fórmula: $\text{Humedad (\%)} = (\text{ADC crudo} / 4095.0) \times 100.0$. El conversor analógico-digital del ESP32 tiene 12 bits de resolución (0 a 4095).

**¿Con qué frecuencia se envían datos y cómo se evita el consumo excesivo de memoria?**  
El ESP32 envía telemetría cada 5 segundos utilizando `time.ticks_ms()` para cronometrar ciclos de forma no bloqueante, evitando pérdidas de memoria o congelamientos en MicroPython.

**¿Qué técnica se usa para estabilizar las lecturas del sensor de humedad?**  
Se aplica sobremuestreo (oversampling): el microcontrolador realiza 10 lecturas consecutivas con intervalos de 5 ms y calcula su promedio aritmético antes de la conversión a porcentaje.

**¿Cuántos sectores gestiona la plataforma y quiénes son los responsables?**  
El sistema gestiona 5 sectores (Invernaderos 1 al 5) administrados por los 5 integrantes del **GRUPO 3**: Diego Charry (Sector 1 - Administrador), Angel Villalobos (Sector 2 - Agrónomo), Adelfo Freyle (Sector 3 - Operador), Juan Quintero (Sector 4 - Técnico IoT) y Juan Figueroa (Sector 5 - Visualizador).

**¿Qué motor de base de datos se utiliza y cómo se gestionan las conexiones?**  
Se utiliza PostgreSQL Serverless alojado en Neon Cloud, gestionado a través de `psycopg2.pool.ThreadedConnectionPool` (1 a 10 conexiones persistentes) para optimizar tiempos de respuesta y escalabilidad.

**¿Por qué los informes PDF mostraban registros vacíos y cómo se corrigió?**  
El componente `QPdfWriter` utiliza 1200 DPI por defecto. El uso previo de tamaños en píxeles (`font-size: 10px`) reducía el texto a una altura de 0.2 mm. Se solucionó configurando `writer.setResolution(300)` y migrando todas las reglas de estilo HTML a unidades en puntos (`pt`), con fuentes `Segoe UI` / `Arial` y márgenes optimizados de 10 mm.

---

## Glosario Técnico Especializado

- **ADC (Analog-to-Digital Converter):** Conversor analógico a digital de 12 bits del ESP32 que transforma voltaje continuo (0 a 3.3V) en enteros de 0 a 4095.
- **API REST:** Interfaz de comunicación cliente-servidor sobre HTTP/HTTPS utilizada para conectar el ESP32 y el Dashboard con la nube.
- **Connection Pooling:** Técnica que mantiene un grupo de conexiones activas a PostgreSQL para reutilizarlas en cada solicitud sin reabrir sockets TCP.
- **ESP32:** SoC de bajo consumo con Wi-Fi y Bluetooth diseñado por Espressif, utilizado como nodo controlador de campo.
- **FastAPI:** Framework web asíncrono para Python con validación estricta de esquemas JSON mediante Pydantic.
- **I2C:** Bus serial de 2 hilos (SDA/SCL) utilizado para gobernar la pantalla LCD 16x2 a 400 kHz en dirección `0x27`.
- **MicroPython:** Entorno de ejecución ligero de Python 3 diseñado para microcontroladores.
- **MVC (Modelo-Vista-Controlador):** Patrón arquitectónico que divide la aplicación en gestión de datos (`modelo.py`), componentes gráficos (`vista.py`) y lógica de negocio (`controlador.py`).
- **Neon Cloud:** Plataforma de bases de datos PostgreSQL serverless que escala recursos dinámicamente según la demanda.
- **PyQt6:** Binding de Python para Qt 6 utilizado en el desarrollo de la aplicación de escritorio.
- **QPdfWriter:** Dispositivo de pintado vectorial de Qt para exportar documentos PDF con control de resolución, tamaños y márgenes.
- **QThread:** Mecanismo de Qt para ejecutar procesos en hilos secundarios en paralelo con el bucle de eventos principal.
- **RAG (Retrieval-Augmented Generation):** Técnica de IA generativa que recupera fragmentos de conocimiento específicos para alimentar el contexto de modelos como Qwen 2.5B Instruct.
- **RBAC (Role-Based Access Control):** Control de acceso basado en roles que define los privilegios de los usuarios (`ADMINISTRADOR`, `AGRONOMO`, `OPERADOR`, `TECNICO_IOT`, `VISUALIZADOR`).
- **Sobremuestreo (Oversampling):** Muestreo reiterado de una señal analógica para promediar las lecturas y suprimir ruido electromagnético.
- **Wokwi:** Plataforma web de simulación de circuitos embebidos para validar hardware ESP32 y código MicroPython.

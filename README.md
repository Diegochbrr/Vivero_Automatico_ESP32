# 🌱 SmartVivero IoT — Sistema Automatizado de Riego y Telemetría con ESP32

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon_Cloud-336791?logo=postgresql&logoColor=white)](https://neon.tech/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![MicroPython](https://img.shields.io/badge/MicroPython-ESP32-darkgreen?logo=espressif&logoColor=white)](https://micropython.org/)
[![Render](https://img.shields.io/badge/Render-Deployed-46E3B7?logo=render&logoColor=white)](https://vivero-automatico-esp32.onrender.com)

**SmartVivero IoT** es una solución integral y profesional de agricultura de precisión desarrollada por el **GRUPO 3**. El sistema automatiza el monitoreo de humedad de suelo, el control de reservorios de agua y la activación de bombas de riego en tiempo real, integrando nodos IoT (**ESP32 / Wokwi**), un backend en la nube (**FastAPI + Neon PostgreSQL**) y un panel de control de escritorio (**PyQt6**) con control de acceso basado en roles (RBAC) y generación de informes técnicos oficiales en PDF.

---

## 👥 Integrantes del Proyecto — GRUPO 3

| Nombre | Correo Institucional | Rol en el Sistema | Sector Asignado |
| :--- | :--- | :---: | :--- |
| **Diego Charry** | `diego.charry@vivero.com` | **`ADMINISTRADOR`** | **Sector 1:** Invernadero 1 (Orquídeas y Suculentas) |
| **Angel Villalobos** | `angel.villalobos@vivero.com` | **`AGRONOMO`** | **Sector 2:** Invernadero 2 (Hortalizas y Tomates) |
| **Adelfo Freyle** | `adelfo.freyle@vivero.com` | **`OPERADOR`** | **Sector 3:** Invernadero 3 (Semilleros y Flores) |
| **Juan Quintero** | `juan.quintero@vivero.com` | **`TECNICO_IOT`** | **Sector 4:** Invernadero 4 (Laboratorio Experimental IoT) |
| **Juan Figueroa** | `juan.figueroa@vivero.com` | **`VISUALIZADOR`** | **Sector 5:** Invernadero 5 (Plantas Ornamentales) |

> 🔑 **Contraseña inicial predeterminada:** `admin123`

---

## 📐 Arquitectura General del Sistema

```mermaid
graph TD
    subgraph "Capa Física / Simulación IoT (Wokwi)"
        ESP32[ESP32 MicroPython]
        SensorHum[Sensor Humedad Capacitivo ADC D34]
        SensorNivel[Sensor Flotador / Nivel D18]
        Bomba[Relé / Bomba de Agua D2]
        BtnManual[Botón de Riego Manual D19]
        LCD[Pantalla LCD I2C 16x2 D21/D22]
        
        SensorHum --> ESP32
        SensorNivel --> ESP32
        BtnManual --> ESP32
        ESP32 --> Bomba
        ESP32 --> LCD
    end

    subgraph "Capa Cloud & Backend (Render + Neon)"
        API[FastAPI REST API / Uvicorn]
        DB[(Neon Serverless PostgreSQL)]
        
        API <--> DB
    end

    subgraph "Capa de Gestión / App de Escritorio (PyQt6)"
        DesktopApp[Panel de Control SmartVivero]
        Dashboard[Dashboard en Vivo]
        Charts[Análisis Gráfico Matplotlib]
        Settings[Configuración de Umbrales]
        Users[Personal & Roles RBAC]
        Reports[Generador PDF Oficial]
        
        DesktopApp --> Dashboard
        DesktopApp --> Charts
        DesktopApp --> Settings
        DesktopApp --> Users
        DesktopApp --> Reports
    end

    ESP32 -- "HTTP POST (Telemetría / Alertas) & GET (Comandos/Sincronización)" --> API
    DesktopApp -- "HTTP REST (X-API-Key)" --> API
```

---

## 🔌 Hardware y Conexiones de Pines (ESP32)

| Componente | Tipo | Pin ESP32 | Función |
| :--- | :---: | :---: | :--- |
| **Sensor de Humedad** | Entrada Analógica | `GPIO 34` (ADC1_CH6) | Lectura capacitiva de humedad de suelo (0 - 4095) |
| **Sensor de Nivel de Agua** | Entrada Digital | `GPIO 18` (PULL_UP) | Detección de reservorio vacío / protección anti-desborde |
| **Botón de Riego Manual** | Entrada Digital | `GPIO 19` (PULL_UP) | Forzado de riego físico en campo |
| **Relé de la Bomba** | Salida Digital | `GPIO 2` | Control de encendido/apagado de electrobomba |
| **LED de Alerta Crítica** | Salida Digital | `GPIO 4` | Notificación visual de falta de agua |
| **Pantalla LCD 16x2 (I2C)** | I2C (SDA) | `GPIO 21` | Transmisión de datos de telemetría y sector activo |
| **Pantalla LCD 16x2 (I2C)** | I2C (SCL) | `GPIO 22` | Señal de reloj I2C (Dirección: `0x27`) |

---

## 🛡️ Control de Acceso Basado en Roles (RBAC)

La aplicación de escritorio cuenta con un motor de permisos estricto que ajusta la interfaz de usuario en tiempo real según el usuario autenticado:

| Funcionalidad | `ADMINISTRADOR` | `AGRONOMO` | `OPERADOR` / `TECNICO_IOT` | `VISUALIZADOR` | `INVITADO` *(Inicio)* |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Monitoreo en Tiempo Real (Dashboard & Gráficas)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Exportar Informes Técnicos PDF** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Control Manual (Forzar Riego Remoto)** | ✅ | ✅ | ✅ | 🔒 *Bloqueado* | 🔒 *Bloqueado* |
| **Ajuste y Guardado de Umbrales de Riego** | ✅ | ✅ | 🔒 *Solo Lectura* | 🔒 *Solo Lectura* | 🔒 *Solo Lectura* |
| **Eliminar Mediciones y Alertas** | ✅ | 🔒 *Bloqueado* | 🔒 *Bloqueado* | 🔒 *Bloqueado* | 🔒 *Bloqueado* |
| **Gestión de Personal (Crear/Editar/Eliminar)** | ✅ | 🔒 *Solo Consulta* | 🔒 *Solo Consulta* | 🔒 *Solo Consulta* | 🔒 *Solo Consulta* |

---

## 🖥️ Características de la Aplicación de Escritorio

1. **Barra Superior Global Permanente:**
   * **Selector de Sector Dinámico:** Conmuta automáticamente métricas, historial, umbrales y gráficos al sector deseado.
   * **Ficha del Encargado:** Muestra nombre, rol, correo y cultivo del área activa.
   * **Cambio de Cuenta Interactivo:** Modal para alternar perfiles o autenticarse mediante correo y contraseña.
2. **Dashboard en Tiempo Real:**
   * Tarjetas métricas de **Humedad Actual (%)** y **Nivel ADC Crudo**.
   * Control manual de **Forzar Riego** con selector de duración en segundos.
   * Tablas en vivo de **Últimas Alertas** e **Historial Completo** con casillas checkbox y buscadores instantáneos.
3. **Análisis Gráfico en Vivo (Matplotlib):**
   * Gráfico de evolución temporal de humedad con líneas de corte (umbrales mínimo y máximo).
   * Histograma de distribución de lecturas de suelo.
4. **Gestión de Personal y Control de Roles:**
   * Registro y edición de miembros del equipo con contraseña y correo opcionales.
   * Selección individual exclusiva mediante casillas checkbox para máxima seguridad.
5. **Generador de Informes Técnicos Oficiales en PDF:**
   * Exportación mediante `QPdfWriter` nativo de Qt (cero bloqueos ni dependencias de drivers de impresión de Windows).
   * Reporte ejecutivo que incluye: Membrete del **GRUPO 3**, datos del sector y auditor, resumen de KPIs y estadísticas, historial de telemetría, registro de incidentes y recuadros de firma formal.
6. **Selector de Tema Visual:**
   * Modo Oscuro (*Cyberpunk/Slate Glassmorphism*) y Modo Claro con soporte de persistencia.

---

## 🌐 Endpoints de la API REST (FastAPI)

URL de Producción: `https://vivero-automatico-esp32.onrender.com`  
Documentación Interactiva Swagger: `https://vivero-automatico-esp32.onrender.com/docs`

### 📡 Telemetría & Alertas
* `POST /api/v1/mediciones`: Registro de lecturas analógicas y calculadas desde el ESP32.
* `GET /api/v1/mediciones`: Historial general de telemetría.
* `GET /api/v1/mediciones/sector/{id_sector}`: Historial filtrado por sector.
* `DELETE /api/v1/mediciones/{id_lectura}`: Eliminación de lectura (requiere API Key).
* `POST /api/v1/alertas`: Registro de alertas de nivel de agua crítico.
* `GET /api/v1/alertas`: Consulta de alertas activas.
* `DELETE /api/v1/alertas/{id_alerta}`: Eliminación de alerta.

### ⚙️ Umbrales & Comandos ESP32
* `GET /api/v1/umbrales/{id_sector}`: Consulta de umbrales activos del sector.
* `PUT /api/v1/umbrales/{id_sector}`: Modificación de umbrales (Humedad Mín/Máx, Tiempo de Bomba).
* `GET /api/v1/comandos/{id_sector}`: Polling consultado por el ESP32 cada 5 segundos.
* `POST /api/v1/comandos/forzar-riego/{id_sector}`: Encola orden de riego manual forzado.
* `DELETE /api/v1/comandos/forzar-riego/{id_sector}`: Confirmación (ACK) de ejecución enviada por el ESP32.
* `GET /api/v1/sistema/sector-activo`: Consulta del sector activo en el sistema.
* `PUT /api/v1/sistema/sector-activo/{id_sector}`: Sincronización en tiempo real del sector activo con Wokwi.

### 👥 Sectores, Usuarios & Autenticación
* `GET /api/v1/sectores`: Lista de sectores y sus encargados asignados.
* `PUT /api/v1/sectores/{id_sector}`: Actualización de datos del sector y responsable.
* `GET /api/v1/usuarios`: Lista de personal registrado.
* `POST /api/v1/usuarios`: Creación de nuevo usuario.
* `PUT /api/v1/usuarios/{id_usuario}`: Edición de usuario (contraseña opcional).
* `DELETE /api/v1/usuarios/{id_usuario}`: Eliminación de usuario.
* `POST /api/v1/auth/login`: Autenticación de credenciales.

---

## 🚀 Instalación y Puesta en Marcha

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Diegochbrr/Vivero_Automatico_ESP32.git
cd Vivero_Automatico_ESP32
```

### 2. Crear y Activar Entorno Virtual
```bash
# En Windows (PowerShell)
python -m venv env
.\env\Scripts\Activate.ps1
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno (`.env`)
Crea un archivo `.env` en la raíz del proyecto tomando como base `.env.example`:
```ini
DATABASE_URL=postgresql://usuario:contrasena@ep-ejemplo.us-east-2.aws.neon.tech/neondb?sslmode=require
API_KEY=sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d
PORT=8000
```

### 5. Ejecutar la API Localmente
```bash
uvicorn main_api_vivero:app --reload --port 8000
```

### 6. Ejecutar la Aplicación de Escritorio
```bash
python main.py
```

### 7. Ejecutar la Simulación en Wokwi
1. Abre [Wokwi ESP32 Simulator](https://wokwi.com/).
2. Carga los archivos [`ESP32/diagram.json`](ESP32/diagram.json) y [`ESP32/main.py`](ESP32/main.py).
3. Asegúrate de incluir las librerías [`ESP32/lcd_api.py`](ESP32/lcd_api.py) y [`ESP32/machine_i2c_lcd.py`](ESP32/machine_i2c_lcd.py).
4. Inicia la simulación; el ESP32 se conectará a la WiFi de Wokwi y se sincronizará automáticamente con la API en la nube.

---

## 📄 Licencia y Créditos
Proyecto desarrollado con fines académicos y de demostración técnica por el **GRUPO 3** para el sistema de control automatizado de invernaderos e infraestructura IoT con ESP32.

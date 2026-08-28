# Descripción General del Proyecto: Vivero Automático con ESP32

## Nombre del Proyecto
**SmartVivero IoT** — Sistema Automatizado de Telemetría ESP32 y Control de Cultivos

## Autores y Certificación — GRUPO 3
El proyecto fue diseñado, desarrollado y certificado por el **GRUPO 3**, compuesto por 5 integrantes con responsabilidades técnicas y operativas:

| Integrante | Correo Institucional | Rol en el Sistema | Sector Asignado | Cultivo Asignado |
| :--- | :--- | :---: | :--- | :--- |
| **Diego Charry** | `diego.charry@vivero.com` | `ADMINISTRADOR` | **Sector 1:** Invernadero 1 (Principal) | Orquídeas y Suculentas |
| **Angel Villalobos** | `angel.villalobos@vivero.com` | `AGRONOMO` | **Sector 2:** Invernadero 2 (Cultivo Agrónomo) | Hortalizas y Tomates |
| **Adelfo Freyle** | `adelfo.freyle@vivero.com` | `OPERADOR` | **Sector 3:** Invernadero 3 (Riego Automatizado) | Semilleros y Flores |
| **Juan Quintero** | `juan.quintero@vivero.com` | `TECNICO_IOT` | **Sector 4:** Invernadero 4 (Laboratorio IoT) | Cultivo Experimental |
| **Juan Figueroa** | `juan.figueroa@vivero.com` | `VISUALIZADOR` | **Sector 5:** Invernadero 5 (Supervisión) | Plantas Ornamentales |

## Objetivo General
Desarrollar un sistema de agricultura de precisión integral y automatizado para invernaderos que monitoree en tiempo real la humedad del suelo y los niveles del reservorio de agua, controle de forma autónoma electrobombas de riego, registre históricos en bases de datos relacionales en la nube y proporcione una interfaz gráfica de escritorio con control de acceso por roles (RBAC) y generación de informes técnicos oficiales en PDF.

## Objetivos Específicos
- Monitorear la humedad del suelo de forma continua mediante sensores capacitivos con sobremuestreo para suprimir ruidos.
- Controlar el encendido/apagado de electrobombas mediante relés según umbrales de humedad configurables por sector.
- Detectar niveles críticos de agua en los reservorios con switches de flotador para proteger las bombas contra trabajo en seco.
- Transmitir telemetría y alertas a una API REST en la nube cada 5 segundos mediante conexión Wi-Fi.
- Gestionar 5 sectores productivos diferenciados con parámetros agronómicos específicos y asignación de personal.
- Visualizar datos en vivo, históricos, análisis gráficos y estadísticas desde una aplicación de escritorio desarrollada en PyQt6.
- Implementar un motor de seguridad RBAC con 5 perfiles de usuario y credenciales protegidas.
- Generar informes técnicos ejecutivos en formato PDF en alta definición (300 DPI) con `QPdfWriter` nativo.

## Arquitectura General del Sistema (3 Capas)

### 1. Capa de Hardware (ESP32 + Sensores + Actuadores)
- **Microcontrolador:** ESP32 DevKit V1 programado en MicroPython y simulado en Wokwi.
- **Sensor de Humedad Capacitivo:** Pin analógico ADC1 `GPIO34` (0 a 4095).
- **Sensor de Nivel de Agua:** Switch flotador digital en `GPIO18` con resistencia PULL_UP interna.
- **Bomba de Agua:** Relé electromecánico conectado a `GPIO2` (LED Verde testigo).
- **Alerta Visual:** LED Rojo de advertencia en `GPIO4`.
- **Botón de Riego Manual:** Pulsador en `GPIO19` (PULL_UP).
- **Pantalla LCD 16x2:** Comunicación I2C (SDA en `GPIO21`, SCL en `GPIO22`, dirección `0x27`).

### 2. Capa de Backend (API REST en la Nube)
- **Framework:** FastAPI (Python 3.10+).
- **Base de Datos:** PostgreSQL Serverless en Neon Cloud.
- **Conectividad:** Pool de conexiones multi-hilo (`psycopg2.pool.ThreadedConnectionPool`).
- **Hosting:** Render.com (`https://vivero-automatico-esp32.onrender.com`).
- **Seguridad:** Autenticación por cabecera `X-API-Key`.

### 3. Capa de Aplicación de Escritorio (Dashboard)
- **Framework:** PyQt6 con patrón de arquitectura MVC.
- **Refresco en Vivo:** Hilo secundario `QThread` (`HiloActualizacionDatos`) con sondeo cada 3 segundos.
- **Visualización Gráfica:** Matplotlib integrado con series de tiempo e histogramas.
- **Reportes:** Generador PDF con `QPdfWriter` a 300 DPI.
- **Autenticación:** Control de sesión y roles RBAC con cambio interactivo de cuentas.

## Tecnologías Utilizadas

| Tecnología | Rol en el Proyecto |
| :--- | :--- |
| **MicroPython** | Firmware del microcontrolador ESP32 |
| **FastAPI** | Backend y API REST en la nube |
| **PostgreSQL (Neon Cloud)** | Base de datos relacional serverless |
| **psycopg2 (Connection Pool)** | Gestor de conexiones eficientes a la base de datos |
| **Pydantic** | Validación y serialización de esquemas JSON |
| **PyQt6** | Interfaz gráfica de escritorio (Dashboard) |
| **Matplotlib** | Renderizado de gráficas estadísticas de telemetría |
| **QPdfWriter / QTextDocument** | Generación de informes técnicos en PDF |
| **Render.com** | Plataforma de despliegue continuo de la API |
| **Wokwi Simulator** | Simulación de hardware y topología de circuitos |

## Sectores Gestionados por el Sistema
1. **Sector 1 (Principal):** Invernadero 1 — Orquídeas y Suculentas (Encargado: Diego Charry).
2. **Sector 2 (Cultivo Agrónomo):** Invernadero 2 — Hortalizas y Tomates (Encargado: Angel Villalobos).
3. **Sector 3 (Riego Automatizado):** Invernadero 3 — Semilleros y Flores (Encargado: Adelfo Freyle).
4. **Sector 4 (Laboratorio IoT):** Invernadero 4 — Cultivo Experimental (Encargado: Juan Quintero).
5. **Sector 5 (Supervisión):** Invernadero 5 — Plantas Ornamentales (Encargado: Juan Figueroa).

## Identificadores del Sistema
- **Sensor de Humedad:** `SEN-CAP-S01`
- **Actuador de Bomba (Relé):** `REL-BOM-01`
- **Sensor de Flotador:** `Sensor Flotador`
- **Clave API Pública/Privada:** `sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d`

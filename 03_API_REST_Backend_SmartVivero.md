# API REST Backend — SmartVivero

## Descripción General
El backend de SmartVivero IoT es una API REST asíncrona de alto rendimiento desarrollada en Python con el framework FastAPI. Actúa como el núcleo central de comunicación entre los nodos de campo ESP32, la base de datos relacional serverless y la aplicación de escritorio PyQt6.

## Información de Despliegue y Conectividad
- **Hosting en Producción:** Render.com
- **URL Base:** `https://vivero-automatico-esp32.onrender.com`
- **Documentación Interactiva (Swagger/OpenAPI):** `https://vivero-automatico-esp32.onrender.com/docs`
- **Versión de la API:** `1.0.0`
- **Servidor ASGI:** Uvicorn con recarga automática y workers asíncronos
- **CORS:** Habilitado para todos los orígenes (`allow_origins=["*"]`)

## Mecanismo de Autenticación
Los endpoints protegidos exigen la presencia de una API Key en los encabezados HTTP:
- **Header:** `X-API-Key`
- **Valor Válido:** `sv_live_8b3a7f9d2e1c4a5b6f8e7d9c0b1a2f3d`
- **Respuesta ante fallo:** `HTTP 403 Forbidden` (`{"detail": "API Key inválida o no proporcionada"}`)

## Base de Datos y Connection Pooling
- **Motor:** PostgreSQL
- **Proveedor:** Neon Cloud (PostgreSQL Serverless)
- **Gestor de Conexiones:** `psycopg2.pool.ThreadedConnectionPool` configurado con mínimo 1 y máximo 10 conexiones simultáneas reutilizables.
- **Ventaja Técnica:** Elimina la sobrecarga de apertura y cierre de conexiones TCP (handshake TLS) en cada petición del ESP32 o de la interfaz de usuario.
- **Acceso a Datos:** Patrón Repositorio (`ViveroRepository`) con consultas SQL directas y cursores tipados `RealDictCursor`.

---

## Tablas de la Base de Datos Relacional

### 1. Tabla: `lecturas_humedad`
Almacena la serie temporal de mediciones enviadas por los sensores de suelo.

| Campo | Tipo SQL | Restricción | Descripción |
| :--- | :--- | :---: | :--- |
| `id_lectura` | `SERIAL` | PK | Identificador único autoincremental de la muestra. |
| `id_sensor` | `VARCHAR(50)` | NOT NULL | Identificador del sensor (ej. `SEN-CAP-S01`). |
| `id_sector` | `INTEGER` | NOT NULL | Identificador del sector auditado (1 al 5). |
| `humedad_porcentaje` | `NUMERIC(5,2)` | NOT NULL | Porcentaje de humedad calculado (0.00% a 100.00%). |
| `valor_adc_crudo` | `INTEGER` | NOT NULL | Lectura analógica cruda del ADC (0 a 4095). |
| `fecha_hora` | `TIMESTAMP` | DEFAULT NOW() | Estampa de tiempo generada automáticamente. |

### 2. Tabla: `alertas_nivel_agua`
Registra los incidentes de falta de agua detectados en los reservorios.

| Campo | Tipo SQL | Restricción | Descripción |
| :--- | :--- | :---: | :--- |
| `id_alerta` | `SERIAL` | PK | Identificador único de la alerta. |
| `id_sector` | `INTEGER` | NOT NULL | Sector donde ocurrió la contingencia. |
| `nivel_detectado` | `VARCHAR(50)` | NOT NULL | Nivel registrado (ej. `CRITICO_VACIO`). |
| `bomba_bloqueada` | `BOOLEAN` | DEFAULT TRUE | Estado de protección automática de la electrobomba. |
| `observacion` | `TEXT` | NULL | Información adicional sobre el evento. |
| `fecha_hora` | `TIMESTAMP` | DEFAULT NOW() | Marca de tiempo del registro. |

### 3. Tabla: `umbrales_configuracion`
Almacena los parámetros de control operativo y agronómico por sector.

| Campo | Tipo SQL | Restricción | Descripción |
| :--- | :--- | :---: | :--- |
| `id_sector` | `INTEGER` | PK | Sector regulado (1 a 5). |
| `humedad_min_on` | `NUMERIC(5,2)` | DEFAULT 35.0 | Humedad por debajo de la cual se activa el riego. |
| `humedad_max_off` | `NUMERIC(5,2)` | DEFAULT 70.0 | Humedad por encima de la cual se detiene el riego. |
| `tiempo_max_riego_seg` | `INTEGER` | DEFAULT 180 | Límite de seguridad anti-desborde para la bomba. |
| `id_usuario_modifica` | `INTEGER` | NULL | Usuario que realizó el último ajuste. |
| `actualizado_en` | `TIMESTAMP` | DEFAULT NOW() | Fecha y hora del cambio de configuración. |

### 4. Tabla: `sectores`
Cataloga las áreas productivas y sus ingenieros/técnicos responsables.

| Campo | Tipo SQL | Restricción | Descripción |
| :--- | :--- | :---: | :--- |
| `id_sector` | `INTEGER` | PK | Número de sector (1 a 5). |
| `nombre_sector` | `VARCHAR(100)` | NOT NULL | Nombre comercial/operativo del invernadero. |
| `encargado_nombre` | `VARCHAR(100)` | NOT NULL | Nombre del integrante del Grupo 3 asignado. |
| `encargado_correo` | `VARCHAR(100)` | NOT NULL | Correo de contacto institucional. |
| `encargado_rol` | `VARCHAR(50)` | NOT NULL | Cargo o rol del responsable. |
| `tipo_cultivo` | `VARCHAR(100)` | NOT NULL | Variedad vegetal sembrada en el sector. |
| `descripcion` | `TEXT` | NULL | Resumen técnico del área. |

### 5. Tabla: `usuarios`
Gestiona el personal del sistema, roles RBAC y credenciales.

| Campo | Tipo SQL | Restricción | Descripción |
| :--- | :--- | :---: | :--- |
| `id_usuario` | `SERIAL` | PK | Identificador único de usuario. |
| `nombre` | `VARCHAR(100)` | NOT NULL | Nombre completo. |
| `correo` | `VARCHAR(100)` | UNIQUE | Correo electrónico de acceso. |
| `rol` | `VARCHAR(50)` | NOT NULL | Perfil (`ADMINISTRADOR`, `AGRONOMO`, etc.). |
| `password_hash` | `VARCHAR(255)` | NOT NULL | Contraseña cifrada con hash seguro (SHA-256). |
| `creado_en` | `TIMESTAMP` | DEFAULT NOW() | Fecha de registro. |

---

## Catálogo de Endpoints de la API REST

### Diagnóstico y Disponibilidad
- `GET /`: Comprueba que el microservicio está en línea.
- `GET /health`: Valida la conectividad con PostgreSQL en Neon Cloud.

### Telemetría de Suelo (Lecturas de Humedad)
- `POST /api/v1/mediciones`: Inserta una nueva medición proveniente del ESP32.
  - Body: `{"id_sensor": "SEN-CAP-S01", "id_sector": 1, "humedad_porcentaje": 45.2, "valor_adc_crudo": 1850}`
- `GET /api/v1/mediciones`: Obtiene el historial general de telemetría.
- `GET /api/v1/mediciones/sector/{id_sector}?limit=50`: Obtiene las mediciones recientes de un sector específico.
- `DELETE /api/v1/mediciones/{id_lectura}`: Elimina una lectura puntual de la base de datos (requiere permisos de Administrador).

### Monitoreo de Reservorios y Alertas
- `POST /api/v1/alertas`: Registra una alerta de nivel de agua crítico enviada por el ESP32.
- `GET /api/v1/alertas?limit=20`: Consulta las alertas activas o históricas.
- `DELETE /api/v1/alertas/{id_alerta}`: Elimina un registro de alerta específico.

### Umbrales de Riego y Calibración
- `GET /api/v1/umbrales/{id_sector}`: Consulta los umbrales configurados para el sector.
- `PUT /api/v1/umbrales/{id_sector}`: Actualiza los umbrales de humedad y tiempo máximo de bomba.

### Comandos de Control Remoto y Sincronización
- `GET /api/v1/comandos/{id_sector}`: Polling consultado por el ESP32 para verificar órdenes pendientes.
- `POST /api/v1/comandos/forzar-riego/{id_sector}`: Encola una orden de forzar riego manual remoto con duración en segundos.
- `DELETE /api/v1/comandos/forzar-riego/{id_sector}`: Notificación de confirmación (ACK) enviada por el ESP32 tras cumplir el riego.
- `GET /api/v1/sistema/sector-activo`: Devuelve el sector activo seleccionado globalmente.
- `PUT /api/v1/sistema/sector-activo/{id_sector}`: Establece el sector activo para sincronizar en tiempo real el simulador Wokwi.

### Gestión de Sectores, Personal y Autenticación
- `GET /api/v1/sectores`: Lista los 5 sectores y sus datos agronómicos.
- `PUT /api/v1/sectores/{id_sector}`: Actualiza los datos de un sector y su encargado.
- `GET /api/v1/usuarios`: Lista los usuarios y sus roles asignados.
- `POST /api/v1/usuarios`: Registra un nuevo usuario con rol y contraseña.
- `PUT /api/v1/usuarios/{id_usuario}`: Modifica los datos de un usuario (contraseña opcional).
- `DELETE /api/v1/usuarios/{id_usuario}`: Elimina un usuario del sistema.
- `POST /api/v1/auth/login`: Autentica credenciales (correo y contraseña).

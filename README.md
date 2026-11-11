# 🔧 Plataforma Full-Stack de Gestión de Taller Mecánico y Telemetría 3D

Sistema integral para la administración operativa de talleres mecánicos automotrices y seguimiento vehicular en tiempo real. Combina un backend transaccional en **Django 6** con un portal interactivo **WebGL / Three.js** que permite a los clientes inspeccionar el estado técnico de su vehículo en 3D, aprobar presupuestos en línea y recibir alertas automatizadas.

---

## 🚀 Demo en Producción (Live Deploy)

* **Portal 3D del Cliente (Acceso Público):** [https://taller-mecanico-frod.onrender.com/](https://taller-mecanico-frod.onrender.com/)
* **Centro de Operaciones del Mecánico (Dashboard):** [https://taller-mecanico-frod.onrender.com/panel-taller/](https://taller-mecanico-frod.onrender.com/panel-taller/)
* **Panel Administrativo de Base de Datos:** [https://taller-mecanico-frod.onrender.com/admin/](https://taller-mecanico-frod.onrender.com/admin/)

### Patentes de Prueba para el Visor 3D:
* `KBH106` — Peugeot 207 XS Compact (**Carrocería 3D Hatchback** · Fase 4: En Reparación)
* `AF450XZ` — Toyota Hilux SRX (**Carrocería 3D Pick-up** · Fase 2: En Diagnóstico)
* `AD892KL` — Renault Duster 4WD (**Carrocería 3D SUV** · Fase 3: Esperando Repuestos)
* `AE123BC` — Volkswagen Vento TSI (**Carrocería 3D Sedán** · Fase 5: Listo para retirar)

---

## 🛡️ Arquitectura de Seguridad y Prevención de Vulnerabilidades (OWASP)

El proyecto fue diseñado aplicando principios de **Seguridad por Diseño (Security by Design)** y mitigación activa de vectores modernos de ataque:

1. **Prevención de Inyección SQL (SQLi):**
   * Prohibición absoluta de consultas crudas concatenadas. Todas las interacciones con la base de datos utilizan el **ORM de Django con consultas parametrizadas (Prepared Statements)**, separando estrictamente las instrucciones SQL de los datos provistos por el usuario.
   * Normalización y validación por expresiones regulares (`/^[A-Z]{3}\d{3}|[A-Z]{2}\d{3}[A-Z]{2}$/`) del formato de patentes Mercosur y estándar antes de consultar el backend.
2. **Prevención de Cross-Site Scripting (XSS) en el Motor 3D:**
   * Sanitización explícita en el cliente mediante escape de entidades HTML y uso estricto de `.textContent` al renderizar etiquetas dinámicas y *hotspots* provenientes de la API REST.
3. **Control de Acceso Basado en Roles (RBAC):**
   * Restricción mediante el decorador `@staff_member_required` en todas las vistas operativas (`/panel-taller/`, cambio de fases y exportación de reportes PDF).
4. **Hardening de Producción y Gestión de Secretos:**
   * Aislamiento de credenciales sensibles (`SECRET_KEY`, `DEBUG`, `DATABASE_URL`) mediante variables de entorno (`.env` / `python-dotenv`) excluidas del control de versiones vía `.gitignore`.
   * Cabeceras de seguridad activas (`CSRF_TRUSTED_ORIGINS`, `XFrameOptionsMiddleware`, `SecurityMiddleware`).

---

## ✨ Módulos Principales Implementados

### 1. Portal 3D Interactivo con Scrollytelling (Three.js + GSAP)
* **Generación Dinámica por Segmento Vehicular:** Renderizado procedural adaptativo y soporte para modelos `.glb` con normalización automática de escala (`THREE.Box3`) según el vehículo consultado (*Hatchback, Pick-up, SUV o Sedán*).
* **Sistema de 8 Hotspots Técnicos:** Anclas tridimensionales sobre *Motor, Frenos ABS, Suspensión, Electrónica OBC, Batería, Transmisión y Escape* con rotación automática de cámara hacia el subsistema seleccionado.
* **Recorrido de 5 Etapas por Scroll:** Pista interactiva con GSAP ScrollTrigger y degradación elegante (*graceful degradation*) para dispositivos con `prefers-reduced-motion`.

### 2. Aprobación de Presupuestos Online (Lado Cliente)
* Endpoint REST (`POST /api/presupuesto/`) que permite al cliente aprobar el presupuesto detallado o solicitar revisión de costos en tiempo real sin llamadas telefónicas, actualizando instantáneamente el estado en el tablero del taller.

### 3. Sistema de Alertas y Comunicación Multicanal
* Suscripción de avisos desde el portal del cliente (`POST /api/notificar/`).
* Generación automática de enlaces profundos (*deep links*) hacia **WhatsApp** desde el Centro de Operaciones con el resumen de fase, presupuesto y acceso directo pre-cargado (`/?patente=XXXX`).
* Disparo automático de notificaciones por correo electrónico (`send_mail`) ante cambios de fase operativa.

### 4. Dashboard Analítico y Exportación Documental (Chart.js + WeasyPrint)
* **KPIs en Tiempo Real:** Ingresos del día, órdenes en box, facturación mensual, ticket promedio, tasa de aprobación online y semáforo de repuestos en stock crítico.
* **Visualización de Datos:** Gráficos interactivos de distribución de flota por fases operativas (Doughnut Chart) y volumen por tipo de carrocería (Bar Chart) implementados con **Chart.js**.
* **Generación de Órdenes en PDF:** Exportación instantánea de órdenes de trabajo en formato PDF listas para impresión mediante **WeasyPrint**.

---

## 📦 Estrategia de Persistencia e Inyección de Datos (Database Seeding)

Dado que el servicio en la nube opera sobre contenedores efímeros (*stateless*), se implementó un pipeline de aprovisionamiento idempotente que garantiza la disponibilidad permanente del entorno de demostración:

* **`crear_admin.py`:** Aprovisiona de manera automatizada el superusuario administrativo si no existe en la instancia.
* **`poblar_taller.py`:** Ejecuta mediante `update_or_create` la inyección controlada de repuestos con umbrales de stock crítico y una flota de 4 vehículos representativos en distintas fases operativas.

**Pipeline de compilación en Render (`Build Command`):**
```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python crear_admin.py && python poblar_taller.py
# 📘 Proyecto: Automatización de Precios Industrial (Bertual API)

Este documento establece las normas fundamentales de arquitectura, seguridad y desarrollo para este proyecto.

## ⚖️ Reglas de Oro (Business Rules)

1.  **Protección de Margen (CRÍTICO):** NUNCA se debe usar el campo `precio_resale` (con descuento) para reportes públicos. Siempre usar el campo `precio` (PVP Final).
2.  **Origen de Datos:** Usar siempre el campo `Precio` bruto de la API de Bertual.
3.  **Mandato de TDD:** Toda nueva funcionalidad o corrección debe incluir pruebas en `tests/`.

## 📊 Estrategia de Ingesta y Notificación (Ingeniería de Datos)

1.  **Ingesta de Alta Frecuencia:** El script debe ejecutarse varias veces al día para capturar telemetría. Estas ejecuciones deben ser **silenciosas** (flag `--silent`), limitándose a registrar métricas y actualizar el estado de los datos.
2.  **Acumulación Diaria:** Los cambios detectados durante el día deben guardarse en un buffer (`status/daily_accum.json`) para ser procesados al final de la jornada.
3.  **Reporte Ejecutivo Nocturno:** Se enviará un único reporte diario a Telegram. Este reporte incluirá:
    *   **Resumen IA:** Análisis de tendencias de precios y productos clave del día.
    *   **Análisis de Ventana de Carga:** El LLM analizará `status/metrics.jsonl` para determinar a qué horas el proveedor (Electronic Haedo) realiza sus cargas, permitiendo optimizar los horarios de los crons.
    *   **Estado de Infraestructura:** Informe de disponibilidad de los nodos y latencia de la API.

## 🏗️ Arquitectura del Sistema

-   **Métricas:** Telemetría detallada en `status/metrics.jsonl`.
-   **Heartbeat:** Actualización de `status/heartbeat.json` para monitoreo de CI/CD.
-   **Silent Mode:** Capacidad de operar sin disparar alertas ni llamadas a la IA para optimizar costos y reducir ruido.

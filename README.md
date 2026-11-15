# Climate Planner

Programación semanal **por temporadas** (Invierno / Entretiempo / Verano) para cualquier entidad `climate` de Home Assistant: Daikin, Vaillant, termostatos, etc. Se gestiona desde un panel propio en la barra lateral (**Climatización**).

## Qué hace

- Horarios semanales con franjas: días, hora de inicio y fin, modo (calor, frío, auto…), consigna y, si el equipo lo admite, ventilador.
- Cada horario pertenece a una temporada y solo se ejecuta cuando esa temporada está activa.
- Cambio de temporada manual o automático por fechas (p. ej. 1 abr → Entretiempo, 15 jun → Verano…). Un cambio manual se respeta hasta la siguiente fecha.
- Franjas que cruzan la medianoche (22:00 → 06:00).
- Opción por horario de **apagar el equipo al terminar cada franja**.
- Funciona por eventos: solo actúa al empezar o acabar una franja, así que si cambias algo a mano no lo pisa hasta el siguiente evento.
- Al arrancar HA o al cambiar de temporada aplica el estado que toca en ese momento (configurable).

## Entidades y servicios

| Entidad (el ID puede variar según el idioma de HA) | Uso |
|---|---|
| `select.climate_planner_season` | Temporada activa |
| `switch.climate_planner_scheduling_enabled` | Interruptor general |
| `switch.climate_planner_date_based_season_change` | Cambio de temporada por fechas |

- `climate_planner.set_season` (`season: winter | transition | summer`)
- `climate_planner.resync`: aplica ahora el estado de los horarios activos.
- Cada acción lanza el evento `climate_planner_action` (útil para notificaciones o logbook).

## Instalación

**HACS (repositorio personalizado):** HACS → menú ⋮ → *Repositorios personalizados* → URL de este repo, tipo *Integración* → instalar → reiniciar HA.

**Manual:** copia `custom_components/climate_planner` en `/config/custom_components/` y reinicia HA.

Después: *Ajustes → Dispositivos y servicios → Añadir integración → Climate Planner*. Aparecerá **Climatización** en la barra lateral (solo administradores).

## Migrar desde la app de Daikin

1. Apunta las tres programaciones actuales de la app.
2. Créalas en el panel: un horario por equipo o grupo de equipos y temporada. El botón **Duplicar** sirve para pasar un horario de una temporada a otra.
3. Ajusta las fechas de cambio de temporada.
4. **Desactiva o borra los temporizadores en la app de Daikin**, porque si no los dos sistemas se pisan.

## Desarrollo

```bash
pip install pytest-homeassistant-custom-component home-assistant-frontend
pytest
```

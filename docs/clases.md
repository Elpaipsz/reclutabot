# Diagrama de clases (modelo implementado)

Imagen: `docs/diagramas/clases.png` (fuente `clases.mmd`). Es el modelo que realmente existe en la base de datos (`db/01-schema.sql`) y en el código. Extiende el diagrama de
clases inicial del equipo con las clases que la implementación necesitó (ver la tabla de cambios al final).

```mermaid
classDiagram
  direction LR

  class Usuario {
    -int id
    -String nombre
    -String correo
    -String passwordHash
    -Rol rol
  }
  class Rol {
    <<enumeration>>
    auxiliar
    analista
    coordinador
    admin
  }
  class Vacante {
    -int id
    -String codigo
    -String titulo
    -String descripcion
    -String area
    -String ubicacion
    -String modalidad
    -String contrato
    -String salario
    -String responsabilidades
    -String ofrecemos
    -EstadoVacante estado
    -JSON requisitos
    -JSON pesos
    +admitePostulaciones() boolean
  }
  class Candidato {
    -int id
    -String nombre
    -String correo
    -String telefono
    -String documento
    -boolean aceptaDatos
  }
  class Postulacion {
    -int id
    -String numero
    -Canal canal
    -EstadoPostulacion estado
    -Clasificacion clasificacion
    -double puntaje
    -String procesoId
    -String rrhhId
    -Date recibidaEn
    +cambiarEstado(String)
  }
  class HojaDeVida {
    -String archivoPath
    -String archivoHash
    +validarDocumento() boolean
  }
  class Extraccion {
    -JSON datos
    -JSON confianza
    -String resumen
    -double aniosExperiencia
    -JSON datosValidados
    -double costoUsd
  }
  class Decision {
    -TipoDecision tipo
    -String resultado
    -String observacion
    -Date creadaEn
  }
  class Expediente {
    <<sistema RR.HH.>>
    -String rrhhId
    -Date fechaCreacion
    +actualizar()
  }
  class Incidencia {
    -Origen origen
    -String detalle
    -String capturaPath
    -boolean resuelta
  }
  class EventoAuditoria {
    -String actor
    -String accion
    -String resultado
    -JSON detalle
    -Date creadoEn
  }
  class Notificacion {
    -String destinatario
    -String plantilla
    -boolean enviada
  }
  class PlantillaCorreo {
    -String clave
    -String asunto
    -String cuerpo
  }
  class MotorReglas {
    <<servicio>>
    +evaluar(datos, anios, requisitos, pesos) Evaluacion
  }
  class ServicioExtraccionIA {
    <<servicio>>
    +extraer(archivo) Extraccion
  }
  class RobotRPA {
    <<servicio>>
    +registrar(postulacion) String
  }
  class CalendarioHabil {
    <<servicio>>
    +plazoEscalacion(inicio) Duracion
  }

  Usuario --> Rol
  Usuario "1" --> "0..*" Vacante : publica y edita
  Candidato "1" --> "0..*" Postulacion : realiza
  Vacante "1" --> "0..*" Postulacion : recibe
  Postulacion "1" *-- "1" HojaDeVida : adjunta
  Postulacion "1" --> "0..*" Extraccion : se extrae en
  Postulacion "1" --> "0..*" Decision : registra
  Usuario "1" --> "0..*" Decision : toma
  Postulacion "1" --> "0..1" Expediente : se organiza en
  Postulacion "1" --> "0..*" Incidencia : genera
  Postulacion "1" --> "0..*" EventoAuditoria : deja traza
  Postulacion "1" --> "0..*" Notificacion : envia
  Notificacion "0..*" --> "1" PlantillaCorreo : usa
  MotorReglas ..> Postulacion : puntua
  ServicioExtraccionIA ..> Extraccion : produce
  RobotRPA ..> Expediente : crea
  CalendarioHabil ..> Postulacion : fija plazo de escalacion
```

## Qué cambió respecto al diagrama inicial

| Cambio | Motivo |
|---|---|
| Nueva `Vacante` (con `requisitos` y `pesos`) | Sin ella no existen RF-13/14/30: los requisitos se configuran por vacante |
| `AnalistaSeleccion` y `CoordinadorSeleccion` → una sola clase `Usuario` con `Rol` | Mismos datos y distinto permiso; añade `auxiliar` y `admin` y alinea HU y RF (que usaban nombres de rol distintos) |
| `Postulacion.documentoValido` y `cumpleRequisitos` (booleanos) → `clasificacion` (Cumple / Revisar / No cumple) + `puntaje` | RF-14 y RF-15 piden puntaje y tres clases, no un booleano |
| `Postulacion.estado` con 10 valores | RF-25 + `Duplicada` (RF-05) |
| `HojaDeVida.datosExtraidos` → clase `Extraccion` aparte | Se conservan varias extracciones (reintentos), la confianza por campo, la versión corregida por la persona y el costo de IA |
| Nuevas `Decision`, `Incidencia`, `EventoAuditoria`, `Notificacion` | HU-13 (trazabilidad), HU-15 (errores), HU-16 (notificaciones), RF-18 (observación obligatoria) |
| `Expediente` se mantiene como el registro en el sistema de RR.HH. | Es lo que crea el robot; se enlaza con `Postulacion.rrhhId` |
| Servicios `MotorReglas`, `ServicioExtraccionIA`, `RobotRPA` | Los métodos `validarDatosYRequisitos`, `validarDocumento` salen de las entidades y pasan a servicios, para que la IA no decida |
| `Vacante` con datos públicos (área, ubicación, modalidad, contrato, salario, responsabilidades, qué ofrecemos) | Página pública de empleos y oferta para LinkedIn u otros portales |
| `Usuario` publica y edita `Vacante` | Pantalla de gestión de vacantes (auxiliar y admin) |
| Nueva `PlantillaCorreo` usada por `Notificacion` | RF-28: textos de correo editables desde pantalla |
| Nuevo servicio `CalendarioHabil` | RF-19: plazo de escalación en horas hábiles |

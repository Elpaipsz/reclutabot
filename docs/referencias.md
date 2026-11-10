# Repos revisados como referencia

| Repo | Licencia | Qué hace | Qué sirvió |
|---|---|---|---|
| interviewstreet/hiring-agent | MIT | Parsea CV a «JSON Resume» y lo puntúa con una rúbrica por roles | Reglas de fechas, cláusula de equidad. Idea futura: puntaje con `score/max` + evidencia por categoría |
| AryaXDG/RecruitAI | Sin licencia (no reutilizable) | ATS Node + Gemini + ML | Solo ideas: citas de evidencia por habilidad, bandera de relleno de palabras clave |
| bfang899/open_recruiter | MIT | Agentes de reclutamiento con emparejamiento CV–vacante (puntaje, fortalezas, brechas) | Idea: salida «fortalezas / brechas / razonamiento» para el puntaje explicable. No aplicado |
| reqcore-inc/reqcore-app | AGPL-3.0 | ATS completo | Repo no accesible (404); en todo caso solo ideas |
| espetro/dits | CPAL-1.0 | Entrevistas con IA | Solo ideas; no se tomó nada |
| IliaLarchenko/Interviewer | Apache-2.0 | Entrevistador de IA con notas ocultas y retroalimentación | Principios de evaluación basada en evidencia y preguntas sin pistas |
| Jonmaa/AI-Interview-Coach | MIT | Coach de entrevistas con RAG y puntaje 1–10 | Dimensiones de evaluación de respuestas |

Lo que **no** se trajo y por qué: detección de duplicados (la nuestra por correo/hash ya cubre RF-05, ningún repo aportaba algo mejor),
ATS completos (ya tenemos Flowable) y voz/RAG (fuera del alcance).

Los repos se clonaron solo para consulta y viven **fuera** del proyecto (`../_refs_referencias`), para no distribuir código ajeno con la entrega.

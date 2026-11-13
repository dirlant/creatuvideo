# Qué prompt usar según el video

| Tipo de video | Hook | Prompt | Público | Palabras por segundo |
|---|---|---|---|---|
| **Rubros** (micropigmentación, estilistas, salón, cejas, maquillaje, depilación, limpieza facial, podología…) | Los hooks por rubro (`lv_…`) | **Dianchi**: `proyectos\dianchi\src\prompt.ts` (resumen en `dianchi_rubros.md`) | La profesional del rubro (o su clienta, según el formato) | 3 (tope), en la práctica unas 2,5 con la voz a 1.3x |
| **Mentor** (temas empresariales: administración, finanzas, publicidad, precios…) | "Si yo fuera tu mentor, te diría lo siguiente" (`mentor.mp4` y `lv_0_20261108105603.mp4`) | **Diegao**: `diegao_mentor.md` (repo `proyectos\Diegao`) | El dueño del negocio de belleza | 2,5 |

Los prompts son instrucciones para quien escribe el guion (Claude), no se llama a ninguna API. Los videos se generan después con `contenido-automatico\generar.py`.

Diseño común (ya confirmado): fondo negro, onda estilo SoundCloud con micrófono y REC, título del hook (Verdana + Billabong), subtítulos sin animación, cinta "GUARDA ESTE AUDIO Y ÚSALO EN TU CONTENIDO", voz 1.3x, CTA de guardar.

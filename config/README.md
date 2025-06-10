# Informacion sobre BONUS Y PENALTY

La respuesta corta y recomendada es: debes usar una escala entre -1 y 1, y en la práctica, un rango aún más pequeño como -0.3 a +0.3 suele ser lo más efectivo.

Aquí te explico el porqué:

El Contexto de tu score_total
Tu score_total se compone de dos partes principales:

La Parte Ponderada: Es la suma de (caracteristica_escalada * peso_normalizado).

Cada caracteristica_escalada está en un rango de 0 a 1.
La suma de todos tus peso_normalizado es 1.0.
Esto significa que esta primera parte del score (la suma de todas las ponderaciones) siempre dará un resultado entre 0.0 y 1.0.
La Parte de Ajustes Fijos (Bonus y Penalizaciones):

Estos son los valores BONUS_... y PENALTY_... que se suman o restan directamente a ese score ponderado que va de 0 a 1.
Por Qué una Escala de 0 a 10 no es recomendable aquí
Imagina este escenario:

Coche A tiene un score ponderado de 0.75 (muy bueno).
Coche B tiene un score ponderado de 0.60 (bueno).
Ambos cumplen una regla que les da un bonus de +8.0.
El resultado sería:

Score final Coche A: 0.75 + 8.0 = 8.75
Score final Coche B: 0.60 + 8.0 = 8.60
Como puedes ver, el bonus de +8.0 es tan desproporcionadamente grande que la diferencia original de calidad entre los coches (0.15 puntos) se vuelve casi irrelevante. La bonificación dominaría por completo el ranking, ignorando todo el trabajo detallado que hicimos con los pesos.

Por Qué una Escala entre -1 y 1 (o más pequeña) es mejor
Usar valores más pequeños para los bonus y penalizaciones te permite tratarlos como ajustes importantes pero equilibrados.

Imagina el mismo escenario con un bonus de +0.15:

Score final Coche A: 0.75 + 0.15 = 0.90
Score final Coche B: 0.60 + 0.15 = 0.75
Aquí, ambos coches reciben un "empujón" por cumplir la regla, pero el Coche A sigue siendo claramente superior. El bonus actúa como un factor de influencia o un desempate, pero no anula la calidad intrínseca del coche según el resto de las preferencias del usuario.

Mi Recomendación
Para las constantes en tu Canvas config/settings.py:

BONUS: Usa valores positivos entre 0.05 (un pequeño empujón) y 0.20 (un favoritismo muy fuerte). Un valor como 0.10 o 0.15 (como los que tienes ahora) es un excelente punto de partida.
PENALTY: Usa valores negativos entre -0.05 y -0.20. Una penalización de -0.25 o -0.50 (como la que pusiste para ZBE) es extremadamente fuerte y debe reservarse para casos que son casi un "veto" o una "bandera roja".
En resumen: Quédate con la escala de -1 a 1, y dentro de ese rango, usa valores que reflejen cuán decisiva quieres que sea cada regla, manteniendo los valores en el Canvas como están.
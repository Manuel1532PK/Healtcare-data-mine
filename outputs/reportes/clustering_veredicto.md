# Veredicto · Agrupamiento K-means con apoyo jerárquico

## Qué hicimos

Agrupamos los **48,710** registros de `main` con **30 variables** (conjunto C: sin variables de diseño de encuesta y sin una dummy de referencia por grupo).

Combinamos dos métodos, según la forma que propone la clase:

1. **Jerárquico Ward sobre una muestra de 5,000 personas.** Lo usamos para revisar el dendrograma y confirmar cuántos grupos sugiere el corte.
2. **K-means con `k=3`, `n_init=10`, `random_state=42`, sobre las 48 710 personas.** Es el método principal y asigna el grupo definitivo.

No usamos la etiqueta para entrenar. La guardamos para describir los grupos al final.

## Resultados

- El corte que da 3 grupos cae entre las alturas 78.82 y 135.56. Ese salto grande es lo que sostiene el número de grupos.
- Tamaños del jerárquico en la muestra: 1649, 1815, 1536.
- Acuerdo entre jerárquico y K-means en la misma muestra (ARI): **0.5856**.
- Silueta de K-means con 2 000 personas: **0.2182**; con 10 000: **0.2213**.
- Tamaños de K-means en las 48 710 personas: grupo 0: 9,130, grupo 1: 23,304, grupo 2: 16,276.

```
 cluster  personas  prevalencia_diabetes_obesidad_colesterol  edad_z  cintura_z  proporcion_proxy_menores  proporcion_hombres
       0      9130                                    0.4807  0.0861     0.3138                    0.2789              0.7125
       1     23304                                    0.6371  0.6759     0.5262                    0.0689              0.4245
       2     16276                                    0.0484 -1.0161    -0.9294                    0.9922              0.4739
```

## Qué significan los grupos

- **Grupo de personas jóvenes:** casi todas tienen el proxy de menores de edad y prevalencia muy baja.
- **Grupo de adultos con mayor prevalencia:** más edad, más cintura y prevalencia cercana a 0,64.
- **Grupo intermedio:** prevalencia cercana a la media de la muestra.

## Lectura del acuerdo

Un ARI de 0.59 indica acuerdo moderado: los dos métodos coinciden en la mayoría de las personas, pero no en todas. Por eso presentamos K-means como resultado principal y el jerárquico como apoyo, no como prueba definitiva.

## Límites

- La silueta es baja (≈0,22): son perfiles amplios, no grupos perfectamente separados.
- El jerárquico se calculó sobre una muestra, por el costo de memoria del método Ward. El resultado final usa las 48 710 personas con K-means.
- El dendrograma está truncado a 30 ramas para poder leerlo.
- La memoria del jerárquico se midió con `tracemalloc` (solo Python); el proceso completo consume más.

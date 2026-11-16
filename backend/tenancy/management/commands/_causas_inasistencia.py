"""Las causas de la inasistencia en el dataset de demostración (US-35).

Sin Django a propósito: es aritmética pura y por eso se importa en las
pruebas sin base de datos. El guion bajo del nombre evita que Django lo tome
por un comando.

**Por qué existe.** Antes, `seed_dataset` sorteaba el desenlace de cada ficha
pasada al azar (78 % atendida, 12 % ausente, 10 % cancelada). Un modelo de
riesgo entrenado con eso no tiene nada que aprender: la ausencia no dependía
de nada. Ahora la probabilidad de ausentarse sale de causas que existen en la
vida real y que el modelo de US-35 puede leer de cada ficha, y la función de
abajo es la "verdad oculta" del dataset.
"""

import math

# --------------------------------------------------------------------------
#  Pesos del logit. Son fijos y están a la vista: si el modelo de US-35 anda
#  bien, tiene que redescubrir estos números (en signo y en orden de magnitud)
#  a partir de las fichas sembradas.
# --------------------------------------------------------------------------

# Ordenada al origen: con todo en cero (reserva para hoy, sin adelanto, sin
# faltas, martes a la mañana) la ausencia ronda el 7 %.
LOGIT_BASE = -2.6

# Por cada día entre la reserva y el turno. Quien reserva con un mes de
# anticipación se olvida más: 30 días suman 1,35 al logit.
PESO_DIA_DE_ANTICIPACION = 0.045
TOPE_DIAS_DE_ANTICIPACION = 45

# Haber pagado al reservar (con al menos 24 h de margen) compromete: baja el
# logit. Es la señal más fuerte a favor de asistir.
PESO_PAGO_ADELANTADO = -1.3

# Quien ya faltó antes, vuelve a faltar. Por cada falta previa del paciente.
PESO_FALTA_PREVIA = 0.9
TOPE_FALTAS_PREVIAS = 3

# Los lunes (arranque de semana) y los sábados (día libre) se falta más.
PESO_LUNES = 0.35
PESO_SABADO = 0.40

# Los turnos de la tarde se pierden más que los de la mañana.
PESO_TARDE = 0.30
HORA_DE_TARDE = 14

LUNES = 0
SABADO = 5

# --------------------------------------------------------------------------
#  Ventana del historial que agrega `seed_dataset --history`: empieza justo
#  antes de las fichas que el `--enrich` ya sembró (los últimos 60 días) y
#  retrocede siete meses. Entre las dos queda más de un semestre de datos, que
#  es lo que pide el entrenamiento.
# --------------------------------------------------------------------------

HISTORIAL_DESDE_DIAS = 210
HISTORIAL_HASTA_DIAS = 61


def probabilidad_ausencia(anticipacion_dias, pago_adelantado, faltas_previas,
                          dia_semana, hora):
    """Probabilidad de que el paciente no se presente al turno, en (0, 1).

    Es una regresión logística con pesos fijos (ver las constantes de arriba).
    Estos son los pesos que el modelo de riesgo de US-35 debería
    redescubrir al entrenar con las fichas que siembra `seed_dataset`:

    - `anticipacion_dias`: días entre la reserva y el turno; cuanto más lejos,
      más se olvida. Suma 0,045 por día, con tope en 45 días.
    - `pago_adelantado`: pagó al reservar, con al menos 24 h de margen. Resta
      1,3: quien pagó por adelantado casi siempre va.
    - `faltas_previas`: ausencias anteriores del mismo paciente. Suma 0,9 por
      cada una, con tope en 3.
    - `dia_semana`: 0 = lunes … 6 = domingo (`datetime.weekday()`). Suma 0,35
      el lunes y 0,40 el sábado.
    - `hora`: hora local de inicio del turno. Suma 0,30 desde las 14.

    Con la base de -2,6 y todo lo demás en cero, la ausencia ronda el 7 %.
    Los valores fuera de rango no fallan: la anticipación negativa cuenta
    como cero y las faltas negativas también.
    """
    dias = min(max(float(anticipacion_dias), 0.0), TOPE_DIAS_DE_ANTICIPACION)
    faltas = min(max(int(faltas_previas), 0), TOPE_FALTAS_PREVIAS)

    logit = LOGIT_BASE + PESO_DIA_DE_ANTICIPACION * dias + PESO_FALTA_PREVIA * faltas
    if pago_adelantado:
        logit += PESO_PAGO_ADELANTADO
    if dia_semana == LUNES:
        logit += PESO_LUNES
    elif dia_semana == SABADO:
        logit += PESO_SABADO
    if hora >= HORA_DE_TARDE:
        logit += PESO_TARDE

    return 1.0 / (1.0 + math.exp(-logit))

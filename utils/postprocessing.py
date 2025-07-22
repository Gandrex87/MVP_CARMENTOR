# Separar responsabilidades: dejar al LLM lo fácil y completar lo crítico
# En lugar de depender de que el LLM devuelva la lista completa, se definen reglas de negocio fija:
# Este enfoque más robusto y estándar en producción:
# Combinar inferencia + reglas determinísticas para asegurar integridad del estado.

# utils/postprocessing.py
from utils.enums import Transmision , TipoMecanica
from typing import Optional, List, Set, Dict
from graph.perfil.state import PerfilUsuario, FiltrosInferidos,InfoClimaUsuario , EstadoAnalisisPerfil
from .conversion import is_yes
import logging

# --- NUEVA Función de Post-procesamiento para PerfilUsuario ---

def aplicar_postprocesamiento_perfil(
    preferencias: Optional[PerfilUsuario]
) -> Optional[PerfilUsuario]:
    """
    Aplica reglas de post-procesamiento que modifican SOLO PerfilUsuario.
    - Regla: Si quiere solo eléctricos y no tiene preferencia de transmisión, 
             se asigna automática.Devuelve una NUEVA instancia de PerfilUsuario con los cambios aplicados, o None si la entrada es None.
    """
    if preferencias is None:
        return None

    # Usamos model_copy() para trabajar sobre una copia y no modificar el objeto original del estado
    prefs_actualizado = preferencias.model_copy(deep=True)
    cambios_realizados = False # Para seguimiento y debugging

    # --- Regla 1: Eléctrico implica transmisión automática si no hay preferencia ---
    solo_electricos_val = prefs_actualizado.solo_electricos
    transmision_actual = prefs_actualizado.transmision_preferida

    # Usamos la utilidad is_yes para comprobar 'sí'/'si' de forma robusta
    if is_yes(solo_electricos_val) and transmision_actual is None:
        print("DEBUG (PostProc Perfil) ► Aplicando regla: solo_electricos='sí' y sin transmision -> asignando AUTOMATICO")
        # Asignamos el MIEMBRO del Enum, no el string 'automático'
        prefs_actualizado.transmision_preferida = Transmision.AUTOMATICO 
        cambios_realizados = True

    # Devolver el objeto actualizado (la copia) si hubo cambios, o el original si no los hubo
    if cambios_realizados:
        print(f"DEBUG (PostProc Perfil) ► Perfil tras post-procesamiento: {prefs_actualizado}")
        return prefs_actualizado
    else:
        # No hubo cambios, podemos devolver el objeto original (o la copia, es indiferente si no se modificó)
        return preferencias # Devolver el original para evitar crear objetos innecesarios


def aplicar_postprocesamiento_filtros(
    filtros: Optional[FiltrosInferidos],
    preferencias: Optional[PerfilUsuario],
    info_clima: Optional[InfoClimaUsuario] 
) -> Optional[FiltrosInferidos]:
    """
    CONSTRUYE la lista de filtros de tipo de mecánica basándose en 
    restricciones duras e innegociables.
    """
    if not filtros or not preferencias:
        return filtros

    filtros_actualizado = filtros.model_copy(deep=True)
    solo_electricos_val = preferencias.solo_electricos

    # --- REGLA 1: La restricción "solo eléctricos" tiene prioridad absoluta ---
    if is_yes(solo_electricos_val):
        logging.info("PostProc Filtros: Restricción dura -> solo_electricos='sí'. Universo de búsqueda: BEV, REEV.")
        filtros_actualizado.tipo_mecanica = [TipoMecanica.BEV, TipoMecanica.REEV]
        return filtros_actualizado

    # --- Si no es solo eléctricos, construimos la lista desde cero ---
    
    # Empezamos con el universo completo de TODAS las mecánicas posibles.
    mecanicas_set: Set[TipoMecanica] = {member for member in TipoMecanica}
    logging.debug(f"PostProc Filtros: Iniciando con el universo completo de mecánicas: {len(mecanicas_set)} tipos.")

    # --- REGLA 2: Restricciones por ZBE ---
    # Si vive en ZBE, eliminamos las opciones más problemáticas.
    if info_clima and getattr(info_clima, 'MUNICIPIO_ZBE', False):
        logging.info("PostProc Filtros: Restricción ZBE -> Eliminando DIESEL puros.")
        #mecanicas_set.discard(TipoMecanica.GASOLINA)
        mecanicas_set.discard(TipoMecanica.DIESEL)

    # --- REGLA 3: Restricciones por disponibilidad de GLP/GNV ---
    if info_clima and getattr(info_clima, 'cp_valido_encontrado', False):
        if not getattr(info_clima, 'ZONA_GLP', True):
            mecanicas_set.discard(TipoMecanica.GLP)
            logging.info("PostProc Filtros: Restricción geográfica -> Eliminando GLP.")
        if not getattr(info_clima, 'ZONA_GNV', True):
            mecanicas_set.discard(TipoMecanica.GNV)
            logging.info("PostProc Filtros: Restricción geográfica -> Eliminando GNV.")

    # Actualización final de los filtros
    filtros_actualizado.tipo_mecanica = sorted(list(mecanicas_set), key=lambda x: x.value)
    logging.info(f"--- FIN DEBUG PostProc Filtros --- Filtros de mecánica finales construidos: {filtros_actualizado.tipo_mecanica}")
    
    return filtros_actualizado


# Flag coche_ciudad_perfil:

# suele_llevar_acompanantes = True
# y frecuencia_viaje_con_acompanantes = "ocasional" o "frecuente"
# y circula_principalmente_ciudad = 'si' 
# y transporta_carga_voluminosa = 'no'
# y distancia_trayecto = DistanciaTrayecto.MENOS_10_KM o  DistanciaTrayecto.ENTRE_10_Y_50_KM 
# y realiza_viajes_largos = 'nunca'

# Entonces → Bonificar
# 'largo'< 330  (+ 5 puntos))
# 'peso' < 950  (+ 2 puntos)


# Flag coche ciudad 2:

# suele_llevar_acompanantes =  False o frecuencia_viaje_con_acompanantes = "ocasional"
# y Circular principalmente ciudad = Sí, y
# Maletero amplio = No 
# y Trayecto más frecuente = DistanciaTrayecto.MENOS_10_KM o  DistanciaTrayecto.ENTRE_10_Y_50_KM 
# y realiza_viajes_largos = 'si'
# y frecuencia_viajes_largos = FrecuenciaViajesLargos.OCASIONALMENTE

# Entonces → Bonificar
# 'largo'< 390  ( + 5 puntos))
# 'peso' < 1000  (+ 2 puntos)


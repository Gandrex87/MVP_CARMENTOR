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



# --- Helper interno para simplificar comprobaciones ---
def _es_nulo_o_vacio(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, (list, str)) and not valor: # Lista vacía o string vacío
        return True
    return False

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
    Aplica reglas de post-procesamiento que modifican FiltrosInferidos,
    utilizando PerfilUsuario e InfoClimaUsuario como contexto.
    Devuelve una instancia de FiltrosInferidos con cambios (o la original si no hay cambios).
    """
    logging.debug("\n--- DEBUG DENTRO PostProc Filtros ---")
    logging.debug(f"Recibido Prefs: {preferencias.model_dump_json(indent=2) if preferencias else None}") # Más legible
    logging.debug(f"Recibido Filtros (antes): {filtros.model_dump_json(indent=2) if filtros else None}")
    logging.debug(f"Recibido Info Clima: {info_clima.model_dump_json(indent=2) if info_clima else None}")
    
    if filtros is None:
         logging.debug("PostProc Filtros: Objeto FiltrosInferidos de entrada es None. No se aplica post-procesamiento.")
         return None 
    if preferencias is None:
         logging.debug("PostProc Filtros: Objeto PreferenciasUsuario de entrada es None. No se puede aplicar la mayoría del post-procesamiento.")
         return filtros 

    filtros_actualizado = filtros.model_copy(deep=True)
    cambios_efectuados_en_este_nodo = False

    # --- Lógica de Tipo de Mecánica ---
    # Trabajar con un set para facilitar adiciones y evitar duplicados
    mecanicas_set: Set[TipoMecanica] = set(filtros_actualizado.tipo_mecanica or [])
    # Guardar una copia del set original para comparar al final si hubo cambios en mecánicas
    mecanicas_set_original = set(mecanicas_set) 

    solo_electricos_val = preferencias.solo_electricos # String 'sí', 'no', o None

    # 1. Regla: Forzar BEV/REEV si 'solo_electricos' es 'sí'
    if is_yes(solo_electricos_val):
        expected_electricas_enums = {TipoMecanica.BEV, TipoMecanica.REEV}
        if mecanicas_set != expected_electricas_enums:
            logging.debug(f"PostProc Filtros: solo_electricos='sí'. Estableciendo tipo_mecanica a BEV, REEV.")
            mecanicas_set = expected_electricas_enums
    # # 2. Regla: Default si 'solo_electricos' es 'no' y el LLM no infirió nada
    # elif isinstance(solo_electricos_val, str) and solo_electricos_val.strip().lower() == 'no':
    #     if not mecanicas_set: # Si el LLM no infirió NADA y no es solo eléctricos
    #         logging.debug("PostProc Filtros: solo_electricos='no' y LLM no dio mecánicas -> asignando default amplio.")
    #         mecanicas_set.update([
    #             TipoMecanica.GASOLINA, TipoMecanica.DIESEL, TipoMecanica.PHEVG, TipoMecanica.PHEVD,
    #             TipoMecanica.HEVG, TipoMecanica.HEVD, TipoMecanica.MHEVG, TipoMecanica.MHEVD,
    #             TipoMecanica.GLP, TipoMecanica.GNV
    #         ])
    # Si solo_electricos_val es None, se procede con lo que haya en mecanicas_set (del LLM o vacío).

    # 4. Lógica para GLP/GNV por Zona (se aplica sobre mecanicas_set)
    if info_clima and info_clima.cp_valido_encontrado: 
        if not info_clima.ZONA_GLP: 
            mecanicas_set.discard(TipoMecanica.GLP) # discard no da error si no está
            logging.debug(f"PostProc Filtros: CP no en ZONA_GLP. GLP eliminado si estaba.")
        elif not is_yes(solo_electricos_val) or solo_electricos_val is None: # Si SÍ hay ZONA_GLP y no es solo_electricos
            mecanicas_set.add(TipoMecanica.GLP)
            logging.debug(f"PostProc Filtros: CP en ZONA_GLP y no solo_electricos. GLP asegurado.")
            
        if not info_clima.ZONA_GNV: 
            mecanicas_set.discard(TipoMecanica.GNV)
            logging.debug(f"PostProc Filtros: CP no en ZONA_GNV. GNV eliminado si estaba.")
        elif not is_yes(solo_electricos_val) or solo_electricos_val is None: # Si SÍ hay ZONA_GNV y no es solo_electricos
            mecanicas_set.add(TipoMecanica.GNV)
            logging.debug(f"PostProc Filtros: CP en ZONA_GNV y no solo_electricos. GNV asegurado.")

    # 5. Lógica adicional por ZBE (ejemplo, sobre mecanicas_set)
    if info_clima and info_clima.cp_valido_encontrado and info_clima.MUNICIPIO_ZBE:
        logging.debug(f"PostProc Filtros: Municipio ZBE. Ajustando mecánicas.")
        if TipoMecanica.DIESEL in mecanicas_set:
            pass # Placeholder
        if not is_yes(solo_electricos_val) or solo_electricos_val is None:
            mecanicas_limpias_para_zbe = {
                TipoMecanica.BEV, TipoMecanica.REEV, TipoMecanica.PHEVG, TipoMecanica.PHEVD, 
                TipoMecanica.HEVG, TipoMecanica.HEVD, TipoMecanica.GLP, TipoMecanica.GNV
            }
            mecanicas_set.update(mecanicas_limpias_para_zbe)
            
    # 6. Revisión final si solo_electricos='no' y la lista es muy restrictiva o vacía
    if preferencias and isinstance(preferencias.solo_electricos, str) and \
       preferencias.solo_electricos.strip().lower() == 'no':
        if not mecanicas_set or \
           (len(mecanicas_set) <= 3 and all(mec in {TipoMecanica.GLP, TipoMecanica.GNV} for mec in mecanicas_set)):
            logging.warning(f"PostProc Filtros: solo_electricos='no' pero mecánicas es {mecanicas_set}. Ampliando.")
            mecanicas_base_adicionales = {TipoMecanica.GASOLINA, TipoMecanica.HEVG, TipoMecanica.PHEVG}
            mecanicas_set.update(mecanicas_base_adicionales)

    # Aplicar la lista final de mecánicas
    lista_final_mecanicas = sorted(list(mecanicas_set), key=lambda x: x.value) if mecanicas_set else None
    
    if filtros_actualizado.tipo_mecanica != lista_final_mecanicas: # Compara la lista original con la final
        filtros_actualizado.tipo_mecanica = lista_final_mecanicas
        cambios_efectuados_en_este_nodo = True

    # # --- Reglas para estetica_min, premium_min, singular_min ---
    # if preferencias:
    #     # Estética
    #     estetica_target = PESO_CRUDO_FAV_ESTETICA if is_yes(preferencias.valora_estetica) else PESO_CRUDO_BASE_ESTETICA
    #     if filtros_actualizado.estetica_min != estetica_target:
    #         logging.debug(f"PostProc Filtros: Aplicando regla estetica: de {filtros_actualizado.estetica_min} a {estetica_target}")
    #         filtros_actualizado.estetica_min = estetica_target
    #         cambios_efectuados_en_este_nodo = True
            
    #     # Premium
    #     premium_min_target = PESO_CRUDO_FAV_PREMIUM if is_yes(preferencias.apasionado_motor) else PESO_CRUDO_BASE_PREMIUM 
    #     if filtros_actualizado.premium_min != premium_min_target:
    #         logging.debug(f"PostProc Filtros: Aplicando regla premium: de {filtros_actualizado.premium_min} a {premium_min_target}")
    #         filtros_actualizado.premium_min = premium_min_target
    #         cambios_efectuados_en_este_nodo = True

    #     # Singular (Aditiva)
    #     singular_min_calculado = (PESO_CRUDO_FAV_SINGULAR if is_yes(preferencias.apasionado_motor) else PESO_CRUDO_BASE_SINGULAR) + \
    #                              (PESO_CRUDO_FAV_SINGULAR if is_yes(preferencias.prefiere_diseno_exclusivo) else PESO_CRUDO_BASE_SINGULAR)
    #     singular_min_calculado = max(0.0, min(10.0, singular_min_calculado)) # Clamp

    #     if filtros_actualizado.singular_min != singular_min_calculado:
    #         logging.debug(f"PostProc Filtros: Aplicando regla singular (aditiva): de {filtros_actualizado.singular_min} a {singular_min_calculado}")
    #         filtros_actualizado.singular_min = singular_min_calculado
    #         cambios_efectuados_en_este_nodo = True

    if cambios_efectuados_en_este_nodo:
        logging.debug(f"--- FIN DEBUG PostProc Filtros --- Filtros actualizados finales: {filtros_actualizado.model_dump_json(indent=2) if filtros_actualizado else None}")
    else:
        logging.debug("--- FIN DEBUG PostProc Filtros --- No se realizaron cambios significativos en los filtros por este nodo.")
        
    return filtros_actualizado


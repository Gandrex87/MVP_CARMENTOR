# Separar responsabilidades: dejar al LLM lo fácil y completar lo crítico
# En lugar de depender de que el LLM devuelva la lista completa, se definen reglas de negocio fija:
# Este enfoque más robusto y estándar en producción:
# Combinar inferencia + reglas determinísticas para asegurar integridad del estado.

# utils/postprocessing.py
from utils.enums import Transmision , TipoMecanica
from typing import Optional, List
from graph.perfil.state import PerfilUsuario, FiltrosInferidos,InfoClimaUsuario 
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
    logging.debug("\n--- DEBUG DENTRO PostProc Filtros ---") # Usar logging
    logging.debug(f"Recibido Prefs: {preferencias}")
    logging.debug(f"Recibido Filtros (antes): {filtros}")
    logging.debug(f"Recibido Info Clima: {info_clima}")
    
    if filtros is None: # Si no hay objeto de filtros base, no podemos hacer nada
         logging.debug("DEBUG (PostProc Filtros) ► Objeto FiltrosInferidos de entrada es None. No se aplica post-procesamiento.")
         return None 
    
    # Trabajar sobre copias para no modificar el objeto original del estado directamente
    # a menos que sea la intención (lo cual es, al final, si hay cambios).
    filtros_actualizado = filtros.model_copy(deep=True)
    cambios_efectuados_en_este_nodo = False # Flag para saber si este nodo hizo algún cambio

    # --- Regla: Tipo de mecánica default si 'solo_electricos' es 'no' y falta tipo_mecanica ---
    if preferencias and isinstance(preferencias.solo_electricos, str) and \
       preferencias.solo_electricos.strip().lower() == 'no' and \
       _es_nulo_o_vacio(filtros_actualizado.tipo_mecanica):
        
        logging.debug("DEBUG (PostProc Filtros) ► Aplicando regla: solo_electricos='no' y sin tipo_mecanica -> asignando default no eléctrico")
        lista_mecanicas_default = [ 
            TipoMecanica.GASOLINA, TipoMecanica.DIESEL, TipoMecanica.PHEVG,
            TipoMecanica.PHEVD, TipoMecanica.HEVG, TipoMecanica.HEVD,
            TipoMecanica.MHEVG, TipoMecanica.MHEVD,
            TipoMecanica.GLP, TipoMecanica.GNV
        ]
        if filtros_actualizado.tipo_mecanica != lista_mecanicas_default: # Comprobar si realmente cambia
            filtros_actualizado.tipo_mecanica = lista_mecanicas_default
            cambios_efectuados_en_este_nodo = True

    # --- Regla: Forzar BEV/REEV si 'solo_electricos' es 'sí' ---
    # Esta regla tiene prioridad sobre la anterior si solo_electricos es 'sí'
    if preferencias and is_yes(preferencias.solo_electricos):
        expected_electricas_enums = [TipoMecanica.BEV, TipoMecanica.REEV]
        # Comparar listas de Enums directamente (el orden importa si no se ordenan antes)
        # o convertir a sets de strings de values para comparación insensible al orden.
        current_mecanicas_enums = filtros_actualizado.tipo_mecanica or []
        
        # Para una comparación robusta insensible al orden:
        current_values_set = {m.value for m in current_mecanicas_enums if hasattr(m, 'value')}
        expected_values_set = {m.value for m in expected_electricas_enums}

        if current_values_set != expected_values_set:
            logging.debug(f"DEBUG (PostProc Filtros) ► Aplicando regla: solo_electricos='sí'. Estableciendo tipo_mecanica a BEV, REEV.")
            filtros_actualizado.tipo_mecanica = expected_electricas_enums
            cambios_efectuados_en_este_nodo = True
            
    # --- LÓGICA PARA FILTRAR GLP/GNV POR ZONA ---
    # Esta lógica se aplica DESPUÉS de las reglas anteriores sobre tipo_mecanica
    if info_clima and info_clima.cp_valido_encontrado: 
        mecanicas_permitidas_actual = list(filtros_actualizado.tipo_mecanica) if filtros_actualizado.tipo_mecanica else []
        mecanicas_modificadas_por_clima = list(mecanicas_permitidas_actual) # Copia para modificar

        if not info_clima.ZONA_GLP: 
            if TipoMecanica.GLP in mecanicas_modificadas_por_clima:
                logging.debug(f"DEBUG (PostProc Filtros) ► CP no en ZONA_GLP. Eliminando GLP de tipo_mecanica.")
                mecanicas_modificadas_por_clima.remove(TipoMecanica.GLP)
        
        if not info_clima.ZONA_GNV: 
            if TipoMecanica.GNV in mecanicas_modificadas_por_clima:
                logging.debug(f"DEBUG (PostProc Filtros) ► CP no en ZONA_GNV. Eliminando GNV de tipo_mecanica.")
                mecanicas_modificadas_por_clima.remove(TipoMecanica.GNV)
            
        if len(mecanicas_modificadas_por_clima) != len(mecanicas_permitidas_actual):
            filtros_actualizado.tipo_mecanica = mecanicas_modificadas_por_clima if mecanicas_modificadas_por_clima else None 
            cambios_efectuados_en_este_nodo = True
    elif info_clima: 
         logging.debug(f"DEBUG (PostProc Filtros) ► No se aplicarán filtros GLP/GNV por zona debido a info_clima no concluyente (cp_valido_encontrado={info_clima.cp_valido_encontrado}).")
    else: 
         logging.debug(f"DEBUG (PostProc Filtros) ► No hay info_clima disponible. No se aplicarán filtros GLP/GNV por zona.")
    # --- FIN LÓGICA GLP/GNV ---  

    # --- Regla: Estética mínima según valora_estetica ---
    if preferencias:
        valora_estetica_val = preferencias.valora_estetica
        estetica_target = 1.0 
        if is_yes(valora_estetica_val): estetica_target = 5.0
        
        if filtros_actualizado.estetica_min != estetica_target:
            logging.debug(f"DEBUG (PostProc Filtros) ► Aplicando regla estetica: de {filtros_actualizado.estetica_min} a {estetica_target} (valora_estetica='{valora_estetica_val}')")
            filtros_actualizado.estetica_min = estetica_target
            cambios_efectuados_en_este_nodo = True
            
    # --- Regla: Premium mínima según apasionado_motor - Apasionado SÍ ---
    if preferencias:
        premium_min_target = 1.0 # Tu valor base para "no apasionado" o None
        if is_yes(preferencias.apasionado_motor):
            premium_min_target = 3.0 # Tu valor para "apasionado"
        
        if filtros_actualizado.premium_min != premium_min_target:
            logging.debug(f"DEBUG (PostProc Filtros) ► Aplicando regla premium: de {filtros_actualizado.premium_min} a {premium_min_target} (apasionado_motor='{preferencias.apasionado_motor}')")
            filtros_actualizado.premium_min = premium_min_target
            cambios_efectuados_en_este_nodo = True

    # --- Regla: Singularidad mínima - Exclusivo SÍ (Aditiva) ---
    if preferencias:
        singular_min_calculado = 0.0 
        # Contribución de apasionado_motor
        if is_yes(preferencias.apasionado_motor):
            singular_min_calculado += 3.0
        else: # 'no' o None
            singular_min_calculado += 1.0 # Tu base para no apasionado era 1.0
        
        # Contribución de prefiere_diseno_exclusivo
        if is_yes(preferencias.prefiere_diseno_exclusivo):
            singular_min_calculado += 3.0
        else: # 'no' o None
            singular_min_calculado += 1.0 # Tu base para no exclusivo era 1.0
        
        singular_min_calculado = max(0.0, min(10.0, singular_min_calculado)) # Clamp

        if filtros_actualizado.singular_min != singular_min_calculado:
            logging.debug(f"DEBUG (PostProc Filtros) ► Aplicando regla singular (aditiva): de {filtros_actualizado.singular_min} a {singular_min_calculado}")
            filtros_actualizado.singular_min = singular_min_calculado
            cambios_efectuados_en_este_nodo = True

    if cambios_efectuados_en_este_nodo:
        logging.debug(f"--- FIN DEBUG PostProc Filtros --- Filtros actualizados finales: {filtros_actualizado}")
    else:
        logging.debug("--- FIN DEBUG PostProc Filtros --- No se realizaron cambios significativos en los filtros.")
        
    return filtros_actualizado





# ---  FunciónV1 Funcional de Post-procesamiento para FiltrosInferidos ---
# def aplicar_postprocesamiento_filtros(
#     filtros: Optional[FiltrosInferidos],
#     preferencias: Optional[PerfilUsuario],
#     info_clima: Optional[InfoClimaUsuario] # <-- NUEVO PARÁMETRO 
# ) -> Optional[FiltrosInferidos]:
#     """
#     Aplica reglas de post-procesamiento que modifican FiltrosInferidos.
#     - Regla Mecánicas: Default si 'solo_electricos' es 'no' y falta.
#     - Regla Estética: Según 'valora_estetica'.
#     - Regla Premium: Según 'apasionado_motor' (nueva base).
#     - Regla Singular: Aditiva según 'apasionado_motor' y 'prefiere_diseno_exclusivo'.
#     Devuelve una instancia de FiltrosInferidos con cambios (puede ser la misma si no hay).
#     """
#     print("\n--- DEBUG DENTRO PostProc Filtros ---")
#     print(f"Recibido Prefs: {preferencias}")
#     print(f"Recibido Filtros (antes): {filtros}")
#     print(f"Recibido Info Clima: {info_clima}") # Para depuración, aunque no se usa en esta función
    
#     if filtros is None or preferencias is None:
#          print(f"DEBUG (PostProc Filtros) ► Entradas None, no se aplica post-procesamiento.")
#          return None 

#     filtros_actualizado = filtros.model_copy(deep=True)
#     cambios_realizados = False 

#     # --- Regla 2: Tipo de mecánica (como la tenías, asegúrate que es la lógica deseada) ---
#     solo_electricos_val = preferencias.solo_electricos
#     tipo_mecanica_actual = filtros_actualizado.tipo_mecanica

#     if is_yes(solo_electricos_val): # Si el usuario quiere SOLO eléctricos
#         # Forzar a BEV y REEV si no lo está ya o si es None
#         expected_electricas = sorted([TipoMecanica.BEV, TipoMecanica.REEV]) # Lista de Enums podriamos validar otros electricos validar con Teo
#         current_mecanicas_enums = filtros_actualizado.tipo_mecanica or [] # Lista de Enums o vacía

#         # Para comparar, es más fácil si ambos son sets de strings de los values
#         current_mecanicas_values_set = {m.value for m in current_mecanicas_enums}
#         expected_electricas_values_set = {m.value for m in expected_electricas}

#         if current_mecanicas_values_set != expected_electricas_values_set:
#             print(f"DEBUG (PostProc Filtros) ► Aplicando regla: solo_electricos='sí'. Estableciendo tipo_mecanica a BEV, REEV. (Anterior: {current_mecanicas_enums})")
#             filtros_actualizado.tipo_mecanica = [TipoMecanica.BEV, TipoMecanica.REEV]
#             cambios_realizados = True
#     elif isinstance(solo_electricos_val, str) and solo_electricos_val.strip().lower() == 'no':
#         # Si dijo explícitamente NO solo eléctricos Y no hay mecánicas, poner default
#         if _es_nulo_o_vacio(tipo_mecanica_actual):
#             print("DEBUG (PostProc Filtros) ► Aplicando regla: solo_electricos='no' y sin tipo_mecanica -> asignando default no eléctrico")
#             lista_mecanicas_default = [ # Ejemplo, ajusta esta lista
#                 TipoMecanica.GASOLINA, TipoMecanica.DIESEL, TipoMecanica.PHEVG,
#                 TipoMecanica.PHEVD, TipoMecanica.HEVG, TipoMecanica.HEVD,
#                 TipoMecanica.MHEVG, TipoMecanica.MHEVD,
#                 TipoMecanica.GLP, TipoMecanica.GNV]
#             filtros_actualizado.tipo_mecanica = lista_mecanicas_default
#             cambios_realizados = True
#         # --- NUEVA LÓGICA PARA FILTRAR GLP/GNV POR ZONA ---
#     if info_clima and info_clima.cp_valido_encontrado: # Solo si tenemos datos climáticos válidos
#         mecanicas_permitidas = list(filtros_actualizado.tipo_mecanica) if filtros_actualizado.tipo_mecanica else []
#         mecanicas_original_len = len(mecanicas_permitidas)

#             # Si CP NO pertenece a [zona_GLP] -> quitar tipo_mecanica [GLP]
#         if not info_clima.ZONA_GLP: # Asumiendo que False o None significa que no está en zona GLP
#             if TipoMecanica.GLP in mecanicas_permitidas:
#                 print(f"DEBUG (PostProc Filtros) ► CP no en ZONA_GLP. Eliminando GLP de tipo_mecanica.")
#                 mecanicas_permitidas.remove(TipoMecanica.GLP)
            
#             # Si CP NO pertenece a [zona_GNV] -> quitar tipo_mecanica [GNV]
#         if not info_clima.ZONA_GNV: # Asumiendo que False o None significa que no está en zona GNV
#             if TipoMecanica.GNV in mecanicas_permitidas:
#                     print(f"DEBUG (PostProc Filtros) ► CP no en ZONA_GNV. Eliminando GNV de tipo_mecanica.")
#                     mecanicas_permitidas.remove(TipoMecanica.GNV)
            
#         if len(mecanicas_permitidas) != mecanicas_original_len:
#                 filtros_actualizado.tipo_mecanica = mecanicas_permitidas if mecanicas_permitidas else None # Si queda vacía, poner None
#                 cambios_realizados = True
#     elif info_clima: # Se consultó el CP pero no se encontraron datos de zona o no era válido
#              print(f"DEBUG (PostProc Filtros) ► No se aplicarán filtros GLP/GNV por zona debido a info_clima no concluyente (cp_valido_encontrado={info_clima.cp_valido_encontrado}).")
#     else: # No hay info_clima en absoluto
#              print(f"DEBUG (PostProc Filtros) ► No hay info_clima disponible. No se aplicarán filtros GLP/GNV por zona.")
#     # --- FIN NUEVA LÓGICA GLP/GNV ---  
#     # --- Regla 3: Estética mínima según valora_estetica (como la tenías) ---
#     valora_estetica_val = preferencias.valora_estetica
#     estetica_target = 1.0 # Default si no valora o es None
#     if is_yes(valora_estetica_val):
#         estetica_target = 5.0
    
#     if filtros_actualizado.estetica_min != estetica_target:
#         print(f"DEBUG (PostProc Filtros) ► Aplicando regla estetica: de {filtros_actualizado.estetica_min} a {estetica_target} (valora_estetica='{valora_estetica_val}')")
#         filtros_actualizado.estetica_min = estetica_target
#         cambios_realizados = True
            
#     # --- LÓGICA MODIFICADA PARA PREMIUM_MIN ---
#     print(f"DEBUG PostProc Filtros: Evaluando premium_min. apasionado_motor='{preferencias.apasionado_motor}'")
#     premium_min_calculado = 1.0 # Valor base si no es apasionado
#     if is_yes(preferencias.apasionado_motor):
#         premium_min_calculado = 3.0
    
#     if filtros_actualizado.premium_min != premium_min_calculado:
#         print(f"DEBUG (PostProc Filtros) ► Aplicando regla premium: de {filtros_actualizado.premium_min} a {premium_min_calculado}")
#         filtros_actualizado.premium_min = premium_min_calculado
#         cambios_realizados = True
#     # --- LÓGICA MODIFICADA PARA SINGULAR_MIN (ADITIVA) ---
#     print(f"DEBUG PostProc Filtros: Evaluando singular_min. apasionado_motor='{preferencias.apasionado_motor}', prefiere_exclusivo='{preferencias.prefiere_diseno_exclusivo}'")
#     singular_min_calculado = 0.0 # Empezar desde cero

#     # Contribución de apasionado_motor
#     if is_yes(preferencias.apasionado_motor):
#         singular_min_calculado += 3.0
#         print(f"DEBUG PostProc Filtros: apasionado_motor='sí', suma +3.0 a singular_min. Subtotal: {singular_min_calculado}")
#     else: # 'no' o None
#         singular_min_calculado += 1.0
#         print(f"DEBUG PostProc Filtros: apasionado_motor!='sí', suma +1.0 a singular_min. Subtotal: {singular_min_calculado}")

#     # Contribución de prefiere_diseno_exclusivo
#     if is_yes(preferencias.prefiere_diseno_exclusivo):
#         singular_min_calculado += 3.0
#         print(f"DEBUG PostProc Filtros: prefiere_diseno_exclusivo='sí', suma +3.0 a singular_min. Total: {singular_min_calculado}")
#     else: # 'no' o None
#         singular_min_calculado += 1.0
#         print(f"DEBUG PostProc Filtros: prefiere_diseno_exclusivo!='sí', suma +1.0 a singular_min. Total: {singular_min_calculado}")
    
#     # Asegurar que no exceda límites (ej: 0.0 a 10.0)
#     # Y que el mínimo sea al menos 1.0 si la suma da 1.0
#     if singular_min_calculado < 1.0 and (is_yes(preferencias.apasionado_motor) or is_yes(preferencias.prefiere_diseno_exclusivo)):
#         # Si alguna preferencia positiva se activó, pero la suma es < 1, podría ser un caso raro.
#         # Podrías querer un mínimo absoluto si alguna de las condiciones es 'sí'.
#         # Por ahora, si la suma da 1.0 +1.0 = 2.0, está bien.
#         # Simplificando: si es menor que 1.0 pero debería haber algo de singularidad, pongamos 1.0.
#         pass

#     # Clamp a rango [0.0, 10.0] por si acaso, aunque con tus valores no se excede
#     singular_min_calculado = max(0.0, min(10.0, singular_min_calculado))

#     if filtros_actualizado.singular_min != singular_min_calculado:
#         print(f"DEBUG (PostProc Filtros) ► Aplicando regla singular (aditiva): de {filtros_actualizado.singular_min} a {singular_min_calculado}")
#         filtros_actualizado.singular_min = singular_min_calculado
#         cambios_realizados = True
#     print(f"--- FIN DEBUG DENTRO PostProc Filtros --- Filtros actualizados finales: {filtros_actualizado}")
#     # Devolver siempre el objeto (potencialmente) actualizado
#     return filtros_actualizado
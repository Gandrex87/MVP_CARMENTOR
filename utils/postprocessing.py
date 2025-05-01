# Separar responsabilidades: dejar al LLM lo fácil y completar lo crítico
# En lugar de depender de que el LLM devuelva la lista completa, se definen reglas de negocio fija:
# Este enfoque más robusto y estándar en producción:
# Combinar inferencia + reglas determinísticas para asegurar integridad del estado.

# utils/postprocessing.py
from utils.enums import Transmision , TipoMecanica
from typing import Optional, List
from graph.perfil.state import PerfilUsuario, FiltrosInferidos 
from .conversion import is_yes


# --- Helper interno para simplificar comprobaciones ---
def _es_nulo_o_vacio(valor):
    """Comprueba si el valor es None, string vacío o lista vacía."""
    # Comprobamos también si es float 0.0 como en la función original? Quizás no sea necesario.
    return valor is None or valor == "" or valor == []

# --- NUEVA Función de Post-procesamiento para PerfilUsuario ---

def aplicar_postprocesamiento_perfil(
    preferencias: Optional[PerfilUsuario]
) -> Optional[PerfilUsuario]:
    """
    Aplica reglas de post-procesamiento que modifican SOLO PerfilUsuario.
    - Regla: Si quiere solo eléctricos y no tiene preferencia de transmisión, 
             se asigna automática.
    
    Devuelve una NUEVA instancia de PerfilUsuario con los cambios aplicados, 
    o None si la entrada es None.
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
        # print("DEBUG (PostProc Perfil) ► No se aplicaron cambios de post-procesamiento al perfil.")
        return preferencias # Devolver el original para evitar crear objetos innecesarios


# --- NUEVA Función de Post-procesamiento para FiltrosInferidos ---

def aplicar_postprocesamiento_filtros(
    filtros: Optional[FiltrosInferidos],
    preferencias: Optional[PerfilUsuario] # Necesita el PerfilUsuario como contexto para las reglas
) -> Optional[FiltrosInferidos]:
    """
    Aplica reglas de post-procesamiento que modifican FiltrosInferidos,
    utilizando el PerfilUsuario como contexto.
    - Regla: Asignar mecánicas default si 'solo_electricos' es 'no' y no hay tipo_mecanica.
    - Regla: Asignar estetica_min según 'valora_estetica'.
    - Regla: Asignar premium_min/singular_min según 'apasionado_motor'.
    
    Devuelve una NUEVA instancia de FiltrosInferidos con los cambios aplicados,
    o None si alguna de las entradas es None.
    """
     # --- NUEVOS PRINTS DE DEPURACIÓN ---
    print("\n--- DEBUG DENTRO PostProc Filtros ---")
    print(f"Recibido Prefs: {preferencias}")
    print(f"Recibido Filtros (antes): {filtros}")
    # --- FIN NUEVOS PRINTS ---
    # Necesitamos ambos objetos para aplicar las reglas
    if filtros is None or preferencias is None:
         print(f"DEBUG (PostProc Filtros) ► Entradas None (filtros={filtros is None}, prefs={preferencias is None}), no se aplica post-procesamiento de filtros.")
         return filtros # Devuelve el objeto de filtros original (que podría ser None)

    # Trabajar sobre copias
    filtros_actualizado = filtros.model_copy(deep=True)
    # No modificamos preferencias, solo leemos de él
    
    cambios_realizados = False # Para seguimiento

    # --- Regla 2: Tipo de mecánica si 'solo_electricos' es 'no' y falta tipo_mecanica ---
    solo_electricos_val = preferencias.solo_electricos
    tipo_mecanica_actual = filtros_actualizado.tipo_mecanica

    # Comprobamos explícitamente 'no' (usar is_yes sería para 'sí') y si falta tipo_mecanica
    if isinstance(solo_electricos_val, str) and solo_electricos_val.strip().lower() == 'no' \
       and _es_nulo_o_vacio(tipo_mecanica_actual):
        
        print("DEBUG (PostProc Filtros) ► Aplicando regla: solo_electricos='no' y sin tipo_mecanica -> asignando default")
        # --- ¡IMPORTANTE! Revisa y ajusta esta lista default según tu criterio ---
        # ¿Incluimos BEV si dijo que NO quiere solo eléctricos? Probablemente no.
        # ¿Incluimos Diesel para ciudad? Quizás no.
        # ¿Cuáles son las opciones más comunes/seguras?
        lista_mecanicas_default = [
            TipoMecanica.GASOLINA, 
            TipoMecanica.DIESEL,
            TipoMecanica.PHEVG, # HEVG/HEVD
            TipoMecanica.PHEVD, # PHEVG/PHEVD
            TipoMecanica.GLP, 
            TipoMecanica.GNV

        ]
        # Asignamos la lista de ENUMS
        filtros_actualizado.tipo_mecanica = lista_mecanicas_default
        cambios_realizados = True

    # --- Regla 3: Estética mínima según valora_estetica ---
    
    valora_estetica_val = preferencias.valora_estetica
    
    print(f"DEBUG PostProc Filtros: Valor de valora_estetica_val = '{valora_estetica_val}' (Tipo: {type(valora_estetica_val)})")
    resultado_is_yes = is_yes(valora_estetica_val)
    print(f"DEBUG PostProc Filtros: Resultado de is_yes(valora_estetica_val) = {resultado_is_yes}")
    
    # Aplicamos la regla siempre para asegurar el valor correcto (1.0 o 5.0)
    if is_yes(valora_estetica_val):
        if filtros_actualizado.estetica_min != 5.0: # Aplicar solo si es diferente
            print("DEBUG (PostProc Filtros) ► Aplicando regla: valora_estetica='sí' -> estetica_min=5.0")
            filtros_actualizado.estetica_min = 5.0
            cambios_realizados = True
    else: # Cubre 'no' y None
        if filtros_actualizado.estetica_min != 1.0:
            print("DEBUG (PostProc Filtros) ► Aplicando regla: valora_estetica!='sí' -> estetica_min=1.0")
            filtros_actualizado.estetica_min = 1.0
            cambios_realizados = True

    # --- Regla 4: Premium y singularidad según apasionado_motor ¿ERES UN APASIONADO/A DEL MOTOR Y/O LA MOVILIDAD? ---
    apasionado_motor_val = preferencias.apasionado_motor
    print(f"DEBUG PostProc Filtros: Valor de apasionado_motor_val = '{apasionado_motor_val}' (Tipo: {type(apasionado_motor_val)})")
    resultado_is_yes = is_yes(apasionado_motor_val)
    print(f"DEBUG PostProc Filtros: Resultado de is_yes(apasionado_motor_val) = {resultado_is_yes}")
    
    # Aplicamos la regla siempre
    if is_yes(apasionado_motor_val):
        if filtros_actualizado.premium_min != 5.0 or filtros_actualizado.singular_min != 5.0:
            print("DEBUG (PostProc Filtros) ► Aplicando regla: apasionado_motor='sí' -> premium/singular_min=5.0")
            filtros_actualizado.premium_min = 5.0
            filtros_actualizado.singular_min = 5.0
            cambios_realizados = True
    else: # Cubre 'no' y None
        if filtros_actualizado.premium_min != 1.0 or filtros_actualizado.singular_min != 1.0:
            print("DEBUG (PostProc Filtros) ► Aplicando regla: apasionado_motor!='sí' -> premium/singular_min=1.0")
            filtros_actualizado.premium_min = 1.0
            filtros_actualizado.singular_min = 1.0
            cambios_realizados = True

    # Devolver el objeto actualizado si hubo cambios, o el original si no
    if cambios_realizados:
        print(f"DEBUG (PostProc Filtros) ► Filtros tras post-procesamiento: {filtros_actualizado}")
        return filtros_actualizado
    else:
        # print("DEBUG (PostProc Filtros) ► No se aplicaron cambios de post-procesamiento a los filtros.")
        return filtros # Devolver el original

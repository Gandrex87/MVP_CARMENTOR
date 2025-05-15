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


# --- NUEVA Función de Post-procesamiento para FiltrosInferidos ---
def aplicar_postprocesamiento_filtros(
    filtros: Optional[FiltrosInferidos],
    preferencias: Optional[PerfilUsuario] 
) -> Optional[FiltrosInferidos]:
    """
    Aplica reglas de post-procesamiento que modifican FiltrosInferidos.
    - Regla Mecánicas: Default si 'solo_electricos' es 'no' y falta.
    - Regla Estética: Según 'valora_estetica'.
    - Regla Premium: Según 'apasionado_motor' (nueva base).
    - Regla Singular: Aditiva según 'apasionado_motor' y 'prefiere_diseno_exclusivo'.
    Devuelve una instancia de FiltrosInferidos con cambios (puede ser la misma si no hay).
    """
    print("\n--- DEBUG DENTRO PostProc Filtros ---")
    print(f"Recibido Prefs: {preferencias}")
    print(f"Recibido Filtros (antes): {filtros}")
    
    if filtros is None or preferencias is None:
         print(f"DEBUG (PostProc Filtros) ► Entradas None, no se aplica post-procesamiento.")
         return filtros 

    filtros_actualizado = filtros.model_copy(deep=True)
    cambios_realizados = False 

    # --- Regla 2: Tipo de mecánica (como la tenías, asegúrate que es la lógica deseada) ---
    solo_electricos_val = preferencias.solo_electricos
    tipo_mecanica_actual = filtros_actualizado.tipo_mecanica

    if is_yes(solo_electricos_val): # Si el usuario quiere SOLO eléctricos
        # Forzar a BEV y REEV si no lo está ya o si es None
        expected_electricas = sorted([TipoMecanica.BEV, TipoMecanica.REEV]) # Lista de Enums podriamos validar otros electricos validar con Teo
        current_mecanicas_enums = filtros_actualizado.tipo_mecanica or [] # Lista de Enums o vacía

        # Para comparar, es más fácil si ambos son sets de strings de los values
        current_mecanicas_values_set = {m.value for m in current_mecanicas_enums}
        expected_electricas_values_set = {m.value for m in expected_electricas}

        if current_mecanicas_values_set != expected_electricas_values_set:
            print(f"DEBUG (PostProc Filtros) ► Aplicando regla: solo_electricos='sí'. Estableciendo tipo_mecanica a BEV, REEV. (Anterior: {current_mecanicas_enums})")
            filtros_actualizado.tipo_mecanica = [TipoMecanica.BEV, TipoMecanica.REEV]
            cambios_realizados = True
    elif isinstance(solo_electricos_val, str) and solo_electricos_val.strip().lower() == 'no':
        # Si dijo explícitamente NO solo eléctricos Y no hay mecánicas, poner default
        if _es_nulo_o_vacio(tipo_mecanica_actual):
            print("DEBUG (PostProc Filtros) ► Aplicando regla: solo_electricos='no' y sin tipo_mecanica -> asignando default no eléctrico")
            lista_mecanicas_default = [ # Ejemplo, ajusta esta lista
                TipoMecanica.GASOLINA, TipoMecanica.DIESEL, TipoMecanica.PHEVG,
                TipoMecanica.PHEVD, TipoMecanica.HEVG, TipoMecanica.HEVD,
                TipoMecanica.MHEVG, TipoMecanica.MHEVD,
                TipoMecanica.GLP, TipoMecanica.GNV
            ]
            filtros_actualizado.tipo_mecanica = lista_mecanicas_default
            cambios_realizados = True
    # Si solo_electricos_val es None, no hacemos nada con tipo_mecanica aquí,el LLM debería haber preguntado o inferido algo.

    # --- Regla 3: Estética mínima según valora_estetica (como la tenías) ---
    valora_estetica_val = preferencias.valora_estetica
    estetica_target = 1.0 # Default si no valora o es None
    if is_yes(valora_estetica_val):
        estetica_target = 5.0
    
    if filtros_actualizado.estetica_min != estetica_target:
        print(f"DEBUG (PostProc Filtros) ► Aplicando regla estetica: de {filtros_actualizado.estetica_min} a {estetica_target} (valora_estetica='{valora_estetica_val}')")
        filtros_actualizado.estetica_min = estetica_target
        cambios_realizados = True
            
    # --- LÓGICA MODIFICADA PARA PREMIUM_MIN ---
    print(f"DEBUG PostProc Filtros: Evaluando premium_min. apasionado_motor='{preferencias.apasionado_motor}'")
    premium_min_calculado = 1.0 # Valor base si no es apasionado
    if is_yes(preferencias.apasionado_motor):
        premium_min_calculado = 3.0
    
    if filtros_actualizado.premium_min != premium_min_calculado:
        print(f"DEBUG (PostProc Filtros) ► Aplicando regla premium: de {filtros_actualizado.premium_min} a {premium_min_calculado}")
        filtros_actualizado.premium_min = premium_min_calculado
        cambios_realizados = True
    # --- FIN LÓGICA PREMIUM_MIN ---

    # --- LÓGICA MODIFICADA PARA SINGULAR_MIN (ADITIVA) ---
    print(f"DEBUG PostProc Filtros: Evaluando singular_min. apasionado_motor='{preferencias.apasionado_motor}', prefiere_exclusivo='{preferencias.prefiere_diseno_exclusivo}'")
    singular_min_calculado = 0.0 # Empezar desde cero

    # Contribución de apasionado_motor
    if is_yes(preferencias.apasionado_motor):
        singular_min_calculado += 3.0
        print(f"DEBUG PostProc Filtros: apasionado_motor='sí', suma +3.0 a singular_min. Subtotal: {singular_min_calculado}")
    else: # 'no' o None
        singular_min_calculado += 1.0
        print(f"DEBUG PostProc Filtros: apasionado_motor!='sí', suma +1.0 a singular_min. Subtotal: {singular_min_calculado}")

    # Contribución de prefiere_diseno_exclusivo
    if is_yes(preferencias.prefiere_diseno_exclusivo):
        singular_min_calculado += 3.0
        print(f"DEBUG PostProc Filtros: prefiere_diseno_exclusivo='sí', suma +3.0 a singular_min. Total: {singular_min_calculado}")
    else: # 'no' o None
        singular_min_calculado += 1.0
        print(f"DEBUG PostProc Filtros: prefiere_diseno_exclusivo!='sí', suma +1.0 a singular_min. Total: {singular_min_calculado}")
    
    # Asegurar que no exceda límites (ej: 0.0 a 10.0)
    # Y que el mínimo sea al menos 1.0 si la suma da 1.0
    if singular_min_calculado < 1.0 and (is_yes(preferencias.apasionado_motor) or is_yes(preferencias.prefiere_diseno_exclusivo)):
        # Si alguna preferencia positiva se activó, pero la suma es < 1, podría ser un caso raro.
        # Podrías querer un mínimo absoluto si alguna de las condiciones es 'sí'.
        # Por ahora, si la suma da 1.0 +1.0 = 2.0, está bien.
        # Simplificando: si es menor que 1.0 pero debería haber algo de singularidad, pongamos 1.0.
        pass

    # Clamp a rango [0.0, 10.0] por si acaso, aunque con tus valores no se excede
    singular_min_calculado = max(0.0, min(10.0, singular_min_calculado))

    if filtros_actualizado.singular_min != singular_min_calculado:
        print(f"DEBUG (PostProc Filtros) ► Aplicando regla singular (aditiva): de {filtros_actualizado.singular_min} a {singular_min_calculado}")
        filtros_actualizado.singular_min = singular_min_calculado
        cambios_realizados = True
    # --- FIN LÓGICA SINGULAR_MIN ---

    print(f"--- FIN DEBUG DENTRO PostProc Filtros --- Filtros actualizados finales: {filtros_actualizado}")
    
    # Devolver siempre el objeto (potencialmente) actualizado
    return filtros_actualizado
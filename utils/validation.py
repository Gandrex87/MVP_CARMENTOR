# En utils/validation.py
from typing import Optional
from pydantic import ValidationError
from graph.perfil.state import PerfilUsuario, EconomiaUsuario, InfoPasajeros,DistanciaTrayecto
from utils.conversion import is_yes
import logging
logger = logging.getLogger(__name__)

# --- Función de Validación de Perfil (Definida anteriormente) ---
def check_perfil_usuario_completeness(prefs: Optional[PerfilUsuario]) -> bool:
    """
    Verifica si el PerfilUsuario está completo, siguiendo la misma lógica
    y orden que la función que genera las preguntas.
    """
    if prefs is None:
        return False

    # 1. Comprobación de campos básicos (en el mismo orden que las preguntas)
    campos_base = [
        "apasionado_motor", "valora_estetica", "coche_principal_hogar", "frecuencia_uso", 
        "distancia_trayecto", "circula_principalmente_ciudad", "uso_profesional", 
        "prefiere_diseno_exclusivo", "altura_mayor_190", "transporta_carga_voluminosa", 
        "arrastra_remolque", "aventura", "estilo_conduccion", "tiene_garage", 
        "tiene_punto_carga_propio", "solo_electricos", "prioriza_baja_depreciacion",
        "rating_fiabilidad_durabilidad", "rating_seguridad", "rating_comodidad", 
        "rating_impacto_ambiental", "rating_costes_uso", "rating_tecnologia_conectividad"
    ]
    for campo in campos_base:
        if getattr(prefs, campo, None) is None:
            # logging.debug(f"Validation fail: Campo base '{campo}' es None.")
            return False

    # 2. Comprobación de campos condicionales (lógica extraída de la función de preguntas)
    # Lógica de viajes largos
    if prefs.distancia_trayecto != DistanciaTrayecto.MAS_150_KM.value:
        if prefs.realiza_viajes_largos is None: return False
        if is_yes(prefs.realiza_viajes_largos) and prefs.frecuencia_viajes_largos is None: return False
    
    # Lógica de uso profesional
    if is_yes(prefs.uso_profesional) and prefs.tipo_uso_profesional is None: return False

    # Lógica de objetos especiales
    if is_yes(prefs.transporta_carga_voluminosa) and prefs.necesita_espacio_objetos_especiales is None: return False

    # Lógica de transmisión (¡CORREGIDO!)
    if not is_yes(prefs.solo_electricos) and prefs.transmision_preferida is None: return False

    # Lógica de garaje
    if is_yes(prefs.tiene_garage):
        if prefs.espacio_sobra_garage is None: return False
        if not is_yes(prefs.espacio_sobra_garage) and not prefs.problema_dimension_garage: return False
    else: # tiene_garage es 'no'
        if prefs.problemas_aparcar_calle is None: return False
        
    # Si todas las comprobaciones pasan, el perfil está completo
    return True


# --- función de Validación de Economía ---

def check_economia_completa(econ: Optional[EconomiaUsuario]) -> bool:
    """
    Verifica si un objeto EconomiaUsuario está lógicamente completo
    según las reglas de negocio (modo/submodo y campos requeridos).
    ¡Esta función AHORA contiene la lógica de validación estricta!
    """
    print("--- DEBUG CHECK ECONOMIA (Manual) ---") # <-- Nuevo Print
    print(f"Input econ object: {econ}") # <-- Nuevo Print
    
    if econ is None:
        print("DEBUG (Validation Economía Manual) ► Objeto EconomiaUsuario es None.")
        return False 

    modo = econ.modo
    submodo = econ.submodo # Puede ser None

    if modo is None:
        print("DEBUG (Validation Economía Manual) ► econ.modo es None.")
        return False # Si no hay modo, no está completo

    if modo == 1:
        # Modo 1: Requiere ingresos Y ahorro
        if econ.ingresos is not None \
            and econ.ahorro is not None\
            and econ.anos_posesion is not None: # <-- AÑADIDA ESTA CONDICIÓN:
            print("DEBUG (Validation Economía Manual) ► Modo 1 completo (ingresos,ahorro y años_posesion presentes).")
            return True
        else:
            # Imprimir qué falta específicamente puede ayudar a depurar
            missing = []
            if econ.ingresos is None: missing.append("ingresos")
            if econ.ahorro is None: missing.append("ahorro")
            if econ.anos_posesion is None: missing.append("anos_posesion")
            print(f"DEBUG (Validation Economía Manual) ► Modo 1 INCOMPLETO (faltan: {', '.join(missing)}).")
            return False
            
    elif modo == 2:
        # Modo 2: Requiere submodo válido
        if submodo not in (1, 2):
            print(f"DEBUG (Validation Economía Manual) ► Modo 2 INCOMPLETO (submodo inválido o None: {submodo}).")
            return False 
            
        if submodo == 1:
            # Modo 2, Submodo 1: Requiere pago_contado
            if econ.pago_contado is not None:
                print("DEBUG (Validation Economía Manual) ► Modo 2/Submodo 1 completo (pago_contado presente).")
                return True
            else:
                print(f"DEBUG (Validation Economía Manual) ► Modo 2/Submodo 1 INCOMPLETO (pago_contado={econ.pago_contado}).")
                return False
                
        elif submodo == 2:
            # Modo 2, Submodo 2: Requiere cuota_max (entrada es opcional)
            if econ.cuota_max is not None:
                print("DEBUG (Validation Economía Manual) ► Modo 2/Submodo 2 completo (cuota_max presente).")
                return True
            else:
                print(f"DEBUG (Validation Economía Manual) ► Modo 2/Submodo 2 INCOMPLETO (cuota_max={econ.cuota_max}).")
                return False
                
    else: 
        # Modo inválido (no debería pasar si Literal[1, 2] funciona)
        print(f"WARN (Validation Economía Manual) ► Modo desconocido: {modo}.")
        return False

    # Fallback por si alguna lógica no se cubrió (no debería llegar aquí)
    return False 


def check_pasajeros_completo(info: Optional[InfoPasajeros]) -> bool:
    """
    Verifica si la información de pasajeros está completa.
    Esta función es el "espejo" de la que genera las preguntas.
    """
    if not info:
        return False

    if info.suele_llevar_acompanantes is None:
        return False
    
    # Si el usuario no lleva acompañantes, la etapa está completa.
    if info.suele_llevar_acompanantes is False:
        return True
    
    # Si sí lleva, todos los campos siguientes deben estar rellenos.
    if (info.frecuencia_viaje_con_acompanantes is None or
        info.num_ninos_silla is None or
        info.num_otros_pasajeros is None):
        return False
        
    return True
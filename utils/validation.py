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



def check_economia_completa(econ: Optional[EconomiaUsuario]) -> bool:
    """
    --- VERSIÓN SIN 'anos_posesion' ---
    """
    if not econ or econ.presupuesto_definido is None:
        return False

    if econ.presupuesto_definido is False: # Modo "Asesoramiento"
        # Ahora solo necesitamos ingresos y ahorro.
        return all([
            econ.ingresos is not None,
            econ.ahorro is not None
        ])
    else: # Modo "Usuario Define"
        # La lógica para pago al contado o cuota máxima se mantiene igual.
        pago_contado_completo = econ.pago_contado is not None
        financiacion_completa = econ.cuota_max is not None
        
        return pago_contado_completo or financiacion_completa


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

def es_cp_valido(cp: Optional[str]) -> bool:
    """
    Valida si una cadena de texto es un código postal español válido.
    Retorna True si es una cadena de 5 dígitos, False en caso contrario.
    """
    if not cp:
        return False
    return cp.isdigit() and len(cp) == 5
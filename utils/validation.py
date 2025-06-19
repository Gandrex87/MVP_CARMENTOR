# En utils/validation.py (o donde prefieras)
from typing import Optional
from pydantic import ValidationError
from graph.perfil.state import PerfilUsuario, FiltrosInferidos, EconomiaUsuario, InfoPasajeros,DistanciaTrayecto
from utils.conversion import is_yes
import logging
logger = logging.getLogger(__name__)

# --- Función de Validación de Perfil (Definida anteriormente) ---
def check_perfil_usuario_completeness(prefs: Optional[PerfilUsuario]) -> bool:
    print(f"--- DEBUG CHECK PERFIL ---") # <-- Nuevo Print
    print(f"Input prefs object: {prefs}") # <-- Nuevo Print
    print(f"Input prefs type: {type(prefs)}") # <-- Nuevo Print
    if prefs is None:
        return False
    campos_obligatorios = [
        "apasionado_motor", "valora_estetica", "coche_principal_hogar" , "frecuencia_uso", "distancia_trayecto", "circula_principalmente_ciudad" , "uso_profesional", "prefiere_diseno_exclusivo", "altura_mayor_190", "peso_mayor_100",
        "transporta_carga_voluminosa", "arrastra_remolque","aventura", "estilo_conduccion", "tiene_garage", "tiene_punto_carga_propio", "solo_electricos", "transmision_preferida", "prioriza_baja_depreciacion","rating_fiabilidad_durabilidad", 
        "rating_seguridad","rating_comodidad", "rating_impacto_ambiental", "rating_costes_uso", "rating_tecnologia_conectividad", 
    ] # por ahora no va 
    for campo in campos_obligatorios:
        valor = getattr(prefs, campo, None)
        #print(f"Checking field '{campo}': value='{valor}', type={type(valor)}") # <-- Nuevo Print
        if valor is None or (isinstance(valor, str) and not valor.strip()):
             print(f"DEBUG (Validation Perfil) ► Campo '{campo}' está vacío/None.")
             return False
    # 0. distancia_trayecto    
    if prefs.distancia_trayecto is not None and prefs.distancia_trayecto != DistanciaTrayecto.MAS_150_KM.value:
        # Si el trayecto es corto/medio, la pregunta sobre viajes largos es obligatoria
        if prefs.realiza_viajes_largos is None:
            print("DEBUG (Validation Perfil) ► 'distancia_trayecto' es corta/media, pero 'realiza_viajes_largos' es None. Perfil INCOMPLETO.")
            return False  
        # Si la respuesta es 'sí', la frecuencia es obligatoria
        if is_yes(prefs.realiza_viajes_largos) and prefs.frecuencia_viajes_largos is None:
            print("DEBUG (Validation Perfil) ► 'realiza_viajes_largos' es 'sí', pero 'frecuencia_viajes_largos' es None. Perfil INCOMPLETO.")
            return False  
    
    # 1. tipo_uso_profesional
    if is_yes(prefs.uso_profesional): 
        if prefs.tipo_uso_profesional is None: # El tipo es Enum, Pydantic maneja valores inválidos
            print("DEBUG (Validation Perfil) ► 'uso_profesional' es 'sí', pero 'tipo_uso_profesional' es None. Perfil INCOMPLETO.")
            return False
    # 2. necesita_espacio_objetos_especiales
    if is_yes(prefs.transporta_carga_voluminosa):
        if prefs.necesita_espacio_objetos_especiales is None or \
           (isinstance(prefs.necesita_espacio_objetos_especiales, str) and not prefs.necesita_espacio_objetos_especiales.strip()):
            print("DEBUG (Validation Perfil) ► 'transporta_carga_voluminosa' es 'sí', pero 'necesita_espacio_objetos_especiales' es None/vacío. Perfil INCOMPLETO.")
            return False
    # 3. Lógica de Garaje/Aparcamiento
    if prefs.tiene_garage is not None: # Solo si ya se respondió a 'tiene_garage'
        if is_yes(prefs.tiene_garage): # Si SÍ tiene garaje
            if prefs.espacio_sobra_garage is None or \
               (isinstance(prefs.espacio_sobra_garage, str) and not prefs.espacio_sobra_garage.strip()):
                print("DEBUG (Validation Perfil) ► 'tiene_garage' es 'sí', pero 'espacio_sobra_garage' es None/vacío. Perfil INCOMPLETO.")
                return False
            if is_yes(prefs.espacio_sobra_garage) is False: # Si NO tiene espacio de sobra
                # problema_dimension_garage es List[DimensionProblematica] o None
                if prefs.problema_dimension_garage is None or not prefs.problema_dimension_garage: # Si es None o lista vacía
                    print("DEBUG (Validation Perfil) ► 'espacio_sobra_garage' es 'no', pero 'problema_dimension_garage' es None/vacío. Perfil INCOMPLETO.")
                    return False
        else: # Si NO tiene garaje (tiene_garage es 'no')
            if prefs.problemas_aparcar_calle is None or \
               (isinstance(prefs.problemas_aparcar_calle, str) and not prefs.problemas_aparcar_calle.strip()):
                print("DEBUG (Validation Perfil) ► 'tiene_garage' es 'no', pero 'problemas_aparcar_calle' es None/vacío. Perfil INCOMPLETO.")
                return False
    # Si prefs.tiene_garage es None, ya fue capturado por el bucle de campos_base_obligatorios
    print("DEBUG (Validation Perfil) ► Todos los campos obligatorios del perfil están presentes.")
    return True

# --- Función de Validación de Filtros ---
def check_filtros_completos(filtros: Optional[FiltrosInferidos]) -> bool:
    """
    Verifica si un objeto FiltrosInferidos tiene los campos esenciales 
    (principalmente tipo_mecanica) para proceder a la etapa de economía.
    """
    if filtros is None:
        print("DEBUG (Validation Filtros) ► Objeto FiltrosInferidos es None.")
        return False # No hay objeto de filtros, no está completo

    # Define qué filtros consideras OBLIGATORIOS para pasar a economía.
    # Por ahora, el más crítico es tipo_mecanica.
    campos_obligatorios = ["tipo_mecanica"] 

    for campo in campos_obligatorios:
        valor = getattr(filtros, campo, None)
        
        # Validación específica para tipo_mecanica (lista)
        if campo == "tipo_mecanica":
            # Consideramos incompleto si es None O si es una lista vacía []
            if valor is None or not valor: # not valor cubre el caso de lista vacía
                 print(f"DEBUG (Validation Filtros) ► Campo '{campo}' es None o lista vacía.")
                 return False # Filtro obligatorio ausente o vacío
        
        # Validación para otros campos si los añades a campos_obligatorios
        # elif campo == "otro_campo_obligatorio":
        #    if valor is None or (isinstance(valor, str) and not valor.strip()):
        #         print(f"DEBUG (Validation Filtros) ► Campo '{campo}' está vacío/None.")
        #         return False 

    # Si todos los campos obligatorios revisados están bien:
    print("DEBUG (Validation Filtros) ► Todos los campos obligatorios de filtros ('tipo_mecanica') están presentes y válidos.")
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
    Verifica si la información de pasajeros está completa según el nuevo flujo.
    """
    # logger.debug("--- DEBUG CHECK PASAJEROS ---")
    if info is None:
        logger.debug("DEBUG (Validation Pasajeros) ► Objeto InfoPasajeros es None. INCOMPLETO.")
        return False

    # Imprimir el objeto para depurar
    # if hasattr(info, "model_dump_json"):
    #     logger.debug(f"Input info pasajeros: {info.model_dump_json(indent=2)}")
    # else:
    #     logger.debug(f"Input info pasajeros: {info}")

    # 1. Verificar el campo principal: suele_llevar_acompanantes
    if info.suele_llevar_acompanantes is None:
        logger.debug("DEBUG (Validation Pasajeros) ► 'suele_llevar_acompanantes' es None. INCOMPLETO.")
        return False

    # 2. Si no suele llevar acompañantes, se considera completo en esta etapa
    if info.suele_llevar_acompanantes is False:
        # En este caso, el nodo recopilar_info_pasajeros_node debería haber inferido:
        # info.frecuencia = "nunca"
        # info.num_ninos_silla = 0
        # info.num_otros_pasajeros = 0
        # Y el LLM debería haber devuelto tipo_mensaje="CONFIRMACION"
        logger.debug("DEBUG (Validation Pasajeros) ► 'suele_llevar_acompanantes' es False. Considerado COMPLETO para el flujo de preguntas.")
        return True

    # 3. Si SÍ suele llevar acompañantes, los siguientes campos son necesarios:
    if info.suele_llevar_acompanantes is True:
        if info.frecuencia_viaje_con_acompanantes is None:
            logger.debug("DEBUG (Validation Pasajeros) ► 'suele_llevar_acompanantes' es True, pero 'frecuencia_viaje_con_acompanantes' es None. INCOMPLETO.")
            return False
        
        # composicion_pasajeros_texto es un campo de ayuda para el LLM, no estrictamente
        # necesario para la completitud si los campos numéricos están llenos.
        # Pero si está vacío y los números también, es incompleto.

        if info.num_ninos_silla is None:
            logger.debug("DEBUG (Validation Pasajeros) ► 'suele_llevar_acompanantes' es True, pero 'num_ninos_silla' es None. INCOMPLETO.")
            return False
        
        if info.num_otros_pasajeros is None:
            logger.debug("DEBUG (Validation Pasajeros) ► 'suele_llevar_acompanantes' es True, pero 'num_otros_pasajeros' es None. INCOMPLETO.")
            return False
            
        # Adicionalmente, el campo 'frecuencia' (el general) debería tener un valor
        # si 'frecuencia_viaje_con_acompanantes' lo tiene.
        if info.frecuencia is None and info.frecuencia_viaje_con_acompanantes is not None:
             logger.debug("DEBUG (Validation Pasajeros) ► 'frecuencia_viaje_con_acompanantes' tiene valor, pero 'frecuencia' general es None. Considerado INCOMPLETO para la lógica final (aunque el LLM debería inferirlo).")
             # Esto podría ser un punto donde el LLM no infirió 'frecuencia' correctamente.
             # Sin embargo, para el flujo de *preguntas*, si los campos anteriores están, se podría considerar completo
             # y dejar que el nodo de recopilación infiera 'frecuencia'.
             # Por ahora, lo marcamos como incompleto si 'frecuencia' falta.
             return False


    logger.debug("DEBUG (Validation Pasajeros) ► Todos los campos necesarios de InfoPasajeros están presentes según el flujo. COMPLETO.")
    return True
# En utils/validation.py (o donde prefieras)
from typing import Optional
from pydantic import ValidationError
from graph.perfil.state import PerfilUsuario, FiltrosInferidos, EconomiaUsuario, InfoPasajeros
from utils.conversion import is_yes

# --- Función de Validación de Perfil (Definida anteriormente) ---
def check_perfil_usuario_completeness(prefs: Optional[PerfilUsuario]) -> bool:
    print(f"--- DEBUG CHECK PERFIL ---") # <-- Nuevo Print
    print(f"Input prefs object: {prefs}") # <-- Nuevo Print
    print(f"Input prefs type: {type(prefs)}") # <-- Nuevo Print
    if prefs is None:
        return False
    campos_obligatorios = [
        "apasionado_motor", "valora_estetica", "coche_principal_hogar" , "uso_profesional", "prefiere_diseno_exclusivo", "altura_mayor_190", "peso_mayor_100",
        "transporta_carga_voluminosa", "arrastra_remolque","aventura",  "solo_electricos",  "prioriza_baja_depreciacion","transmision_preferida","rating_fiabilidad_durabilidad", 
        "rating_seguridad","rating_comodidad", "rating_impacto_ambiental", "rating_tecnologia_conectividad", "rating_costes_uso"
    ] # por ahora no va 
    for campo in campos_obligatorios:
        valor = getattr(prefs, campo, None)
        #print(f"Checking field '{campo}': value='{valor}', type={type(valor)}") # <-- Nuevo Print
        if valor is None or (isinstance(valor, str) and not valor.strip()):
             print(f"DEBUG (Validation Perfil) ► Campo '{campo}' está vacío/None.")
             return False
    # Si uso_profesional es 'sí', entonces tipo_uso_profesional también es obligatorio
    if is_yes(prefs.uso_profesional): # Usar is_yes para manejar 'sí', 'si', etc.
        if prefs.tipo_uso_profesional is None or \
           not str(prefs.tipo_uso_profesional).strip(): # Verificar que no sea cadena vacía si es str
            print("DEBUG (Validation Perfil) ► 'uso_profesional' es 'sí', pero 'tipo_uso_profesional' está vacío/None. Perfil INCOMPLETO.")
            return False
    # --- NUEVA COMPROBACIÓN CONDICIONAL PARA ESPACIO OBJETOS ESPECIALES ---
    if is_yes(prefs.transporta_carga_voluminosa):
        if prefs.necesita_espacio_objetos_especiales is None:
            print("DEBUG (Validation Perfil) ► 'transporta_carga_voluminosa' es 'sí', pero 'necesita_espacio_objetos_especiales' es None. Perfil INCOMPLETO.")
            return False
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


# --- Función de Validación de Pasajeros ---
def check_pasajeros_completo(info: Optional[InfoPasajeros]) -> bool:
    """
    Verifica si la información sobre pasajeros está completa.
    - Si frecuencia es 'nunca', se considera completo.
    - Si frecuencia es 'ocasional' o 'frecuente', requiere tener valores 
      (incluso 0) para num_ninos_silla y num_otros_pasajeros.
    - Si falta frecuencia, no está completo.
    """
    print("--- DEBUG CHECK PASAJEROS ---")
    print(f"Input info pasajeros: {info}")
    
    if info is None:
        print("DEBUG (Validation Pasajeros) ► Objeto InfoPasajeros es None.")
        return False # No hay objeto, no está completo

    frecuencia = info.frecuencia
    num_ninos_silla = info.num_ninos_silla
    num_otros_pasajeros = info.num_otros_pasajeros

    if frecuencia is None:
        print("DEBUG (Validation Pasajeros) ► info.frecuencia es None.")
        return False # Si no sabemos la frecuencia, no está completo

    if frecuencia == "nunca":
        # Si nunca lleva pasajeros, no necesitamos saber cuántos niños/otros.
        print("DEBUG (Validation Pasajeros) ► Frecuencia es 'nunca'. Considerado COMPLETO.")
        return True 
    elif frecuencia in ["ocasional", "frecuente"]:
        # Si lleva pasajeros ocasional o frecuentemente, necesitamos saber cuántos.
        # Comprobamos que ambos campos numéricos NO sean None.
        if num_ninos_silla is not None and num_otros_pasajeros is not None:
            print(f"DEBUG (Validation Pasajeros) ► Frecuencia='{frecuencia}'. Niños silla y otros pasajeros tienen valor. Considerado COMPLETO.")
            return True
        else:
            missing = []
            if num_ninos_silla is None: missing.append("num_ninos_silla")
            if num_otros_pasajeros is None: missing.append("num_otros_pasajeros")
            print(f"DEBUG (Validation Pasajeros) ► Frecuencia='{frecuencia}'. Faltan datos: {', '.join(missing)}. Considerado INCOMPLETO.")
            return False
    else:
        # Caso inesperado para frecuencia (no debería ocurrir con Literal)
        print(f"WARN (Validation Pasajeros) ► Valor de frecuencia inesperado: '{frecuencia}'. Considerado INCOMPLETO.")
        return False
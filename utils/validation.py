# En utils/validation.py (o donde prefieras)
from typing import Optional
from pydantic import ValidationError
from graph.perfil.state import PerfilUsuario, FiltrosInferidos, EconomiaUsuario # Ajusta ruta

# --- Función de Validación de Perfil (Definida anteriormente) ---
def check_perfil_usuario_completeness(prefs: Optional[PerfilUsuario]) -> bool:
    print(f"--- DEBUG CHECK PERFIL ---") # <-- Nuevo Print
    print(f"Input prefs object: {prefs}") # <-- Nuevo Print
    print(f"Input prefs type: {type(prefs)}") # <-- Nuevo Print
    if prefs is None:
        return False
    campos_obligatorios = [
        "altura_mayor_190", "peso_mayor_100", "uso_profesional", 
        "valora_estetica", "solo_electricos", "transmision_preferida", 
        "apasionado_motor", "aventura"
    ]
    for campo in campos_obligatorios:
        valor = getattr(prefs, campo, None)
        print(f"Checking field '{campo}': value='{valor}', type={type(valor)}") # <-- Nuevo Print
        if valor is None or (isinstance(valor, str) and not valor.strip()):
             print(f"DEBUG (Validation Perfil) ► Campo '{campo}' está vacío/None.")
             return False
    print("DEBUG (Validation Perfil) ► Todos los campos obligatorios del perfil están presentes.")
    return True

# --- NUEVA Función de Validación de Filtros ---
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

# En utils/validation.py

# --- NUEVA Función de Validación de Economía ---

# --- VERSIÓN REESCRITA de check_economia_completa ---
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
        if econ.ingresos is not None and econ.ahorro is not None:
            print("DEBUG (Validation Economía Manual) ► Modo 1 completo (ingresos y ahorro presentes).")
            return True
        else:
            print(f"DEBUG (Validation Economía Manual) ► Modo 1 INCOMPLETO (ingresos={econ.ingresos}, ahorro={econ.ahorro}).")
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
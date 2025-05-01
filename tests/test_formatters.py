# tests/test_formatters.py

import pytest
# Ajusta rutas de importación
from utils.formatters import formatear_preferencias_en_tabla
from graph.perfil.state import PerfilUsuario, FiltrosInferidos, EconomiaUsuario
from utils.enums import Transmision, NivelAventura, TipoMecanica # Importa Enums

# ---- Pruebas para formatear_preferencias_en_tabla ----

# --- Caso 1: Solo Preferencias Básicas ---
def test_formatear_tabla_solo_prefs_basicas():
    prefs = PerfilUsuario(
        solo_electricos="no",
        uso_profesional="no",
        altura_mayor_190="no",
        peso_mayor_100="no",
        valora_estetica="sí",
        transmision_preferida=Transmision.AUTOMATICO,
        apasionado_motor="no",
        aventura=NivelAventura.ninguna
    )
    resultado = formatear_preferencias_en_tabla(preferencias=prefs)
    
    print(f"\nResultado Tabla (Prefs Básicas):\n{resultado}") # Imprimir para depuración visual

    # Verificar cabecera y algunas filas clave de preferencias
    assert "✅ He entendido lo siguiente sobre tus preferencias:" in resultado
    assert "| Preferencia             | Valor                      |" in resultado
    assert "| Tipo de coche           | No necesariamente eléctrico |" in resultado # is_yes(no) -> False
    assert "| Uso                     | Particular |" in resultado # is_yes(no) -> False
    assert "| Estética                | Importante |" in resultado # is_yes(sí) -> True
    assert "| Transmisión preferida   | Automático |" in resultado # Enum.value.capitalize()
    assert "| Apasionado del motor    | No |" in resultado # is_yes(no) -> False
    assert "| Aventura                | Ninguna |" in resultado # Enum.value.capitalize()
    # Verificar que NO aparezcan las secciones de filtros y economía
    assert "🎯 Filtros técnicos inferidos:" not in resultado
    assert "💰 Economía del usuario:" not in resultado
    assert "Espero que este resumen te sea útil." in resultado # Verificar mensaje final

# --- Caso 2: Preferencias y Filtros (con listas) ---
def test_formatear_tabla_con_filtros():
    prefs = PerfilUsuario(solo_electricos="sí", valora_estetica="no", apasionado_motor="sí") # Otros None
    filtros = FiltrosInferidos(
        tipo_mecanica=[TipoMecanica.BEV], # Lista con un Enum
        estetica_min=1.0,
        premium_min=5.0,
        singular_min=5.0,
        tipo_carroceria=["SUV", "COUPE"] # Lista de strings (como vendría de RAG quizás)
    )
    resultado = formatear_preferencias_en_tabla(preferencias=prefs, filtros=filtros)
    
    print(f"\nResultado Tabla (Prefs+Filtros):\n{resultado}")

    # Verificar sección preferencias
    assert "| Tipo de coche           | Eléctrico |" in resultado # is_yes(sí) -> True
    assert "| Estética                | No prioritaria |" in resultado # is_yes(no) -> False
    assert "| Apasionado del motor    | Sí |" in resultado # is_yes(sí) -> True
    # Verificar sección filtros
    assert "🎯 Filtros técnicos inferidos:" in resultado
    assert "| Filtro técnico        | Valor                            |" in resultado
    assert "| Tipo de mecánica     | BEV |" in resultado # Lista de enums formateada
    assert "| Tipo de carrocería   | SUV, COUPE |" in resultado # Lista de strings formateada
    assert "| Estética mínima      | 1.0 |" in resultado
    assert "| Premium mínima       | 5.0 |" in resultado
    # Verificar ausencia de economía
    assert "💰 Economía del usuario:" not in resultado

# --- Caso 3: Todo Incluido - Economía Modo 1 ---
def test_formatear_tabla_completa_econ_modo1():
    prefs = PerfilUsuario(solo_electricos="no", uso_profesional="sí", aventura=NivelAventura.ocasional)
    filtros = FiltrosInferidos(tipo_mecanica=[TipoMecanica.HEVG], tipo_carroceria=["MONOVOLUMEN"])
    economia = EconomiaUsuario(modo=1, ingresos=60000.50, ahorro=15000) # Modo 1 completo
    
    resultado = formatear_preferencias_en_tabla(preferencias=prefs, filtros=filtros, economia=economia)
    print(f"\nResultado Tabla (Completa Econ 1):\n{resultado}")

    assert "✅ He entendido lo siguiente" in resultado
    assert "| Uso                     | Uso profesional |" in resultado
    assert "| Aventura                | Ocasional |" in resultado
    assert "🎯 Filtros técnicos inferidos" in resultado
    assert "| Tipo de mecánica     | HEVG |" in resultado
    assert "| Tipo de carrocería   | MONOVOLUMEN |" in resultado
    # Verificar sección economía MODO 1
    assert "💰 Economía del usuario:" in resultado
    assert "| Modo               | Asesor Financiero |" in resultado
    assert "| Ingresos anuales   | 60.000 € |" in resultado # Formato número
    assert "| Ahorro disponible  | 15.000 € |" in resultado # Formato número
    assert "Cuota máxima" not in resultado # No debe aparecer cuota
    assert "Presupuesto Contado" not in resultado # No debe aparecer pago contado

# --- Caso 4: Todo Incluido - Economía Modo 2 Submodo 2 ---
def test_formatear_tabla_completa_econ_modo2_sub2():
    prefs = PerfilUsuario(solo_electricos="no")
    filtros = FiltrosInferidos(tipo_mecanica=[TipoMecanica.GASOLINA])
    # Modo 2, submodo 2 completo con entrada
    economia = EconomiaUsuario(modo=2, submodo=2, cuota_max=350.99, entrada=5000) 
    
    resultado = formatear_preferencias_en_tabla(preferencias=prefs, filtros=filtros, economia=economia)
    print(f"\nResultado Tabla (Completa Econ 2/2):\n{resultado}")

    assert "✅ He entendido lo siguiente" in resultado
    assert "🎯 Filtros técnicos inferidos" in resultado
    # Verificar sección economía MODO 2 / SUBMODO 2
    assert "💰 Economía del usuario:" in resultado
    assert "| Modo               | Presupuesto Definido |" in resultado
    assert "| Tipo de Pago       | Cuotas Mensuales |" in resultado
    assert "| Cuota máxima       | 351 €/mes |" in resultado # Formato número redondeado y texto
    assert "| Entrada inicial    | 5.000 € |" in resultado # Formato número
    assert "Ingresos anuales" not in resultado # No debe aparecer ingresos
    assert "Ahorro disponible" not in resultado # No debe aparecer ahorro
    assert "Presupuesto Contado" not in resultado # No debe aparecer pago contado

# --- Caso 5: Economía Modo 2 Submodo 1 ---
def test_formatear_tabla_completa_econ_modo2_sub1():
    prefs = PerfilUsuario(solo_electricos="no")
    filtros = FiltrosInferidos(tipo_mecanica=[TipoMecanica.GASOLINA])
    # Modo 2, submodo 1 completo
    economia = EconomiaUsuario(modo=2, submodo=1, pago_contado=22000) 
    
    resultado = formatear_preferencias_en_tabla(preferencias=prefs, filtros=filtros, economia=economia)
    print(f"\nResultado Tabla (Completa Econ 2/1):\n{resultado}")

    assert "💰 Economía del usuario:" in resultado
    assert "| Modo               | Presupuesto Definido |" in resultado
    assert "| Tipo de Pago       | Pago Contado |" in resultado
    assert "| Presupuesto Contado| 22.000 € |" in resultado # Formato número
    assert "Cuota máxima" not in resultado # No debe aparecer cuota
    assert "Entrada inicial" not in resultado # No debe aparecer entrada
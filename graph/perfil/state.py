from typing import TypedDict
from typing import List, Optional, Annotated, Literal
from langchain_core.messages import HumanMessage, BaseMessage,AIMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, model_validator
from utils.enums import Transmision, TipoMecanica, NivelAventura, TipoUsoProfesional, DimensionProblematica, EstiloConduccion,FrecuenciaUso , DistanciaTrayecto, FrecuenciaViajesLargos
from typing import Literal, Optional


# 🧠 Modelos de Datos (InfoClimaUsuario, PerfilUsuario, FiltrosInferidos, EconomiaUsuario): Estos modelos definen la información que quieres recopilar.
   
   
# Las claves aquí deben coincidir con los nombres de tus columnas en la tabla zona_climas
class InfoClimaUsuario(BaseModel):
    MUNICIPIO_ZBE: bool = False # Default a False
    ZONA_LLUVIAS: bool = False
    ZONA_NIEBLAS: bool = False
    ZONA_NIEVE: bool = False
    ZONA_CLIMA_MONTA: bool = False
    ZONA_GLP: bool = False
    ZONA_GNV: bool = False
    cp_valido_encontrado: bool = Field(default=False, description="Indica si el CP se procesó y se encontró en al menos una categoría o es válido.")
    codigo_postal_consultado: Optional[str] = Field(default=None, description="El CP que se consultó.") 
        
class PerfilUsuario(BaseModel):
    # Añadir default=None a todos los Optional que no lo tenían
    apasionado_motor : Optional[str] = Field(default=None, description="¿Eres un apasionado/a del motor y/o la movilidad? Responde 'sí' o 'no'")
    valora_estetica: Optional[str] = Field(default=None, description="¿Valora la estética del coche? Responde 'sí' o 'no'")
    coche_principal_hogar: Optional[str] = Field(default=None,description="¿Será el coche principal del hogar? Responde 'sí' o 'no'")
     # --- NUEVOS CAMPOS PARA FRECUENCIA DE USO Y DISTANCIA ---
    frecuencia_uso: Optional[FrecuenciaUso] = Field(default=None, description="Frecuencia con la que el usuario usará el coche semanalmente.")
    distancia_trayecto: Optional[DistanciaTrayecto] = Field(default=None, description="Distancia del trayecto más frecuente o habitual en kilómetros.")
    realiza_viajes_largos: Optional[str] = Field(default=None, description="¿El usuario realiza viajes largos (>150km) además de su trayecto habitual? Responde 'sí' o 'no'")
    frecuencia_viajes_largos: Optional[FrecuenciaViajesLargos] = Field(default=None,description="Si realiza viajes largos, ¿con qué frecuencia lo hace?" )
    circula_principalmente_ciudad: Optional[str] = Field(
        default=None,
        description="¿El usuario circula principalmente por ciudad? Responde 'sí' o 'no'"
    )
    uso_profesional: Optional[str] = Field(default=None, description="¿Usará el coche para trabajo? Responde 'sí' o 'no'")
    tipo_uso_profesional: Optional[TipoUsoProfesional] = Field(default=None, description="Si el uso profesional es 'sí', especifica si es para 'pasajeros', 'carga' o 'mixto'")
    prefiere_diseno_exclusivo: Optional[str] = Field(default=None,description="¿Prefiere un diseño exclusivo/diferenciador ('sí') o algo más discreto ('no')?")
    altura_mayor_190: Optional[str] = Field(default=None, description="¿El usuario mide más de 1.90 metros? Responde 'sí' o 'no'")
    peso_mayor_100: Optional[str] = Field(default=None, description="¿El usuario pesa más de 100 kg? Responde 'sí' o 'no'")
    transporta_carga_voluminosa: Optional[str] = Field(default=None, description="¿Transporta con frecuencia equipaje o carga voluminosa? Responde 'sí' o 'no'") #acostumbra a viajar con mucho equipaje
    necesita_espacio_objetos_especiales: Optional[str] = Field(default=None, description="Si transporta carga, ¿necesita espacio para objetos de dimensiones especiales (bicicletas, etc.)? Responde 'sí' o 'no'")    
    arrastra_remolque: Optional[str] = Field(default=None, description="¿Va a arrastrar remolque pesado o caravana? Responde 'sí' o 'no'" )
     # --- NUEVOS CAMPOS PARA GARAJE/APARCAMIENTO ---
    tiene_garage: Optional[str] = Field(default=None, description="¿Tiene garaje o plaza de aparcamiento propia? Responde 'sí' o 'no'" )
    problemas_aparcar_calle: Optional[str] = Field(default=None,description="Si no tiene garaje, ¿suele tener problemas para aparcar en la calle? Responde 'sí' o 'no'")
    espacio_sobra_garage: Optional[str] = Field(default=None, description="Si tiene garaje, ¿tiene espacio de sobra? Responde 'sí' o 'no'")
    problema_dimension_garage: Optional[List[DimensionProblematica]] = Field(default=None,description="Si no tiene espacio de sobra en garaje, ¿cuál es la dimensión problemática principal (largo, ancho, alto)? Puede ser una lista.")
    tiene_punto_carga_propio: Optional[str] = Field(default=None, description="¿El usuario tiene un punto de carga para vehículo eléctrico en propiedad? Responde 'sí' o 'no'" )
    aventura: Optional[NivelAventura] = Field(default=None,description="¿Qué nivel de aventura buscas con tu vehículo: 'ninguna', 'ocasional' o 'extrema'?")
    estilo_conduccion: Optional[EstiloConduccion] = Field(default=None, description="Estilo de conducción preferido: tranquilo, deportivo o mixto.")
    solo_electricos: Optional[str] = Field(default=None, description="¿Quiere solo coches eléctricos? Responde 'sí' o 'no'")
    prioriza_baja_depreciacion: Optional[str] = Field(default=None, description="¿Es importante que la depreciación del coche sea lo más baja posible? Responde 'sí' o 'no'")
    transmision_preferida: Optional[Transmision] = Field(default=None, description="¿Qué transmisión prefieres: automático, manual o ambos?")
    # --- NUEVOS CAMPOS DE RATING (0-10) ---
    rating_fiabilidad_durabilidad: Optional[int] = Field( default=None, ge=0, le=10,description="Importancia de Fiabilidad y Durabilidad (0-10).")  # ge=greater or equal, le=less or equal
    rating_seguridad: Optional[int] = Field(default=None, ge=0, le=10, description="Importancia de la Seguridad (0-10).")
    rating_comodidad: Optional[int] = Field(default=None, ge=0, le=10, description="Importancia de la Comodidad (0-10)." )
    rating_impacto_ambiental: Optional[int] = Field(default=None, ge=0, le=10,description="Importancia del Bajo Impacto Medioambiental (0-10)."  )
    rating_tecnologia_conectividad: Optional[int] = Field(default=None, ge=0, le=10, description="Importancia de la Tecnología y Conectividad (0-10).")
    rating_costes_uso: Optional[int] = Field( default=None, ge=0, le=10, description="Importancia de Costes de Uso y Mantenimiento Reducidos (0-10).") 
    
    # ConfigDict se mantiene igual (recuerda quitar ignored_types si no lo hiciste)
    class ConfigDict:
        use_enum_values = True


# --- Modelo Pydantic para InfoPasajeros (MODIFICADO) ---
class InfoPasajeros(BaseModel):
    # NUEVOS CAMPOS PARA EL FLUJO DE PREGUNTAS
    suele_llevar_acompanantes: Optional[bool] = Field(
        default=None, 
        description="¿El usuario suele llevar acompañantes? (true/false)"
    )
    frecuencia_viaje_con_acompanantes: Optional[Literal["ocasional", "frecuente"]] = Field(
        default=None,
        description="Si suele llevar acompañantes, ¿con qué frecuencia? ('ocasional' o 'frecuente')"
    )
    composicion_pasajeros_texto: Optional[str] = Field(
        default=None,
        description="Respuesta textual del usuario a la pregunta sobre la composición de los pasajeros (ej: 'dos niños y un adulto', 'tres adultos')."
    )
    
    # CAMPO EXISTENTE: se inferirá de los nuevos o se preguntará si es necesario
    frecuencia: Optional[Literal["nunca", "ocasional", "frecuente"]] = Field(
        default=None, 
        description="Frecuencia general con la que viaja con pasajeros (inferido o preguntado)."
    )
    
    # CAMPOS EXISTENTES: se inferirán de composicion_pasajeros_texto y la pregunta de sillas
    num_ninos_silla: Optional[int] = Field(
        default=None, 
        ge=0, 
        description="Número de niños que necesitan silla infantil."
    )
    num_otros_pasajeros: Optional[int] = Field(
        default=None, 
        ge=0, 
        description="Número de otros pasajeros (adultos o niños sin silla), sin contar al conductor."
    )

    class ConfigDict:
        use_enum_values = True # Para que los Literal se traten como sus valores

class FiltrosInferidos(BaseModel):
    #batalla_min: Optional[float] = Field(default=None, description="Valor mínimo de batalla recomendado (rango: 1500.0 a 4490.0 mm). Relevante si el usuario mide más de 189 cm.")
    #indice_altura_interior_min: Optional[float] = Field(default=None, description="Valor mínimo de índice de altura interior recomendado (rango: 0.90 a 3.020). Relevante si el usuario mide más de 189 cm.")
    #estetica_min: Optional[float] = Field(default=None, description="Mínimo valor de estética recomendado (0.0 a 10.0)")
    tipo_mecanica: Optional[List[TipoMecanica]] = Field(default=None, description="Lista de motorizaciones recomendadas")
    #premium_min: Optional[float] = Field(default=None, description="Mínimo valor de premium recomendado (0.0 a 10.0)")
    #singular_min: Optional[float] = Field(default=None, description="Mínimo valor de singularidad recomendado (0.0 a 10.0)")
    tipo_carroceria: Optional[List[str]] = Field(default=None, description="Lista de tipos de carrocería recomendados por RAG (ej: ['SUV', 'COUPE'])")
    modo_adquisicion_recomendado: Optional[Literal['Contado', 'Financiado']] = Field(
        default=None,
        description="Modo de compra recomendado (Contado/Financiado) basado en análisis Modo 1."
    )
    precio_max_contado_recomendado: Optional[float] = Field(
        default=None,
        description="Precio máximo recomendado si se aconseja comprar al contado (Modo 1)."
    )
    cuota_max_calculada: Optional[float] = Field(
        default=None,
        description="Cuota mensual máxima calculada si se aconseja financiar (Modo 1)."
    )
    plazas_min: Optional[int] = Field(default=None, description="Número mínimo de plazas recomendadas (conductor + pasajeros).")
   
#cuanta gana y aplicamos un % 60 /por porcentaje MODO 1 o 2 iNGRESO 
class EconomiaUsuario(BaseModel):
    modo:         Optional[Literal[1, 2]] = Field(default=None) # Añadir Field(default=None) por si acaso
    submodo:      Optional[Literal[1, 2]] = Field(default=None)
    ingresos:     Optional[float] = Field(default=None)
    ahorro:       Optional[float] = Field(default=None)
    pago_contado: Optional[float] = Field(default=None)
    cuota_max:    Optional[float] = Field(default=None)
    entrada:      Optional[float] = Field(default=None)
    anos_posesion: Optional[int] = Field(default=None, description="Número estimado de años que el usuario planea conservar el vehículo." )


# 🧠 Modelos de Salida (ResultadoEconomia, ResultadoSoloPerfil, ResultadoSoloFiltros): Estos modelos definen la salida esperada del LLM.
class ResultadoEconomia(BaseModel):
    economia: EconomiaUsuario = Field(description="Objeto que contiene TODA la información económica recopilada o actualizada.") 
    mensaje_validacion: str

class ResultadoSoloPerfil(BaseModel):
    """Salida esperada del LLM enfocado solo en el perfil del usuario."""
    preferencias_usuario: PerfilUsuario = Field(
        description="Objeto con las preferencias del usuario actualizadas o inferidas."
        )
    tipo_mensaje: Literal["PREGUNTA", "CONFIRMACION", "ERROR"] = Field(
        description="Clasificación del mensaje: 'PREGUNTA' si se necesita más info de perfil, 'CONFIRMACION' si el perfil parece completo o se confirma un dato, 'ERROR' si hubo un problema irresoluble."
    )
    contenido_mensaje: str = Field(
        description="El texto real del mensaje: la pregunta específica, la confirmación, o el detalle del error."
    )

# --- NUEVO MODELO DE SALIDA PARA LLM DE PASAJEROS ---
class ResultadoPasajeros(BaseModel):
    """Salida esperada del LLM enfocado en recopilar info de pasajeros."""
    info_pasajeros: InfoPasajeros = Field(
        description="Objeto con la información de pasajeros actualizada o inferida."
    )
    tipo_mensaje: Literal["PREGUNTA", "CONFIRMACION", "ERROR"] = Field(...) # Hacer obligatorio
    contenido_mensaje: str = Field(...) # Hacer obligatorio

    
class ResultadoSoloFiltros(BaseModel):
    """Salida esperada del LLM enfocado solo en inferir filtros técnicos."""
    filtros_inferidos: FiltrosInferidos
    mensaje_validacion: str = Field(description="Pregunta de seguimiento CLARA y CORTA si falta información ESENCIAL para completar los FiltrosInferidos (ej: tipo_mecanica), o un mensaje de confirmación si los filtros están completos.")


# Modelo Pydantic para la salida del LLM que extrae el CP ---
class ResultadoCP(BaseModel):
    """Salida esperada del LLM enfocado en extraer el código postal."""
    codigo_postal_extraido: Optional[str] = Field(default=None, description="El código postal numérico de 5 dígitos extraído de la respuesta del usuario.")
    tipo_mensaje: Literal["PREGUNTA_ACLARACION", "CP_OBTENIDO", "ERROR"] = Field(description="Clasificación: 'PREGUNTA_ACLARACION' si el CP no es válido o falta, 'CP_OBTENIDO' si se extrajo un CP válido, 'ERROR'.")
    contenido_mensaje: str = Field(description="El texto real del mensaje: la pregunta de aclaración para el CP, una confirmación, o un detalle del error.")




#ES el contenedor general que acumula toda la información a lo largo de la ejecución del grafo.
class EstadoAnalisisPerfil(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  # 👈 sumo todos los mensajes sin perder contexto
    codigo_postal_usuario: Optional[str] # El CP validado
    info_clima_usuario: Optional[InfoClimaUsuario] # Los datos climáticos de BQ
    codigo_postal_extraido_temporal: Optional[str]
    tipo_mensaje_cp_llm: Optional[Literal["PREGUNTA_ACLARACION", "CP_OBTENIDO", "ERROR"]]
    _decision_cp_validation: Optional[Literal["buscar_clima", "repreguntar_cp"]] # Clave interna para routing
    preferencias_usuario: Optional[PerfilUsuario]
    filtros_inferidos: Optional[FiltrosInferidos]
    economia: Optional[EconomiaUsuario]          # ← nuevo canal para la rama económica
    mensaje_validacion: Optional[str]
    pesos:              Optional[dict]  # soft‑weights normalizados
    pregunta_pendiente: Optional[str] # Para guardar la pregunta entre nodos
    coches_recomendados: Optional[List[dict[str, any]]] # Lista de diccionarios de coches
    info_pasajeros: Optional[InfoPasajeros] # Añadimos el nuevo objeto al estado principal
    penalizar_puertas_bajas: Optional[bool] 
    #priorizar_ancho: Optional[bool]
    flag_penalizar_low_cost_comodidad: Optional[bool]
    flag_penalizar_deportividad_comodidad: Optional[bool]
    flag_penalizar_antiguo_por_tecnologia: Optional[bool]
    aplicar_logica_distintivo_ambiental: Optional[bool]
    es_municipio_zbe: Optional[bool]
    penalizar_bev_reev_aventura_ocasional: Optional[bool]
    penalizar_phev_aventura_ocasional: Optional[bool]
    penalizar_electrificados_aventura_extrema: Optional[bool] # Un solo flag para BEV, REEV, PHEV en aventura extrema
    # --- NUEVOS FLAGS PARA LÓGICA DE CARROCERÍA ---
    favorecer_carroceria_montana: Optional[bool]
    favorecer_carroceria_comercial: Optional[bool]
    favorecer_carroceria_pasajeros_pro: Optional[bool]
    desfavorecer_carroceria_no_aventura: Optional[bool]
    favorecer_suv_aventura_ocasional: Optional[bool]
    favorecer_pickup_todoterreno_aventura_extrema:Optional[bool]
    aplicar_logica_objetos_especiales: Optional[bool]
    favorecer_carroceria_confort: Optional[bool] 
    flag_logica_uso_ocasional: Optional[bool]
    flag_favorecer_bev_uso_definido: Optional[bool]
    flag_penalizar_phev_uso_intensivo: Optional[bool]
    flag_favorecer_electrificados_por_punto_carga: Optional[bool]
    flag_logica_diesel_ciudad: Optional[str]
    km_anuales_estimados: Optional[int]
    tabla_resumen_criterios: Optional[str] # Para la tabla MD de finalizar_y_presentar






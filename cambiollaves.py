{{
  "$defs": {{
    "FiltrosInferidos": {{
      "properties": {{
        "tipo_mecanica": {{
          "anyOf": [
            {{
              "items": {{
                "$ref": "#/$defs/TipoMecanica"
              }},
              "type": "array"
            }},
            {{
              "type": "null"
            }}
          ],
          "default": null,
          "description": "Lista de motorizaciones recomendadas",
          "title": "Tipo Mecanica"
        }},
        "tipo_carroceria": {{
          "anyOf": [
            {{
              "items": {{
                "type": "string"
              }},
              "type": "array"
            }},
            {{
              "type": "null"
            }}
          ],
          "default": null,
          "description": "Lista de tipos de carrocer\u00eda recomendados por RAG (ej: ['SUV', 'COUPE'])",
          "title": "Tipo Carroceria"
        }},
        "modo_adquisicion_recomendado": {{
          "anyOf": [
            {{
              "enum": [
                "Contado",
                "Financiado"
              ],
              "type": "string"
            }},
            {{
              "type": "null"
            }}
          ],
          "default": null,
          "description": "Modo de compra recomendado (Contado/Financiado) basado en an\u00e1lisis Modo 1.",
          "title": "Modo Adquisicion Recomendado"
        }},
        "precio_max_contado_recomendado": {{
          "anyOf": [
            {{
              "type": "number"
            }},
            {{
              "type": "null"
            }}
          ],
          "default": null,
          "description": "Precio m\u00e1ximo recomendado si se aconseja comprar al contado (Modo 1).",
          "title": "Precio Max Contado Recomendado"
        }},
        "cuota_max_calculada": {{
          "anyOf": [
            {{
              "type": "number"
            }},
            {{
              "type": "null"
            }}
          ],
          "default": null,
          "description": "Cuota mensual m\u00e1xima calculada si se aconseja financiar (Modo 1).",
          "title": "Cuota Max Calculada"
        }},
        "plazas_min": {{
          "anyOf": [
            {{
              "type": "integer"
            }},
            {{
              "type": "null"
            }}
          ],
          "default": null,
          "description": "N\u00famero m\u00ednimo de plazas recomendadas (conductor + pasajeros).",
          "title": "Plazas Min"
        }}
      }},
      "title": "FiltrosInferidos",
      "type": "object"
    }},
    "TipoMecanica": {{
      "enum": [
        "GASOLINA",
        "DIESEL",
        "BEV",
        "FCEV",
        "GLP",
        "GNV",
        "HEVD",
        "HEVG",
        "MHEVD",
        "MHEVG",
        "PHEVD",
        "PHEVG",
        "REEV"
      ],
      "title": "TipoMecanica",
      "type": "string"
    }}
  }},
  "description": "Salida esperada del LLM enfocado solo en inferir filtros t\u00e9cnicos.",
  "properties": {{
    "filtros_inferidos": {{
      "$ref": "#/$defs/FiltrosInferidos"
    }},
    "mensaje_validacion": {{
      "description": "Pregunta de seguimiento CLARA y CORTA si falta informaci\u00f3n ESENCIAL para completar los FiltrosInferidos (ej: tipo_mecanica), o un mensaje de confirmaci\u00f3n si los filtros est\u00e1n completos.",
      "title": "Mensaje Validacion",
      "type": "string"
    }}
  }},
  "required": [
    "filtros_inferidos",
    "mensaje_validacion"
  ],
  "title": "ResultadoSoloFiltros",
  "type": "object"
}}
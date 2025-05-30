# utils/enums.py
from enum import Enum

#✅ Si luego agrego otros Enums (por ejemplo, para UsoVehiculo o NivelEstetica), este es el lugar ideal para añadirlos.
# Enums para campos compatibles
class TipoCarroceria(str, Enum):
    COMERCIAL = "COMERCIAL"
    DESCAPOTABLE = "DESCAPOTABLE"
    TRES_VOL = "3VOL"
    DOS_VOL = "2VOL"
    SUV = "SUV"
    AUTOCARAVANA = "AUTOCARAVANA"
    COUPE = "COUPE"
    FURGONETA = "FURGONETA"
    MONOVOLUMEN = "MONOVOLUMEN"
    PICKUP = "PICKUP"
    TODOTERRENO = "TODOTERRENO"

class TipoMecanica(str, Enum):
    GASOLINA = "GASOLINA"
    DIESEL = "DIESEL"
    BEV = "BEV"
    FCEV = "FCEV"
    GLP = "GLP"
    GNV = "GNV"
    HEVD = "HEVD"  # Híbrido Eléctrico Diesel
    HEVG = "HEVG"  # Híbrido Eléctrico Gasolina
    MHEVD = "MHEVD" # Mild Hybrid Diesel
    MHEVG = "MHEVG" # Mild Hybrid Gasolina
    PHEVD = "PHEVD" # Híbrido Enchufable Diesel
    PHEVG = "PHEVG" # Híbrido Enchufable Gasolina
    REEV = "REEV"   # Eléctrico de Autonomía Extendida

class NivelAventura(str, Enum):
    ninguna   = "ninguna"
    ocasional = "ocasional"
    extrema   = "extrema"
    
class Transmision(str, Enum):
    AUTOMATICO = "automático"
    MANUAL      = "manual"
    AMBOS       = "ambos"

class TipoUsoProfesional(str, Enum):
    PASAJEROS = "pasajeros"
    CARGA     = "carga"
    MIXTO     = "mixto"
    
class DimensionProblematica(str, Enum):
    LARGO = "largo"
    ANCHO = "ancho"
    ALTO = "alto"
    
class EstiloConduccion(str, Enum):
    TRANQUILO = "tranquilo"
    DEPORTIVO = "deportivo"
    MIXTO     = "mixto"
    
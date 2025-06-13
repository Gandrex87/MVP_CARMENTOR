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
    

class FrecuenciaUso(str, Enum):
    DIARIO = "diario"
    FRECUENTEMENTE = "frecuentemente"
    OCASIONALMENTE = "ocasionalmente"

class DistanciaTrayecto(str, Enum):
    MENOS_10_KM = "no supera los 10 km"
    ENTRE_10_Y_50_KM = "está entre 10 y 50 km"
    ENTRE_51_Y_150_KM = "está entre 51 y 150 km"
    MAS_150_KM = "supera los 150 km"
    
  
class FrecuenciaViajesLargos(str, Enum):
    FRECUENTEMENTE = "frecuentemente"
    OCASIONALMENTE = "ocasionalmente"
    ESPORADICAMENTE = "esporádicamente"
    




# Sistema de Ponderación de Pesos para Recomendador de Vehículos

## 1. Introducción

Este documento describe la arquitectura y el funcionamiento del sistema de cálculo de pesos (`compute_raw_weights`), que constituye el núcleo del motor de entendimiento de las preferencias del usuario.

El objetivo de este sistema es traducir las necesidades, deseos y contexto de un usuario en un vector de pesos numéricos que represente su "coche ideal". Este vector se utiliza posteriormente para puntuar y clasificar los vehículos disponibles.

Esta arquitectura fue desarrollada para superar las limitaciones de un sistema anterior basado en pesos arbitrarios, buscando una mayor robustez, consistencia, mantenibilidad y coherencia metodológica.

## 2. Filosofía Central: Adaptación al Usuario

El principio que guía todo el sistema es: "El usuario no se adapta al sistema, el sistema se adapta al usuario".

Rechazamos la idea de encasillar a los usuarios en perfiles predefinidos ("familiar", "urbano", "deportivo"). La realidad de un usuario es multidimensional y a menudo contradictoria. Un usuario puede desear seguridad, deportividad y economía a la vez.

Nuestro modelo no busca resolver estas "contradicciones" imponiendo un perfil, sino que las acepta y genera un perfil de pesos único y personalizado que refleja fielmente la complejidad de los deseos de cada usuario.

## 3. Arquitectura: "Genoma del Automóvil + Multiplicadores"

Para lograr esta flexibilidad sin caer en la arbitrariedad, el sistema se basa en una arquitectura de dos capas:

### 3.1. Capa 1: El "Genoma del Automóvil" (`master_weights.yaml`)

Este fichero es el pilar de la objetividad y consistencia del sistema.

¿Qué es? Es un diccionario que contiene el peso base para cada una de las ~40 características técnicas que evaluamos. La suma de todos estos pesos es 1.0.

¿Qué representa? No representa a un usuario, sino nuestra visión experta y objetiva de un "coche idealmente equilibrado". Es el ADN de lo que consideramos un buen coche en términos generales.

¿Cómo se creó? Estos pesos no son arbitrarios. Se calcularon utilizando el Best-Worst Method (BWM), una metodología formal de toma de decisiones multi-criterio. El proceso se realizó en dos niveles:

Nivel Micro (Intra-Dimensión): Se determinó la importancia relativa de cada característica técnica dentro de su propia dimensión (ej: ¿Qué es más importante para las "Prestaciones", la aceleración o el par_motor?).

Nivel Macro (Inter-Dimensión): Se determinó la importancia relativa de cada una de las 7 dimensiones principales (Seguridad, Economía, Prestaciones, etc.) en el conjunto global.

¿Debe modificarse? No. Este fichero es la base estable del sistema y no debe ser alterado a menos que se realice un rediseño fundamental de la filosofía del recomendador.

### 3.2. Capa 2: Los Multiplicadores Dinámicos (en `compute_raw_weights`)

Esta es la capa de personalización donde la magia ocurre.

¿Qué es? Es un diccionario de multiplicadores que se crea en tiempo de ejecución. Por defecto, todas las características tienen un multiplicador de 1.0.

¿Cómo funciona? La función compute_raw_weights analiza las preferencias del usuario y, en lugar de asignar pesos, modifica estos multiplicadores.

if usuario valora la estética -> multiplicadores[`estetica`] *= 6.0

El Resultado: El peso crudo final de cada característica se calcula como: peso_base_del_genoma * multiplicador_del_usuario. Esto asegura que la personalización sea siempre proporcional a la importancia objetiva de la característica.

## 4. Flujo de Trabajo de compute_raw_weights

La función sigue un proceso claro y secuencial:

Cargar el Genoma: Lee el fichero master_weights.yaml.

Inicializar Multiplicadores: Crea un diccionario de multiplicadores, todos con valor 1.0.

Aplicar Reglas de Negocio: Itera sobre todas las preferencias del usuario y ajusta los multiplicadores correspondientes.

Calcular Pesos Proporcionales: Calcula un primer conjunto de pesos crudos multiplicando `master_weights[key]` * `multiplicadores[key]`.

Aplicar "Overrides" de Perfil: Para casos muy específicos como estilo_conduccion, se aplica una lógica de "override" que reemplaza los pesos recién calculados para un grupo de características con valores absolutos. Esto modela un cambio de "personalidad" completo.

Aplicar Clamping: Se realiza una validación final para asegurar que ningún peso sea menor que su valor base en master_weights ni mayor que un máximo global (ej. 10.0). Esto actúa como una válvula de seguridad para mantener el equilibrio.

Devolver Resultado: La función devuelve el diccionario de pesos crudos finales, listo para ser normalizado.

## 5. Tipos de Reglas de Negocio

Dentro de la función, hemos establecido dos patrones de diseño para las reglas:

Modificadores de Importancia (*= o += al multiplicador): Es el patrón por defecto. Se usa cuando una preferencia del usuario debe amplificar la importancia de una o dos características aisladas (ej: `nivel_aventura` -> `altura_libre_suelo`).

Perfiles de Comportamiento (`.update() al raw_weights`): Se usa con moderación. Es para preferencias que redefinen por completo la relación entre un grupo de características (ej: estilo_conduccion -> Prestaciones). Este patrón aplica un "override" después del cálculo proporcional.

## 6. Cómo Mantener y Evolucionar el Sistema

Para añadir una nueva regla de negocio:

Identifica qué característica(s) del master_weights se ven afectadas.

Dentro de compute_raw_weights, en la sección del Paso 3, añade tu lógica condicional (`if/else`).

Decide si la regla es un "Modificador" (la mayoría de los casos) o un "Perfil".

Ajusta el multiplicador correspondiente.

Para ajustar la "sensibilidad" del sistema:

Modifica el valor de los multiplicadores (ej. cambiar un * 6.0 por un * 4.0). Estos valores deberían estar definidos como constantes para facilitar su gestión.

Nunca modifiques directamente los valores en master_weights.yaml para reflejar una regla de negocio. La integridad de ese fichero es lo que garantiza la coherencia del sistema.
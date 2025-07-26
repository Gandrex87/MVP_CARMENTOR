from typing import List, Dict

# --- ✅ BANCO DE PREGUNTAS CENTRALIZADO ---
# Este archivo actúa como un almacén de datos para todas las posibles preguntas.
# Al externalizarlo, es muy fácil añadir o modificar variaciones sin tocar la lógica del agente.


# --- ✅ PASO 1: Creamos nuestro "Banco de Preguntas" ---
# Centralizamos todas las posibles preguntas aquí. Es fácil añadir nuevas variaciones.
QUESTION_BANK: Dict[str, List[str]] = {
    "apasionado_motor": [
        "Para empezar, ¿te consideras una persona entusiasta del mundo del motor?",
        "¿Te describirías como un/a 'car lover' o un apasionado/a de los automóviles?",
        "¿Te apasiona el mundo del motor?",
        "¿Te consideras un fan del automóvil?",
        "¿Te gustan mucho los coches y todo lo que los rodea?",
        "¿Sientes verdadera pasión por el mundo del automóvil?",
        "¿Los coches son una de tus grandes aficiones? ",
        "¿Eres de los que disfrutan hablando sobre coches?"

    ],
    "valora_estetica": [
        "¿La Estética es importante para ti o crees que hay factores más importantes?",
        "En cuanto al estilo, ¿buscas un coche que destaque visualmente o priorizas otros aspectos?",
        "¿Es la estética del coche un factor decisivo para ti, o prefieres priorizar otros aspectos?",
        "¿El aspecto del coche influye mucho en tu elección, o no tanto?",
        "¿La estética de un coche es un factor importante para ti al decidir?",
        "¿Para ti es importante que un coche sea bonito?",
        "¿Te influye el diseño exterior de un coche a la hora de elegirlo?",
        "¿Te importa el aspecto del coche al tomar una decisión de compra? ",
        "¿El estilo y la forma del coche son determinantes para ti? ",
        "¿Valoras más un coche si tiene un diseño atractivo? ",
        "¿Eres de los que en lo primero que se fijan es en el diseño?"

    ],
    "coche_principal_hogar": [
        "¿El coche que estamos buscando será el vehículo principal de tu hogar?",
        "¿Este coche será el vehículo principal de tu hogar?",
        "¿El coche que buscas será el que más uséis en casa?", 
	    "¿Estamos eligiendo el coche principal del hogar?",
	    "¿Este será el coche que más vas a utilizar en el día a día?",
	    "¿Va a ser el coche principal que tengáis en casa?"

    ],
    "frecuencia_uso": [
        ("¿Con qué frecuencia usarás el coche?\n"
         "* 💨 A diario (incluso varias veces al día)\n"
         "* 🔄 Frecuentemente (varias veces por semana)\n"
         "* 🕐 Ocasionalmente (pocas veces al mes)"),
        ("¿Con qué regularidad vas a conducir este vehículo?\n"
         "* 💨 A diario (incluso varias veces al día)\n"
         "* 🔄 Frecuentemente (varias veces por semana)\n"
         "* 🕐 Ocasionalmente (pocas veces al mes)"),
        ("¿Cada cuánto vas a utilizar el coche?\n" 
         "* 💨 A diario (incluso varias veces al día)\n"
         "* 🔄 Frecuentemente (varias veces por semana)\n"
         "* 🕐 Ocasionalmente (pocas veces al mes)")     
    ],
    "distancia_trayecto": [
        ("¿Cuál es la distancia aproximada de tu trayecto más habitual?\n"
        "* 🐌 Hasta 10 km\n"
        "* 🚴‍♂️ 10-50 km\n"
        "* 🚗  51-150 km\n"
        "* 🚀 Más de 150 km"),
        ("¿Qué distancia recorres normalmente en tus trayectos más frecuentes?\n"
         "* 🟣 Hasta 10 km\n"
         "* 🟡 10-50 km\n"
         "* 🟠 51-150 km\n"
         "* 🔵 Más de 150 km"),
        ("¿Cuántos kilómetros haces, por lo general, en un trayecto típico?\n"
         "* 🟣 Hasta 10 km\n"
         "* 🟡 10-50 km\n"
         "* 🟠 51-150 km\n"
         "* 🔵 Más de 150 km"),
        ("¿Cuál es la media de kilómetros que sueles hacer por desplazamiento habitual?\n"
        "* 🐌 Hasta 10 km\n"
        "* 🚴‍♂️ 10-50 km\n"
        "* 🚗  51-150 km\n"
        "* 🚀 Más de 150 km")
    ],    
    "realiza_viajes_largos": [
        "Además de tus trayectos habituales, ¿sueles hacer viajes largos de más de 150 km?\n* ✅ Sí\n* ❌ No",
        "Pensando en viajes más largos, ¿realizas recorridos de más de 150 km de vez en cuando?\n* ✅ Sí\n* ❌ No"
    ],
    "frecuencia_viajes_largos": [
        ("Entendido. ¿Y con qué frecuencia realizas estos viajes largos?\n"
         "* 💨 Frecuentemente (Varias veces al mes)\n"
         "* 🗓️ Ocasionalmente (Algunas veces al mes)\n"
         "* 🕐 Esporádicamente (Pocas veces al año)")
    ],
    "circula_principalmente_ciudad": [
        "¿Circulas principalmente por ciudad?\n* ✅ Sí\n* ❌ No",
        "¿Tu conducción habitual es en entorno urbano?\n* ✅ Sí\n* ❌ No",
        "¿Sueles moverte sobre todo por ciudad?\n* ✅ Sí\n* ❌ No",
        "¿La mayoría de tus trayectos son urbanos?\n* ✅ Sí\n* ❌ No",
        "¿Tu uso principal del coche es en ciudad?\n* ✅ Sí\n* ❌ No"
    ],
    "uso_profesional": [
        "¿El coche lo destinaras principalmente para uso personal o más para fines profesionales (trabajo)?",
        "¿El uso principal del coche será para tu vida personal o para el trabajo?",
        "¿El uso habitual será más personal o profesional?",
        "¿Lo emplearás principalmente como coche de uso particular o como herramienta de trabajo?"
    ],
    "tipo_uso_profesional": [
        "¿Y ese uso profesional será principalmente para llevar pasajeros, transportar carga o un uso mixto?",
       	"¿En tu trabajo usarás el coche sobre todo para transportar personas, mercancías o ambos?",
    	"¿El uso profesional será más bien como vehículo de pasajeros, de carga o un poco de todo?", 
	    "¿Tu actividad laboral requiere trasladar personas, cosas o ambas?",
	    "¿Será un coche orientado a trasladar clientes, transportar productos o los dos tipos de uso?",
	    "¿Lo necesitas como transporte para pasajeros, para carga, o para ambas funciones?"
    ],
    "prefiere_diseno_exclusivo":[
        "¿Prefieres conducir algo que marque la diferencia o que se integre sin llamar la atención?",
        "Al conducir, ¿te gusta diferenciarte del resto o prefieres la discreción y pasar más desapercibido?",
        "¿Te gusta que tu coche llame la atención o prefieres algo más discreto?",
    	"¿Eres de los que conducen para diferenciarse o prefieres no destacar demasiado?",
	    "¿Buscas un coche que refleje personalidad y estilo, o priorizas pasar desapercibido?",
	    "¿Tu estilo al volante es más rompedor o más discreto?"   
    ],
    "altura_mayor_190":[
        "¿Mides más de 1,90 m? Es importante para recomendarte un coche con buen espacio interior.", 
        "¿Tu estatura supera los 1,90 metros? Así evitamos recomendarte coches incómodos.",
        "¿Eres más alto de 1,90 m? Nos ayuda a elegir modelos con mejor espacio para ti.",
        "¿Tienes una estatura elevada (más de 1,90 m)? Lo tendremos en cuenta para el habitáculo.",
        "¿Mides más de 1,90 m? Queremos asegurarnos de que vayas cómodo al volante.",
        "¿Superas el 1,90 m de altura? Esto influye en el espacio del coche que elijamos."   
    ],
    "transporta_carga_voluminosa":[
        "¿Acostumbras a viajar con el maletero muy cargado?\n* ✅ Sí\n* ❌ No",
        "¿Sueles llevar el maletero muy lleno en tus viajes?\n* ✅ Sí\n* ❌ No",
        "¿Acostumbras a cargar el maletero al máximo con frecuencia?\n* ✅ Sí\n* ❌ No",
        "¿Viajas habitualmente con el maletero repleto de equipaje o cosas?\n* ✅ Sí\n* ❌ No",
        "¿Tu maletero va casi siempre hasta arriba?\n* ✅ Sí\n* ❌ No",
        "¿Eres de los que llena el maletero cada vez que sale?\n* ✅ Sí\n* ❌ No",
        "¿El espacio del maletero es clave para ti porque lo usas mucho?\n* ✅ Sí\n* ❌ No"     
    ],
    "necesita_espacio_objetos_especiales":[
        "¿Vas a transportar objetos voluminosos como bicicletas, tablas de surf, cochecitos, instrumentos musicales o similares?",
        "¿Necesitas espacio para cargar cosas grandes como bicis, tablas, sillas infantiles o instrumentos?",
        "¿Sueles llevar en el coche objetos de tamaño especial (bicicletas, cochecitos, equipamiento deportivo…)?",
        "¿Cuentas con equipamiento grande que necesites llevar contigo (como una silla de ruedas, una tabla de surf o una bici)?"   
    ],
     "arrastra_remolque":[
        "¿Tienes previsto usar el coche para arrastrar una caravana o remolque grande? \n* ✅ Sí\n* ❌ No",
        "¿Necesitas que el vehículo tenga buena capacidad de remolque?\n* ✅ Sí\n* ❌ No" ,
        "¿El coche que buscas debería poder tirar de una caravana o remolque sin problemas?\n* ✅ Sí\n* ❌ No",
        "¿Vas a enganchar un remolque o similar de forma habitual?\n* ✅ Sí\n* ❌ No"        
    ],
      "aventura":[
          (
            "¿Con qué tipo de terreno se enfrentará tu coche? :\n"
            "* 🛣️ Solo asfalto\n"
            "* 🌲 También por pistas sin asfaltar, de forma ocasional\n"
            "* 🏔️ Frecuentemente por terrenos complicados o en condiciones extremas"
        ) 
    ],
     "estilo_conduccion":[
            (
            "¿Conduces de forma relajada o prefieres sensaciones más deportivas?\n" 
            "* 🚗 Relajada\n"  
            "* 🏁 Deportiva\n"  
            "* ⚖️ Depende del día, mixto" 
        ),
            (
            "¿Qué estilo te define más al volante? \n" 
            "* 🚗 Tranquilo\n"  
            "* 🏁 Deportiva\n"  
            "* ⚖️ Depende del día, mixto" 
        ),
            (
    "¿Qué tipo de conducción te resulta más natural?\n"  # Doble salto de línea aquí
    "* 🚗 Tranquilo\n"  # Asterisco y espacio al principio
    "* 🏁 Deportiva\n"  # Asterisco y espacio al principio
    "* ⚖️ Depende del día, mixto"  # Asterisco y espacio al principio
    ),      
    ],
     "tiene_garage":[
         "Hablemos un poco de dónde aparcarás. ¿Tienes garaje o plaza de aparcamiento propia?\n* ✅ Sí\n* ❌ No",
         "Hablemos un poco de dónde aparcarás. ¿Dispones de un garaje o sitio fijo para aparcar?\n* ✅ Sí\n* ❌ No",
         "Hablemos un poco de dónde aparcarás. ¿Tu vivienda dispone de garaje o aparcamiento reservado?\n* ✅ Sí\n* ❌ No",
         "Hablemos un poco de dónde aparcarás. ¿Cuentas con una plaza de parking particular?\n* ✅ Sí\n* ❌ No"
          
    ],
     "espacio_sobra_garage":[
        "¡Genial lo del garaje/plaza! Y dime, ¿el espacio que tienes es amplio y te permite aparcar un coche de cualquier tamaño con comodidad?\n* ✅ Sí\n* ❌ No",
        "¡Genial lo de la plaza! ¿El espacio que tienes es amplio y te permite aparcar un coche de cualquier tamaño con comodidad?\n* ✅ Sí\n* ❌ No",
        "¡Genial! ¿Tienes sitio suficiente para aparcar coches grandes sin problema?\n* ✅ Sí\n* ❌ No",
        "¿El espacio donde aparcas permite maniobrar fácilmente con cualquier coche?\n* ✅ Sí\n* ❌ No"
    ],
     "problema_dimension_garage":[
         "Comprendo que el espacio es ajustado. ¿Cuál es la principal limitación de dimensión?\n ↔️ Ancho\n ↕️ Alto\n ⬅️➡️ Largo",
         "¿Qué es lo que más limita el tipo de coche que puedes aparcar ahí?\n ↔️ Ancho\n ↕️ Alto\n ⬅️➡️ Largo"  
    ],
     "problemas_aparcar_calle":[
         "Entendido. En ese caso, al aparcar en la calle, ¿sueles encontrar dificultades por el tamaño del coche o la disponibilidad de sitios?\n* ✅ Sí\n* ❌ No",
         "¿Dirías que aparcar en la calle es una dificultad en tu día a día?\n* ✅ Sí\n* ❌ No"  
    ],
     "tiene_punto_carga_propio":[
        "¿cuentas con un punto de carga para vehículo eléctrico en tu domicilio o lugar de trabajo habitual?\n* ✅ Sí\n* ❌ No",
        "¿Tienes acceso habitual a un punto de carga para coche eléctrico en casa o en el trabajo?\n* ✅ Sí\n* ❌ No",
        "¿Dispones de algún enchufe o cargador para coches eléctricos en tu vivienda o trabajo?\n* ✅ Sí\n* ❌ No",
        "¿Puedes cargar un coche eléctrico fácilmente desde casa o tu oficina?\n* ✅ Sí\n* ❌ No",
        "¿Tienes instalada una toma de carga para vehículos eléctricos en alguno de tus espacios habituales?\n* ✅ Sí\n* ❌ No"       
    ],
     "solo_electricos":[
        "¿Estás interesado exclusivamente en vehículos con motorización eléctrica?\n* ✅ Sí\n* ❌ No",
        "¿Buscas únicamente un coche 100% eléctrico?\n* ✅ Sí\n* ❌ No",
        "¿Te interesa solo un coche con motor eléctrico, sin combustión?\n* ✅ Sí\n* ❌ No",
        "¿Quieres que tu próximo coche sea exclusivamente eléctrico?\n* ✅ Sí\n* ❌ No",
        "¿Tu elección se centra solo en coches eléctricos?\n* ✅ Sí\n* ❌ No"      
    ],
     
     "transmision_preferida":[
         ("En cuanto a la transmisión, ¿qué opción se ajusta mejor a tus preferencias?\n"
            "* Automático\n"
            "* Manual\n"
            "* Ambos, puedo considerar ambas opciones"
        ),
         (
        "En cuanto a la transmisión, ¿qué prefieres? \n"
        "* ⚙️ **Automático**\n"
        "* 🕹️ **Manual**\n"
        "* 🤔 **Ambos** (estoy abierto/a a ambas)"
        )
    ],
     
     "prioriza_baja_depreciacion":[
        "¿Es importante para ti que la depreciación del coche sea lo más baja posible?\n* ✅ Sí\n* ❌ No",
        "¿Te importa que el coche mantenga bien su valor con el tiempo?\n* ✅ Sí\n* ❌ No",
        "¿Valoras que el coche no pierda demasiado valor al cabo de los años?\n* ✅ Sí\n* ❌ No",
        "¿Te preocupa cuánto se deprecia el coche después de comprarlo?\n* ✅ Sí\n* ❌ No",
        "¿Prefieres un coche que conserve un buen precio de reventa?\n* ✅ Sí\n* ❌ No",
        "¿Es relevante para ti que el coche pierda poco valor con el uso?\n* ✅ Sí\n* ❌ No"    
    ],
     "rating_fiabilidad_durabilidad":[
         ( 
        "¿Cómo de importante es para ti la Fiabilidad y Durabilidad del coche?\n" 
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        ),
         (
        "¿Cuánto valoras que el coche sea fiable y dure muchos años sin dar problemas?\n" 
        "📊 0 (nada importante) ———— 10 (extremadamente importante)" 
         ),
         (
        "¿Qué importancia le das a que el coche tenga buena reputación de fiabilidad y larga vida útil?\n" 
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"    
         )    
    ],
     "rating_seguridad":[
        ( 
        "¿Pensando en la Seguridad, ¿qué puntuación le darías en importancia?\n" 
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        ),
        ( 
        "¿Cuánto valoras que el coche ofrezca altos niveles de seguridad en carretera?\n" 
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        ),
        ( 
        "¿Qué nivel de prioridad le das a la seguridad frente a otros aspectos del coche?\n" 
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        )
    ],
     "rating_comodidad":[
         (
        "Y en cuanto a la comodidad y confort del vehiculo como de importante es que sea elevado?\n"
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        ),
         (
        "¿Qué prioridad le das al confort frente a otros factores?\n"
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        )
    ],
     "rating_impacto_ambiental":[
         (
        "¿Cómo de importante es para ti que tu movilidad tenga un bajo impacto medioambiental?\n"
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        ),
         (
        "¿Qué importancia le das a reducir las emisiones y cuidar el medio ambiente con tu coche?\n"
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        ),
         (
        "¿Qué importancia tiene la sostenibilidad en tu decisión a la hora de elegir coche?\n"
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        )        
    ],
     "rating_costes_uso":[
         (
        "Cómo de importante es para ti que el vehículo sea económico en su uso diario y mantenimiento?\n"
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        ),
         (
        "¿Valoras que el coche tenga un consumo y mantenimiento bajos?\n"
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        ),
         (
        "¿Cuánto te importa que el coche sea barato de mantener y eficiente en consumo?\n"
        "📊 0 (nada importante) ———— 10 (extremadamente importante)"
        )        
    ],
    "rating_tecnologia_conectividad": [
        ("Finalmente, en cuanto a la Tecnología y Conectividad, ¿qué nota de importancia le asignarías? \n"
         "📊 0 (nada importante) ———— 10 (extremadamente importante)"),
        ("Y para terminar con las valoraciones, ¿Qué importancia le das a la tecnología de a bordo y sistemas multimedia del vehículo??\n"
         "📊 0 (nada importante) ———— 10 (extremadamente importante)")
    ],
    "fallback": [
        "¿Podrías darme algún detalle más sobre tus preferencias?",
        "Cuéntame un poco más sobre lo que buscas para poder ayudarte mejor.",
        "¿Hay algo más que consideres importante para tu próximo coche?"
    ]
}


PREGUNTAS_CP_INICIAL = [
    "¿Podrías indicarme tu código postal para personalizar tu recomendación?",
    "Para empezar, ¿me podrías facilitar tu código postal? Así podré ajustar mejor las sugerencias.",
    "¿Cuál es tu código postal? Lo usaré para tener en cuenta factores locales en la recomendación."
]

PREGUNTAS_CP_REINTENTO = [
    "El código postal no parece correcto. Por favor, asegúrate de que son 5 dígitos. ¿Podrías intentarlo de nuevo? Si prefieres no darlo, no hay problema, podemos continuar.",
    "Hmm, ese código postal no es válido. ¿Podrías introducir los 5 dígitos de nuevo, por favor? Si no quieres, dímelo y seguimos adelante.",
    "Necesito un código postal de 5 dígitos para continuar. ¿Podrías verificarlo? Si prefieres no compartirlo, podemos saltar este paso."
]

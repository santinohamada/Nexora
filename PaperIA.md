# Sistema de Comunicación y Reconocimiento de Lengua de Señas Argentina (LSA) basado en Arquitectura Multipantalla e Inteligencia Artificial Local

**Universidad Tecnológica Nacional, Facultad Regional Tucumán**

---

## Abstract

La comunicación efectiva en atención médica es un desafío para pacientes usuarios de Lengua de Señas Argentina (LSA) debido a la escasez de intérpretes. Aunque la legislación argentina garantiza la accesibilidad, su implementación es deficiente y afecta a más de 900.000 personas con dificultad auditiva. Este trabajo presenta un prototipo de arquitectura multipantalla para comunicación bidireccional paciente-profesional. El sistema interpreta LSA en tiempo real extrayendo puntos clave con MediaPipe Holistic y clasificando secuencias con una red LSTM (PyTorch). Un Modelo de Lenguaje Grande (LLM) de ejecución local reconstruye gramaticalmente las oraciones al español, verbalizadas mediante Piper TTS. El flujo inverso emplea reconocimiento de voz (Web Speech API) y sincronización P2P vía BroadcastChannel. Incluye además un módulo de captura para ampliar el vocabulario incrementalmente. Se describe la arquitectura, su relevancia social y la factibilidad de la integración local, identificando la evaluación cuantitativa como trabajo futuro.

**Palabras Clave:** Lengua de Señas Argentina (LSA), Informática Médica, Inteligencia Artificial, Reconocimiento de Gestos, Procesamiento de Lenguaje Natural, Arquitectura Local, Inclusión Social, Accesibilidad en Salud.

---

## Introducción

La atención médica exige comunicación precisa. Sin embargo, los pacientes sordos usuarios de LSA enfrentan sistemáticas barreras en centros de salud. La falta de intérpretes presenciales y la ineficacia de métodos alternativos (lectura labial o escritura) retrasan la atención y generan malentendidos críticos, reflejando inequidades estructurales en el acceso a la salud.

La OMS estima que 430 millones de personas padecen pérdida auditiva discapacitante globalmente [8], mientras que en Argentina más de 900.000 personas presentan alguna dificultad auditiva [9]. Pese a que el marco normativo nacional reconoce el derecho a la accesibilidad comunicacional, la presencia de intérpretes en hospitales públicos es excepcional.

Este trabajo plantea cómo orquestar visión computacional y procesamiento de lenguaje natural en una arquitectura estrictamente local (sin depender de la nube) para entornos médicos, donde la privacidad es prioritaria. El objetivo es presentar un prototipo multipantalla para la traducción e interacción bidireccional LSA-español que empodere al paciente sordo y asista al profesional, acoplando extracción de características corporales con un LLM in situ y aprendizaje incremental para expandir el vocabulario ante la escasez de corpus públicos de LSA. 

---

## Contexto Socio-Sanitario y Marco Normativo

Bajo el modelo social de la discapacidad (Naciones Unidas) [10], la discapacidad surge de la interacción entre las características funcionales de la persona y las barreras del entorno. Un paciente sordo es discapacitado por un sistema de salud exclusivamente oralista. Estudios internacionales demuestran que estas barreras aumentan los errores de medicación y los diagnósticos demorados [11], imposibilitando un verdadero consentimiento informado.

En Argentina, la LSA es una lengua natural con sintaxis propia (predominantemente sujeto-objeto-verbo) e independiencia del español oral [12]. Por ello, su traducción requiere una reconstrucción gramatical profunda y no un simple mapeo de palabras. A nivel normativo, leyes como la 26.378 y 27.044 (Convención de los Derechos de las Personas con Discapacidad con jerarquía constitucional) [13] exigen al Estado garantizar la accesibilidad sanitaria. No obstante, la implementación real es marginal.

El sistema propuesto no reemplaza al intérprete humano, cuyas competencias pragmáticas y culturales son irreemplazables. En cambio, actúa como un "ajuste razonable" complementario para brindar un canal de comunicación básico en situaciones de guardia donde la alternativa es la ausencia total de comunicación o el uso de métodos precarios que vulneran la privacidad del paciente.

---

## Arquitectura del Sistema

El prototipo utiliza una arquitectura web asíncrona, dividiendo el procesamiento entre un backend de IA (FastAPI/Uvicorn) y un frontend interactivo de doble vista (Next.js/React). 

> *Figura 1: Arquitectura del sistema. Flujos de comunicación: (a) paciente a profesional (captura, LSTM, LLM, TTS); (b) profesional a paciente (reconocimiento de voz y sincronización).*

El diseño emplea dos interfaces en el navegador: la "Estación del Paciente" y la "Estación de Recepción". La sincronización se realiza vía BroadcastChannel (P2P), evitando los retardos y riesgos de privacidad de servidores intermediarios (ej. WebSockets), al no almacenar datos sensibles. Un video demostrativo del funcionamiento del prototipo en tiempo real se encuentra disponible como material suplementario [17].

Para el flujo paciente-profesional, la Estación del Paciente usa MediaPipe Holistic localmente para extraer 33 puntos corporales y 21 por mano, normalizándolos en secuencias de 45 frames. Una red LSTM entrenada en PyTorch procesa la dinámica espacial. Si la confianza supera el 70%, clasifica la seña. El uso de MediaPipe evita hardware especializado (guantes o sensores), facilitando su adopción pública.

Al detectarse un reposo de dos segundos, el búfer de señas se envía a un LLM Qwen2 1.5b (vía Ollama). Este modelo reconstruye semánticamente el mensaje agramatical al español fluido ("yo dolor cabeza" -> "Tengo mucho dolor de cabeza"). Finalmente, Piper TTS verbaliza el texto.

En el flujo inverso, el profesional usa reconocimiento de voz (Web Speech API) para dictar mensajes que se transcriben y envían al monitor del paciente instantáneamente, agilizando la atención. 

Además, se incluyó un módulo de captura asistida para registrar nuevas señas localmente. Esto es vital para la LSA por la falta de corpus masivos y por sus variantes dialectales regionales, permitiendo a cada hospital adaptar el vocabulario a su comunidad.

---

## Trabajos Relacionados

Sistemas previos de reconocimiento de lengua de señas han empleado brazaletes IMU/EMG y guantes, logrando alta exactitud pero introduciendo fricción y costos inviables en entornos clínicos [1]. Otros enfoques modernos usan anillos inteligentes con una precisión del 88% en vocabularios acotados [2].

En visión por computadora sin instrumentación, antecedentes en LSA incluyen intérpretes web usando MediaPipe y redes LSTM/GRU [3]. También se han propuesto sistemas en Lengua de Señas Mexicana para consultas médicas [4] y diccionarios cotidianos con más del 90% de exactitud [5]. Para la Lengua de Signos Española, el proyecto Sign4all interpreta dactilología y frases en tiempo real (80% de precisión) [6, 7].

Desde lo social, investigaciones destacan las barreras comunicacionales sanitarias [14] y la necesidad de diseño participativo con la comunidad sorda para garantizar que las soluciones respondan a demandas reales [15]. A diferencia de estos antecedentes, nuestro sistema combina: (a) reconstrucción gramatical vía LLM local, (b) captura incremental de vocabulario para dialectos regionales y (c) una arquitectura P2P que garantiza privacidad clínica.

---

## Conclusión y Trabajos Futuros

Este trabajo demostró la viabilidad técnica de una arquitectura de hardware de consumo para mitigar barreras comunicacionales en salud para usuarios de LSA. Mediante LSTM, un LLM local, TTS y sincronización P2P, se logró una traducción multimodal asíncrona sin dependencia de la nube, resguardando datos clínicos sensibles regidos por la Ley 25.326 de Protección de Datos Personales [16].

El sistema aborda un problema de exclusión social y derechos humanos, devolviendo agencia al paciente sordo en su atención médica [11]. Su diseño modular permite extenderlo a otras áreas de atención pública. No obstante, la tecnología no soluciona el déficit estructural de intérpretes, debiendo integrarse en estrategias institucionales más amplias.

Entre las limitaciones éticas, los modelos locales son más propensos a errores semánticos que aquellos en la nube. Un error de traducción clínica puede ser grave, por lo que es prioritario implementar un mecanismo de confirmación visual para el paciente antes de verbalizar. 

Las futuras líneas de trabajo incluyen:
1. **Evaluación técnica**: Validar cuantitativamente el modelo LSTM, la calidad del LLM y la latencia del sistema, incorporando además rasgos no manuales de la LSA.
2. **Evaluación con usuarios**: Realizar estudios de usabilidad y aceptabilidad con personas sordas y médicos bajo estrictos protocolos éticos.
3. **Optimización y despliegue**: Cuantizar el LLM para reducir demanda de hardware, agregar confirmaciones visuales de seguridad y ejecutar un despliegue piloto en una guardia real.

---

## Agradecimientos

[Nota: Versión para evaluación ciega — sección en blanco. Para la versión Camera Ready, se incluirá el texto de agradecimientos correspondiente.]

---

## Referencias

[1] Sistemas basados en sensores IMU/EMG y guantes para lengua de señas mexicana. Disponible: researchgate.net/publication/387094402
[2] Sistema WRSLT de anillos inteligentes, Science Advances (2026). Disponible: infobae.com
[3] Intérprete Web de LSA, UNSJ. Disponible: huru.unsj.edu.ar/handle/123456789/321
[4] Reconocimiento de LSA en consultas médicas, Univ. Veracruzana. Disponible: cdigital.uv.mx/items/f5e74f40-239b-499f-bd80-47595977c4a3
[5] E. Sánchez Vázquez, "IA para traducción de lengua de señas", RIMI, 2023. Disponible: researchgate.net/publication/387094402
[6] E. Martínez y F. Morillas, Sign4all (LSE), Grupo RoViT, Univ. de Alicante, 2023. Disponible: web.ua.es
[7] Grupo RoViT, "Sign4all Dataset", Univ. de Alicante, 2024. Disponible: observatorio-cientifico.ua.es
[8] OMS, "World Report on Hearing", 2021. Disponible: who.int
[9] INDEC, Encuesta Nacional de Personas con Discapacidad (ENDI), 2005. Disponible: indec.gob.ar
[10] ONU, "Convención sobre los Derechos de las Personas con Discapacidad", 2008. Disponible: un.org
[11] T. Barnett, "Impact of communication on healthcare for deaf patients", Patient Ed. and Counseling, 2021.
[12] M. I. Massone et al., "La comunidad sorda argentina y su LSA", Edicial, 2000.
[13] Rep. Argentina, Leyes 26.378 y 27.044.
[14] P. Kushalnagar et al., "Infants and children with hearing loss need early language access", JCE, 2010.
[15] J. C. Guzmán et al., "Diseño participativo de tecnologías de asistencia en Latinoamérica", RITEET, 2022.
[16] Rep. Argentina, Ley 25.326 de Protección de los Datos Personales.
[17] NEXORA. (s. f.). Prototipo Señalud. Disponible en: https://drive.google.com/file/d/1lVs-bJ-JAgv_IeN5blAoF4qm87E45JJE

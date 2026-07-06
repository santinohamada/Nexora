import wave
import os
from piper.voice import PiperVoice

# 1. Cargamos el modelo de voz que acabás de descargar
modelo = "voices/es_AR-daniela-high.onnx"
voice = PiperVoice.load(modelo)

# 2. El texto que sacamos de Ollama
texto = "Tengo dolor en mi hombro. Necesito ver a un médico."

# 3. Generamos el audio y lo guardamos en un .wav
archivo_salida = "prueba_voz.wav"
with wave.open(archivo_salida, "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(voice.config.sample_rate)
    voice.synthesize_wav(texto, wav_file)

print("¡Audio generado! Escuchando...")
# Esto abre el reproductor de Windows automáticamente para escucharlo
os.system(f"start {archivo_salida}")

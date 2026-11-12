"""Texto legible para los valores de las respuestas (la base de conocimiento guarda códigos)."""
_E = {
    "verdadero": "Sí", "falso": "No",
    "apagado_reinicio": "Se apaga o reinicia solo", "errores_extranos": "Errores o comportamiento extraño",
    "imagen_video": "Problemas de imagen o video", "lentitud": "Lentitud, bloqueos o bajo rendimiento",
    "red_audio_perifericos": "Falla de Internet, audio o periféricos",
    "audio": "Audio", "internet": "Internet", "mouse_usb": "Mouse USB", "teclado": "Teclado",
    "alguno": "Alguno", "ninguno": "Ninguno", "maxima": "Al máximo", "deficiente": "Deficiente", "anormal": "Anormal",
    "distorsion": "La imagen se ve distorsionada", "sin_senal": "No hay señal en la pantalla",
}


def etiqueta(valor: str) -> str:
    return _E.get(valor, valor.replace("_", " "))

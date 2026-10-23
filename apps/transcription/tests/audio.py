from io import BytesIO

import av
import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile

SAMPLE_RATE = 16000


def audio_bytes(seconds: float = 1, container_format: str = "ipod", codec: str = "aac") -> bytes:
    buffer = BytesIO()
    samples = np.zeros((1, int(seconds * SAMPLE_RATE)), dtype=np.float32)

    with av.open(buffer, mode="w", format=container_format) as container:
        stream = container.add_stream(codec, rate=SAMPLE_RATE, layout="mono")
        frame = av.AudioFrame.from_ndarray(samples, format="fltp", layout="mono")
        frame.rate = SAMPLE_RATE

        for packet in [*stream.encode(frame), *stream.encode(None)]:
            container.mux(packet)

    return buffer.getvalue()


def uploaded_audio(
    seconds: float = 1,
    container_format: str = "ipod",
    codec: str = "aac",
    content_type: str = "audio/mp4",
    name: str = "audio.m4a",
) -> SimpleUploadedFile:
    content = audio_bytes(seconds, container_format, codec)

    return SimpleUploadedFile(name, content, content_type=content_type)

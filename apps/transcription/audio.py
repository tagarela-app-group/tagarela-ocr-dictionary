from dataclasses import dataclass

import av


class InvalidAudioError(Exception):
    pass


@dataclass(frozen=True)
class AudioInfo:
    formats: tuple[str, ...]
    codecs: tuple[str, ...]
    seconds: float | None


def read_audio_info(source) -> AudioInfo:
    try:
        with av.open(source) as container:
            duration = container.duration

            return AudioInfo(
                formats=tuple(container.format.name.split(",")),
                codecs=tuple(stream.codec_context.name for stream in container.streams),
                seconds=None if duration is None else duration / av.time_base,
            )
    except av.FFmpegError as exc:
        raise InvalidAudioError(str(exc)) from exc

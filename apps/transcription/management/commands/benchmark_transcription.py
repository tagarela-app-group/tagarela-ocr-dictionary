import resource
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.transcription.audio import read_audio_info
from apps.transcription.providers.whisper import WhisperProvider


class Command(BaseCommand):
    help = "Mede tempo e CPU da transcrição de áudios com um modelo do Whisper."

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="+", type=Path)
        parser.add_argument("--model")
        parser.add_argument("--compute-type")
        parser.add_argument("--threads", type=int)
        parser.add_argument("--beam-size", type=int)

    def handle(self, *args, **options):
        missing = [str(path) for path in options["paths"] if not path.is_file()]
        if missing:
            raise CommandError(f"Arquivo não encontrado: {', '.join(missing)}")

        provider = WhisperProvider(
            model_name=options["model"],
            compute_type=options["compute_type"],
            cpu_threads=options["threads"],
            beam_size=options["beam_size"],
        )
        self.stdout.write(
            f"modelo {provider.model_name} | {provider.compute_type} | "
            f"beam {provider.beam_size} | threads {provider.cpu_threads or 'auto'}"
        )

        wall, cpu, _ = self.measure(provider.load)
        self.stdout.write(f"carga: {wall:.1f} s (CPU {cpu:.1f} s)")

        for path in options["paths"]:
            seconds = read_audio_info(str(path)).seconds
            wall, cpu, text = self.measure(provider.transcribe_path, path)
            self.stdout.write(
                f"{path.name}: áudio {seconds:.1f} s | tempo {wall:.1f} s | "
                f"CPU {cpu:.1f} s | {wall / seconds:.2f}x o áudio | {cpu / wall:.1f} núcleos"
            )
            self.stdout.write(f"  {text}")

        peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
        self.stdout.write(f"memória pico: {peak_mb} MB")

    def measure(self, function, *args):
        wall_started, cpu_started = time.perf_counter(), time.process_time()
        result = function(*args)
        wall, cpu = time.perf_counter() - wall_started, time.process_time() - cpu_started

        return wall, cpu, result

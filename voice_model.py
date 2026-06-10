from __future__ import annotations

import asyncio
import io
import logging
import subprocess
import tempfile
import wave
from pathlib import Path

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def _pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 24000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buffer.getvalue()


def _wav_to_ogg_bytes(wav_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        wav_path = tmpdir_path / "input.wav"
        ogg_path = tmpdir_path / "output.ogg"
        wav_path.write_bytes(wav_bytes)

        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-c:a",
            "libopus",
            "-b:a",
            "32k",
            str(ogg_path),
        ]
        subprocess.run(command, check=True, capture_output=True)
        return ogg_path.read_bytes()


async def generate_voice_ogg_bytes(
    *,
    prompt: str,
    api_key: str,
    model: str,
    voice_name: str,
    api_version: str | None = None,
) -> bytes:
    def _run() -> bytes:
        client_kwargs = {"api_key": api_key}
        if api_version:
            client_kwargs["http_options"] = {"api_version": api_version}
        client = genai.Client(**client_kwargs)

        is_tts_model = "tts" in model.lower()
        speech_config = {
            "voice_config": {"prebuilt_voice_config": {"voice_name": voice_name}}
        }
        thinking_config = types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.HIGH
        )

        async def _collect_live_audio() -> bytes:
            audio_chunks: list[bytes] = []
            config = {
                "response_modalities": ["AUDIO"],
                "speech_config": speech_config,
                "thinking_config": thinking_config,
            }
            async with client.aio.live.connect(model=model, config=config) as session:
                await session.send_realtime_input(text=prompt)
                async for response in session.receive():
                    server_content = getattr(response, "server_content", None)
                    if not server_content:
                        continue
                    model_turn = getattr(server_content, "model_turn", None)
                    if model_turn and getattr(model_turn, "parts", None):
                        for part in model_turn.parts:
                            inline_data = getattr(part, "inline_data", None)
                            if inline_data and getattr(inline_data, "data", None):
                                audio_chunks.append(inline_data.data)
                    if getattr(server_content, "turn_complete", False):
                        break
            return b"".join(audio_chunks)

        def _generate_tts_audio() -> bytes:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_modalities": ["AUDIO"],
                    "speech_config": speech_config,
                    "thinking_config": thinking_config,
                },
            )
            candidate = response.candidates[0] if response.candidates else None
            if not candidate or not candidate.content or not candidate.content.parts:
                return b""
            inline_data = candidate.content.parts[0].inline_data
            return inline_data.data if inline_data and inline_data.data else b""

        if is_tts_model:
            return _generate_tts_audio()
        return asyncio.run(_collect_live_audio())

    pcm_bytes = await asyncio.to_thread(_run)
    if not pcm_bytes:
        raise RuntimeError("Gemini returned no audio data")
    wav_bytes = _pcm_to_wav_bytes(pcm_bytes)
    return await asyncio.to_thread(_wav_to_ogg_bytes, wav_bytes)

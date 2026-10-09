#!/usr/bin/env python3
"""Stage 2: transcribe 01-source/audio.wav with Whisper.

Usage:
    transcribe.py <workfolder> [--model large-v3] [--language auto|en|ru|...] [--backend auto|faster|mlx|openai]
    transcribe.py <workfolder> --detect-only      # print the detected language and exit

Backends, tried in this order with --backend auto:
    faster  — faster-whisper (CTranslate2), fastest on CPU/CUDA
    mlx     — mlx-whisper, fastest on Apple Silicon
    openai  — the reference openai-whisper package
Decoding is deterministic (temperature 0, no conditioning on previous text) to limit hallucinations.

Writes 02-transcript/: transcript.json (segments with start/end/text and words), transcript.txt, transcript.srt.
"""
import argparse
import json
import sys
from pathlib import Path

MLX_MODELS = {"large-v3": "mlx-community/whisper-large-v3-mlx", "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
              "medium": "mlx-community/whisper-medium-mlx", "small": "mlx-community/whisper-small-mlx"}


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def run_faster(wav, model, language, detect_only):
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="auto", compute_type="auto")
    segs, info = m.transcribe(str(wav), language=None if language == "auto" else language, temperature=0,
                              condition_on_previous_text=False, word_timestamps=not detect_only, vad_filter=True,
                              beam_size=5)
    if detect_only:
        return info.language, []
    out = [{"start": s.start, "end": s.end, "text": s.text.strip(),
            "words": [{"start": float(w.start), "end": float(w.end), "word": w.word} for w in (s.words or [])]} for s in segs]
    return info.language, out


def run_mlx(wav, model, language, detect_only):
    import mlx_whisper
    if model not in MLX_MODELS and "/" not in model:
        sys.exit(f"mlx backend: unknown model '{model}'; use one of {', '.join(MLX_MODELS)} or a Hugging Face repo id")
    res = mlx_whisper.transcribe(str(wav), path_or_hf_repo=MLX_MODELS.get(model, model),
                                 language=None if language == "auto" else language, temperature=0.0,
                                 condition_on_previous_text=False, word_timestamps=not detect_only,
                                 clip_timestamps="0,30" if detect_only else "0")
    out = [{"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip(),
            "words": [{"start": float(w["start"]), "end": float(w["end"]), "word": w["word"]} for w in s.get("words", [])]}
           for s in res["segments"]]
    return res.get("language"), ([] if detect_only else out)


def run_openai(wav, model, language, detect_only):
    import whisper
    m = whisper.load_model(model)
    if detect_only:
        audio = whisper.pad_or_trim(whisper.load_audio(str(wav)))
        mel = whisper.log_mel_spectrogram(audio, n_mels=m.dims.n_mels).to(m.device)
        _, probs = m.detect_language(mel)
        return max(probs, key=probs.get), []
    res = m.transcribe(str(wav), language=None if language == "auto" else language, temperature=0,
                       condition_on_previous_text=False, word_timestamps=True)
    out = [{"start": s["start"], "end": s["end"], "text": s["text"].strip(), "words": s.get("words", [])}
           for s in res["segments"]]
    return res.get("language"), out


BACKENDS = {"faster": ("faster_whisper", run_faster), "mlx": ("mlx_whisper", run_mlx), "openai": ("whisper", run_openai)}


def pick_backend(name):
    import importlib.util
    order = [name] if name != "auto" else ["mlx", "faster", "openai"] if sys.platform == "darwin" else ["faster", "openai", "mlx"]
    for b in order:
        mod, fn = BACKENDS[b]
        if importlib.util.find_spec(mod):
            return b, fn
    sys.exit("no Whisper backend installed: pip install faster-whisper  (or mlx-whisper on Apple Silicon, or openai-whisper)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workfolder")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--language", default="auto")
    ap.add_argument("--backend", default="auto", choices=["auto", *BACKENDS])
    ap.add_argument("--detect-only", action="store_true")
    a = ap.parse_args()
    root = Path(a.workfolder)
    wav = root / "01-source" / "audio.wav"
    if not wav.exists():
        sys.exit(f"{wav} not found: run fetch.py first")
    name, fn = pick_backend(a.backend)
    lang, segs = fn(wav, a.model, a.language, a.detect_only)
    if a.detect_only:
        print(f"language: {lang}")
        return
    out = root / "02-transcript"
    out.mkdir(exist_ok=True)
    (out / "transcript.json").write_text(json.dumps({"language": lang, "backend": name, "model": a.model, "segments": segs},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "transcript.txt").write_text("\n".join(s["text"] for s in segs) + "\n", encoding="utf-8")
    with open(out / "transcript.srt", "w", encoding="utf-8") as fh:
        for i, s in enumerate(segs, 1):
            fh.write(f"{i}\n{srt_time(s['start'])} --> {srt_time(s['end'])}\n{s['text']}\n\n")
    words = sum(len(s["text"].split()) for s in segs)
    print(f"backend: {name}, model: {a.model}, language: {lang}, segments: {len(segs)}, words: {words}")


if __name__ == "__main__":
    main()

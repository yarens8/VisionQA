# Vision Providers

VisionQA uses visual model providers only at runtime. Importing backend modules
or running CI unit tests must not download SAM3 or Grounding DINO weights.

## Provider Order

Default environment:

```env
VISION_MODEL_PROVIDER=sam3
VISION_MODEL_FALLBACK=dinox
SAM3_MODEL_ID=facebook/sam3
DINO_MODEL_ID=IDEA-Research/grounding-dino-base
```

Runtime behavior:

1. Try SAM3 first.
2. If SAM3 cannot load, raises an access/dependency error, or returns no visual
   elements when results are required, try Grounding DINO.
3. If both providers are unavailable, return an empty visual result and continue
   with DOM, metadata, pixel, or URL-based fallback logic.

Set `VISION_MODEL_PROVIDER=none` and `VISION_MODEL_FALLBACK=none` to disable
model-based visual detection.

## Docker Cache Warmer

Run the SAM3 smoke test and populate the Hugging Face cache volume:

```bash
docker compose run --rm sam3-cache
```

The first run downloads the model into `visionqa_huggingface_cache`. Later runs
reuse that volume unless it is removed with commands such as
`docker compose down -v` or Docker Desktop volume cleanup.

## CI Policy

CI should test:

- provider modules can be imported;
- fallback behavior works with fake provider objects;
- disabling providers returns an empty visual result.

CI should not run `sam3-cache` or instantiate real model clients during normal
unit tests.

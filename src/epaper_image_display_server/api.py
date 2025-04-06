import os
import random
from contextlib import asynccontextmanager
from fractions import Fraction
from functools import lru_cache
from importlib.metadata import version
from itertools import batched
from pathlib import Path

from fastapi import FastAPI, Response
from loguru import logger
from PIL import Image, UnidentifiedImageError

from epaper_image_display_server.request_payload import ImageRequest

name = "epaper_image_display_server"
images: set[Path] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    image_dir = Path(os.environ.get("IMAGE_LOCATION", "images"))
    global images
    for f in image_dir.iterdir():
        try:
            Image.open(f)
            images.add(f)
        except UnidentifiedImageError as e:
            print(f"Unable to open {f}: {e}")
    if not images:
        raise RuntimeError(f"{image_dir=} contained no images")
    yield


app = FastAPI(title=name, version=version(name), lifespan=lifespan)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@lru_cache
def _memoized_image(image_path: str, image_request: ImageRequest) -> bytes:
    """
    If we've computed a similar-enough image request for this image, then we
    should be ok to just return the previously computed bytes.
    """
    with Image.open(image_path) as loaded_image:
        # handle resizing (which may affect colors?) before palette ops
        if image_request.dimensions:

            # crop to correct aspect ratio
            aspect_ratio = Fraction(
                image_request.dimensions[0], image_request.dimensions[1]
            )
            if loaded_image.height < loaded_image.width * 1 / aspect_ratio:
                # chop width
                loaded_image = loaded_image.crop(
                    (
                        0,
                        0,
                        float(loaded_image.width * aspect_ratio),
                        loaded_image.height,
                    )
                )
            elif loaded_image.height > loaded_image.width * 1 / aspect_ratio:
                loaded_image = loaded_image.crop(
                    (
                        0,
                        0,
                        loaded_image.width,
                        float(loaded_image.width * 1 / aspect_ratio),
                    )
                )

            logger.info(f"Resizing to {image_request.dimensions}")
            loaded_image.thumbnail(size=image_request.dimensions)

        # quantize/dither to requested palette
        if image_request.palette:
            logger.info(f"Dithering to palette {image_request.palette}")
            palette_stub = Image.new("P", (1, 1))

            # alpha=False guarantees list[int]
            palette: list[int] = [
                item
                for color in image_request.palette
                for item in color.as_rgb_tuple(alpha=False)
            ]  # type: ignore
            palette_stub.putpalette(palette)

            # must convert to RGB or L before quantization
            loaded_image = loaded_image.convert("RGB")

            # the actual dithering/quantization
            loaded_image = loaded_image.quantize(
                colors=len(image_request.palette),
                palette=palette_stub,
            )

        loaded_bytes = loaded_image.tobytes()

        # now re-pack accordingly
        if image_request.pixels_per_byte > 1:
            squished_bytes = bytearray()
            for i_tup in batched(loaded_bytes, image_request.pixels_per_byte):
                i_x = 0
                for idx, i in enumerate(i_tup, start=1):
                    i_x += i << (
                        (image_request.pixels_per_byte - idx)
                        * (8 // image_request.pixels_per_byte)
                    )
                    # TODO: right pad with zeroes
                squished_bytes.append(i_x)

            loaded_bytes = bytes(squished_bytes)

        return loaded_bytes


@app.post(
    "/art",
    responses={200: {"content": {"application/octet-stream": {}}}},
    response_class=Response,
)
def query_art(image_request: ImageRequest) -> Response:
    """
    POSTing to this endpoint returns bytes that you should (probably) feed
    directly to the display.
    """

    if image_request.image_name and image_request.image_name in images:
        loaded_image = image_request.image_name
    else:
        loaded_image = random.choice(list(images))  # TODO: this is O(N)

    logger.info(f"Selected {loaded_image}")

    # this _is_ hashable, as long as frozen=True
    loaded_bytes = _memoized_image(loaded_image, image_request)  # type: ignore
    logger.success(f"Returning {len(loaded_bytes)} bytes")

    return Response(
        content=loaded_bytes,
        media_type="application/octet-stream",
    )

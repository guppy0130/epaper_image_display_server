from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_extra_types.color import Color


class ImageRequest(BaseModel):
    """
    Options in the request for an image
    """

    model_config = ConfigDict(frozen=True)

    #: specify an image by name
    image_name: str | None = None

    #: colors you can display
    palette: tuple[Color, ...] | None = None

    #: resize to this (width, height)
    dimensions: tuple[int, int] | None = None

    # TODO: is this something that should be left to client devices?
    #: bit packing
    pixels_per_byte: int = 1

    @field_validator("pixels_per_byte", mode="after")
    @classmethod
    def image_bits_per_byte_valid(cls, pixels_per_byte: int) -> int:
        """
        Must be 1, 2, 4, or 8 because bytes are 8 bits.
        """

        # TODO: handle when image_bits_per_byte isn't 1, 2, 4, 8
        if pixels_per_byte in {1, 2, 4, 8}:
            return pixels_per_byte
        raise ValueError(
            f"Unable to handle {pixels_per_byte=} (not 1, 2, 4, or 8)"
        )

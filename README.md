# epaper-image-display-server

send dithered image data to epaper displays

## usage

```bash
pip install -e '.[dev]'
hypercorn epaper_image_display_server.api:app --bind 0.0.0.0:8000 --reload --debug
```

## notes

### `/art` endpoint

Refer to `request_payload.py`.

```jsonc
// all fields are optional.
{
  "image_name": "IMG_3116.jpeg",  // request specific image
  "palette": [
    "#fff", "#000", "#882b2b", "b5af30", "#235c47", "#2456b2"
  ],
  "dimensions": [1200, 1600],  // width, height
  "pixels_per_byte": 2
}
```

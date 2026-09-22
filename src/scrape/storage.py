"""Raw PDF storage with provenance sidecar. Separate from extracted text
so re-chunking never requires re-scraping."""
import datetime
import json
import pathlib
import urllib.parse

RAW_DIR = pathlib.Path("data/raw")


def dest_path(url: str, subdir: str) -> pathlib.Path:
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    return RAW_DIR / subdir / name


def save(client, url: str, subdir: str, **metadata) -> pathlib.Path:
    """Fetch url and write PDF + a .json provenance sidecar next to it.
    Skips the network call if the PDF is already on disk."""
    path = dest_path(url, subdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = path.with_suffix(path.suffix + ".json")
    if path.exists() and sidecar.exists():
        return path
    resp = client.get(url)
    path.write_bytes(resp.content)
    sidecar.write_text(
        json.dumps(
            {
                "source_url": url,
                "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                **metadata,
            },
            indent=2,
        )
    )
    return path

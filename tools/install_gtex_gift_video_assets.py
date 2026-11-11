#!/usr/bin/env python3
"""Install and verify the owner-supplied GTEX cinematic gift video pack."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED = {
  "gtex-gift-atmosphere.mp4": {
    "size_bytes": 1882885,
    "sha256": "8716425b17ebd38f6562bfc7a4332560fad149828cbcc163f69ff4537f8eb9eb"
  },
  "gtex-gift-bicycle.mp4": {
    "size_bytes": 2141805,
    "sha256": "6533094e886a3ac246e9d1542e91610323aba91403d3be78c8ee5905f84e8f0e"
  },
  "gtex-gift-boot.mp4": {
    "size_bytes": 1969300,
    "sha256": "204ad6fd9eff5ed2c8dd84d456114fd551009ab1a4b5d9d1cef31937c2dcaf51"
  },
  "gtex-gift-campus.mp4": {
    "size_bytes": 1730573,
    "sha256": "412af3e5305bf814f5ad760709bf497b6ec73db5070722a5828c29fb7a7bc572"
  },
  "gtex-gift-card.mp4": {
    "size_bytes": 2164028,
    "sha256": "72c0944aeccbfd53e93b2247978f10c272e58aadc1429fb855d0fda58af4231c"
  },
  "gtex-gift-city.mp4": {
    "size_bytes": 2769819,
    "sha256": "2b4f8de0b1676b3bf08b196e126dee4ca3b23c3afc9eb8e8e65fa4f088a0eb59"
  },
  "gtex-gift-coach.mp4": {
    "size_bytes": 883638,
    "sha256": "10af5902a641cc412265379150a825efe0dfd67836fa8f9974ba7f85735fbde8"
  },
  "gtex-gift-crown.mp4": {
    "size_bytes": 1621574,
    "sha256": "7ab9f2821827b8580ebfc66408e40d34ecef9492275852620f3024c9a6c3166c"
  },
  "gtex-gift-glove.mp4": {
    "size_bytes": 2048104,
    "sha256": "79a9ba682b8166cbf70bbfa2d5ba2fba100987d450a6bb630d635daee4d11d97"
  },
  "gtex-gift-goal.mp4": {
    "size_bytes": 1598470,
    "sha256": "52ae1cefaf3a31706c2c5e1c76119ca1494fa62aa3b1d4c613b5f5eb94240929"
  },
  "gtex-gift-golden-goal.mp4": {
    "size_bytes": 2035201,
    "sha256": "80a1893489323d9851432b36e507b3f7b0c2a9a2fc7104504955ae06ac7b6323"
  },
  "gtex-gift-hat-trick.mp4": {
    "size_bytes": 1548129,
    "sha256": "5ce364a41c04d91b6890fb132fc7c4859bf24b1899d2604524855a09a3eb5ea9"
  },
  "gtex-gift-hypercar.mp4": {
    "size_bytes": 1114862,
    "sha256": "156a777af89667300316739d38a92d371c68359dc9f78654fe17ee4e3c1580c4"
  },
  "gtex-gift-jet.mp4": {
    "size_bytes": 718680,
    "sha256": "deb27c551cb4f45b1a714dcd212e652466bdf3aa05992dd2de26ad580a6cffb1"
  },
  "gtex-gift-last-minute.mp4": {
    "size_bytes": 1254885,
    "sha256": "31d71bb69e28a3d3754bc713a2d78d140e52841a0d275d9c710eb9b62bd73bf4"
  },
  "gtex-gift-save.mp4": {
    "size_bytes": 1612728,
    "sha256": "57c5fdba5bd97683429ef9be9db87417b87a16f79a97d9c429e8e4730e1ddbdb"
  },
  "gtex-gift-tactics.mp4": {
    "size_bytes": 1139038,
    "sha256": "6103088c814b2b79282d90b0b3946f38b0bdaecb608a1c9ac0e9f55144294199"
  },
  "gtex-gift-trophy.mp4": {
    "size_bytes": 2443032,
    "sha256": "6db00dd41a8a5e50271dbf5f82d0f0aafbc355ffa74d38c6962274738a8f6e53"
  },
  "gtex-gift-yacht.mp4": {
    "size_bytes": 1654519,
    "sha256": "9f2b92666bcb91b65044611dc2741de4479bc153fc1b82845a325e80197adbbc"
  },
  "gtex-maracana-gift.mp4": {
    "size_bytes": 3015966,
    "sha256": "55266380e294790ba3aca96e38de7a65b4f0ec09b4cde10f3e2d7c7fb88cdbad"
  }
}

ARCHIVE_PREFIX = "frontend/react-shell/public/assets/gifting/"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_verified_pack(archive: Path) -> dict[str, bytes]:
    if not archive.is_file():
        raise FileNotFoundError(f"Asset archive not found: {archive}")

    payloads: dict[str, bytes] = {}
    with zipfile.ZipFile(archive) as bundle:
        for filename, metadata in EXPECTED.items():
            suffix = ARCHIVE_PREFIX + filename
            candidates = [
                info for info in bundle.infolist()
                if not info.is_dir() and info.filename.endswith(suffix)
            ]
            if len(candidates) != 1:
                raise ValueError(
                    f"Expected exactly one archive entry ending in {suffix!r}; "
                    f"found {len(candidates)}"
                )

            info = candidates[0]
            normalized = PurePosixPath(info.filename)
            if normalized.is_absolute() or ".." in normalized.parts:
                raise ValueError(f"Unsafe archive path: {info.filename}")

            data = bundle.read(info)
            if len(data) != metadata["size_bytes"]:
                raise ValueError(
                    f"{filename}: size mismatch; expected {metadata['size_bytes']}, "
                    f"got {len(data)}"
                )
            actual_hash = sha256(data)
            if actual_hash != metadata["sha256"]:
                raise ValueError(
                    f"{filename}: SHA-256 mismatch; expected {metadata['sha256']}, "
                    f"got {actual_hash}"
                )
            payloads[filename] = data

    return payloads


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install the verified GTEX cinematic gift MP4 files."
    )
    parser.add_argument("archive", type=Path, help="Path to gtex-gift-video-assets.zip")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="GTEX repository root (defaults to the parent of tools/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing MP4 whose bytes do not match the verified pack",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify the archive and report actions without writing files",
    )
    args = parser.parse_args()

    try:
        payloads = read_verified_pack(args.archive.resolve())
        destination = args.repo_root.resolve() / "frontend/react-shell/public/assets/gifting"

        actions: list[tuple[str, bytes]] = []
        for filename, data in payloads.items():
            target = destination / filename
            if target.is_file():
                existing_hash = sha256(target.read_bytes())
                if existing_hash == EXPECTED[filename]["sha256"]:
                    print(f"verified existing  {filename}")
                    continue
                if not args.force:
                    raise FileExistsError(
                        f"{target} already exists with different content. "
                        "Re-run with --force to replace it."
                    )
            actions.append((filename, data))

        if args.dry_run:
            print(f"Verified {len(payloads)} MP4 files; {len(actions)} would be installed.")
            return 0

        destination.mkdir(parents=True, exist_ok=True)
        for filename, data in actions:
            target = destination / filename
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination, prefix=f".{filename}.", delete=False
            ) as temp:
                temp.write(data)
                temp_path = Path(temp.name)
            temp_path.replace(target)
            print(f"installed           {filename}")

        print(
            f"Success: {len(payloads)} verified gift clips are available at "
            f"{destination.relative_to(args.repo_root.resolve())}"
        )
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"gift video install failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

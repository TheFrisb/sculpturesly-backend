import concurrent.futures
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from PIL import Image


class Command(BaseCommand):
    help = (
        "Optimizes images (PNG, JPG, WEBP). "
        "Options for WebP conversion or lossy PNG quantization."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Absolute path to the directory")
        parser.add_argument("--workers", type=int, default=4, help="Number of threads")
        parser.add_argument(
            "--lossy",
            action="store_true",
            help="Reduce PNG colors to 256 (PNG only)",
        )
        parser.add_argument(
            "--webp",
            action="store_true",
            help="Convert all images to WebP format",
        )

    def process_image(self, file_path, output_dir, options):
        try:
            path_obj = Path(file_path)
            ext = path_obj.suffix.lower()

            # Determine Output Format and Filename
            if options["webp"]:
                new_filename = path_obj.stem + ".webp"
                save_format = "WEBP"
            else:
                new_filename = path_obj.name
                # Map extension to PIL format
                if ext in [".jpg", ".jpeg"]:
                    save_format = "JPEG"
                elif ext == ".png":
                    save_format = "PNG"
                elif ext == ".webp":
                    save_format = "WEBP"
                else:
                    # Fallback for unforeseen types supported by PIL
                    save_format = None

            output_path = output_dir / new_filename

            with Image.open(path_obj) as img:
                original_size = path_obj.stat().st_size

                # --- SAVING LOGIC ---

                # 1. WebP Conversion (or optimization if already WebP)
                if save_format == "WEBP":
                    # method=6 is slowest compression but best size
                    img.save(output_path, "WEBP", quality=85, method=6)

                # 2. PNG Optimization
                elif save_format == "PNG":
                    if options["lossy"]:
                        # Quantize to 256 colors (TinyPNG style)
                        img = img.convert("P", palette=Image.ADAPTIVE, colors=256)
                        img.save(output_path, "PNG", optimize=True)
                    else:
                        # Lossless optimization
                        img.save(output_path, "PNG", optimize=True, compress_level=9)

                # 3. JPEG Optimization
                elif save_format == "JPEG":
                    # Convert RGBA to RGB if necessary (JPEGs don't support alpha)
                    if img.mode in ("RGBA", "LA"):
                        img = img.convert("RGB")

                    img.save(output_path, "JPEG", optimize=True, quality=85)

                # 4. Fallback
                else:
                    img.save(output_path, optimize=True)

                new_size = output_path.stat().st_size

                return {
                    "success": True,
                    "filename": new_filename,
                    "original_size": original_size,
                    "new_size": new_size,
                }

        except Exception as e:
            return {
                "success": False,
                "filename": Path(file_path).name,
                "error": str(e),
            }

    def handle(self, *args, **options):
        directory = Path(options["path"])
        workers = options["workers"]

        if not directory.is_dir():
            raise CommandError(f'Directory "{directory}" does not exist.')

        output_dir = directory / "optimized"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Updated filter for multiple extensions
        valid_extensions = {".png", ".jpg", ".jpeg", ".webp"}
        tasks = [
            f
            for f in directory.iterdir()
            if f.is_file() and f.suffix.lower() in valid_extensions
        ]

        self.stdout.write(f"Processing {len(tasks)} images with {workers} workers...")

        total_orig = 0
        total_new = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {
                executor.submit(self.process_image, f, output_dir, options): f
                for f in tasks
            }

            for future in concurrent.futures.as_completed(future_to_file):
                res = future.result()

                if res["success"]:
                    total_orig += res["original_size"]
                    total_new += res["new_size"]

                    saved = res["original_size"] - res["new_size"]
                    if res["original_size"] > 0:
                        percent = (saved / res["original_size"]) * 100
                    else:
                        percent = 0

                    # Green if > 20% savings, otherwise yellow/white
                    color = self.style.SUCCESS if percent > 20 else self.style.WARNING

                    self.stdout.write(
                        f"{res['filename']}: {res['original_size']/1024:.0f}KB -> "
                        f"{res['new_size']/1024:.0f}KB "
                        f"({color(f'-{percent:.1f}%')})"
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Error {res['filename']}: {res['error']}")
                    )

        if total_orig > 0:
            saved_mb = (total_orig - total_new) / (1024 * 1024)
            self.stdout.write("-" * 30)
            self.stdout.write(
                self.style.SUCCESS(f"Total Space Saved: {saved_mb:.2f} MB")
            )

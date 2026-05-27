import sys
import argparse
from pathlib import Path
import logging

try:
    import cv2
except ImportError:
    print("Ошибка: не найдена библиотека opencv-python")
    print("Установите: pip install opencv-python")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Ошибка: не найдена библиотека Pillow")
    print("Установите: pip install Pillow")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mov', '.mkv', '.wmv',
    '.flv', '.webm', '.m4v', '.mpg', '.mpeg'
}

def is_video_file(file_path: Path) -> bool:
    return file_path.suffix.lower() in VIDEO_EXTENSIONS

def collect_videos(input_dir: Path, recursive: bool) -> list:
    if recursive:
        return [p for p in input_dir.rglob('*') if p.is_file() and is_video_file(p)]
    else:
        return [p for p in input_dir.iterdir() if p.is_file() and is_video_file(p)]

def convert_to_gif(input_path: Path, output_path: Path,
                   target_fps: int, target_width: int,
                   preserve_speed: bool, optimize: bool) -> bool:
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        logger.error(f"Не удалось открыть видео: {input_path.name}")
        return False

    try:
        orig_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if orig_fps <= 0:
            orig_fps = 25
            logger.warning(f"Не удалось определить FPS для {input_path.name}, использую 25")

        if preserve_speed:
            if orig_fps <= target_fps:
                frame_step = 1
                duration_ms = 1000 / orig_fps
            else:
                frame_step = round(orig_fps / target_fps)
                duration_ms = (frame_step / orig_fps) * 1000
        else:
            if orig_fps <= target_fps:
                frame_step = 1
            else:
                frame_step = round(orig_fps / target_fps)
            duration_ms = 1000 / target_fps

        frames = []
        frame_idx = 0
        captured = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_step == 0:
                h, w = frame.shape[:2]
                scale = target_width / w
                new_h = int(h * scale)
                resized = cv2.resize(frame, (target_width, new_h),
                                     interpolation=cv2.INTER_LANCZOS4)
                rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                frames.append(pil_img)
                captured += 1

                if captured == 2000:
                    logger.warning(
                        f"Видео {input_path.name} даёт много кадров (>2000). "
                        "Это может привести к нехватке памяти. Рекомендуется уменьшить FPS или ширину."
                    )

            frame_idx += 1

        if not frames:
            logger.error(f"Не удалось извлечь ни одного кадра из {input_path.name}")
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(
            str(output_path),
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=optimize
        )
        logger.info(f"Создан {output_path.name} ({captured} кадров, длительность кадра = {duration_ms:.1f} мс)")
        return True

    except Exception as e:
        logger.error(f"Ошибка при обработке {input_path.name}: {e}")
        return False
    finally:
        cap.release()

def interactive_mode():
    print("\n   .oooooo.      .oooooo.")
    print("  d8P'  `Y8b    d8P'  `Y8b")
    print(" 888           888              oo.ooooo.  oooo    ooo")
    print(" 888           888               888' `88b  `88.  .8'")
    print(" 888     ooooo 888               888   888   `88..8'")
    print(" `88.    .88'  `88b    ooo  .o.  888   888    `888'")
    print("  `Y8bood8P'    `Y8bood8P'  Y8P  888bod8P'     .8'")
    print("                                 888       .o..P'")
    print("gif converter by l0wgenn        o888o      `Y8P'\n")
    
    input_dir = input("Введите путь к папке с видео: ").strip().strip('"')
    if not input_dir:
        print("Ошибка: путь не может быть пустым.")
        sys.exit(1)
    
    output_dir = input("Введите путь к папке для сохранения GIF: ").strip().strip('"')
    if not output_dir:
        print("Ошибка: путь не может быть пустым.")
        sys.exit(1)
    
    print("\nНастройки по умолчанию: FPS=10, ширина=320, без сохранения скорости, без оптимизации")
    use_defaults = input("Использовать настройки по умолчанию? (y/n): ").strip().lower()
    
    if use_defaults == 'y':
        fps = 10
        width = 320
        preserve_speed = False
        optimize = False
    else:
        try:
            fps = int(input("Введите FPS (целое число, по умолчанию 10): ") or 10)
        except ValueError:
            fps = 10
            print("Неверное значение, установлен FPS=10")
        
        try:
            width = int(input("Введите ширину в пикселях (по умолчанию 320): ") or 320)
        except ValueError:
            width = 320
            print("Неверное значение, установлена ширина=320")
        
        preserve_speed = input("Сохранять оригинальную скорость видео? (y/n): ").strip().lower() == 'y'
        optimize = input("Оптимизировать GIF (меньше размер, дольше обработка)? (y/n): ").strip().lower() == 'y'
    
    recursive = input("Рекурсивно обрабатывать подпапки? (y/n): ").strip().lower() == 'y'
    quiet = input("Показывать только ошибки? (y/n): ").strip().lower() == 'y'
    
    return (Path(input_dir), Path(output_dir), fps, width, preserve_speed, optimize, recursive, quiet)

def main():
    if len(sys.argv) == 1:
        input_dir, output_dir, fps, width, preserve_speed, optimize, recursive, quiet = interactive_mode()
        if quiet:
            logger.setLevel(logging.ERROR)
    else:
        parser = argparse.ArgumentParser(
            description="Конвертация видеофайлов в анимированные GIF."
        )
        parser.add_argument("input_dir", help="Папка с исходными видео")
        parser.add_argument("output_dir", help="Папка для сохранения GIF")
        parser.add_argument("--fps", type=int, default=10,
                            help="Целевой FPS для GIF (по умолчанию 10)")
        parser.add_argument("--width", type=int, default=320,
                            help="Ширина GIF в пикселях (высота пропорциональна, по умолчанию 320)")
        parser.add_argument("--preserve-speed", action="store_true",
                            help="Сохранять оригинальную скорость воспроизведения")
        parser.add_argument("--optimize", action="store_true",
                            help="Оптимизировать GIF (меньше размер, дольше генерация)")
        parser.add_argument("--recursive", action="store_true",
                            help="Рекурсивно обрабатывать подпапки")
        parser.add_argument("--quiet", action="store_true",
                            help="Показывать только ошибки")
        
        args = parser.parse_args()
        input_dir = Path(args.input_dir)
        output_dir = Path(args.output_dir)
        fps = args.fps
        width = args.width
        preserve_speed = args.preserve_speed
        optimize = args.optimize
        recursive = args.recursive
        if args.quiet:
            logger.setLevel(logging.ERROR)

    if not input_dir.exists() or not input_dir.is_dir():
        logger.error(f"Папка источника не существует: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    video_files = collect_videos(input_dir, recursive)
    if not video_files:
        logger.warning(f"Не найдено видеофайлов в {input_dir}")
        sys.exit(0)

    logger.info(f"Найдено видео: {len(video_files)}")
    logger.info(f"Выходная папка: {output_dir}")
    logger.info("Начинаю конвертацию...")

    success = 0
    for video in video_files:
        rel_path = video.relative_to(input_dir) if recursive else video.name
        gif_name = video.stem + '.gif'
        if recursive:
            out_subdir = output_dir / video.parent.relative_to(input_dir)
            out_path = out_subdir / gif_name
        else:
            out_path = output_dir / gif_name

        logger.info(f"Обработка: {rel_path} -> {gif_name}")
        if convert_to_gif(
            video, out_path,
            target_fps=fps,
            target_width=width,
            preserve_speed=preserve_speed,
            optimize=optimize
        ):
            success += 1

    logger.info(f"Готово. Успешно: {success} из {len(video_files)}")

if __name__ == "__main__":
    main()
import os
import cv2
import json
import pygame
import asyncio
from collections import deque
from PIL import Image
from pillow_heif import register_heif_opener, register_avif_opener

# Register HEIF and AVIF format support
register_heif_opener()
register_avif_opener()

# Orientation tag for EXIF data
ORIENTATION_TAG = 274

with open("config.json") as file:
    data = json.load(file)

local_media_directory = data["local_media_directory"]
announcement_directory = data["announcement_directory"]
slide_duration = data["slide_duration"]
announcement_duration = data["announcement_duration"]
supported_image_formats = ('.ras', '.im', '.grib', '.qoi', '.jfif', '.pxr', '.pbm', '.rgb', '.pnm', '.hdf', '.sgi', '.jpf', '.icns', '.blp', '.jpeg', '.bw', '.rgba', '.ppm', '.tiff', '.pgm', '.xpm', '.mpeg', '.ftu', '.bufr', '.gif', '.ftc', '.pcx', '.jpg', '.fits', '.pcd', '.ps', '.apng', '.pfm', '.emf', '.jpe', '.tif', '.vst', '.fli', '.cur', '.dib', '.jp2', '.gbr', '.tga', '.icb', '.j2c', '.webp', '.ico', '.png', '.jpc', '.vda', '.h5', '.flc', '.msp', '.eps', '.j2k', '.iim', '.wmf', '.bmp', '.dcx', '.jpx', '.psd', '.fit', '.xbm', '.mpg', '.dds', '.heic', '.avif', '.exif', '.xmp', '.iptc', '.svg', '.lbm')
supported_video_formats = ('.avi', '.mp4', '.mov', '.mkv') # Probably more, but no official opencv list due to differences in codecs per install?

# Set up the display
pygame.init()
pygame.display.set_caption("LCS Slideshow")
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN) 
screen_size = screen.get_size()
clock = pygame.time.Clock()

media_queue = deque(maxlen=5)

class event_handler:
    def handle_event(event):
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        if event.type == pygame.KEYDOWN:
            # Ctrl+C to exit
            if event.key == pygame.K_c and pygame.key.get_mods() & pygame.KMOD_CTRL:
                pygame.quit()
                exit()
            # Escape key to exit
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                exit()   
            # q key to exit
            elif event.key == pygame.K_q:
                pygame.quit()
                exit()  

async def handle_events(events_to_handle):
    for event in events_to_handle:
        event_handler.handle_event(event)

async def load_image(image_path, screen_size):
    try:
        img = Image.open(image_path)
        img_width, img_height = img.size
        if (img_width < 1280) or (img_height < 720):
            print(f"Omitting image, too small...")
            return None

        # Utilize EXIF data to properly orient image
        try:
            exif = img._getexif()
            if exif is not None:
                orientation_value = exif.get(ORIENTATION_TAG, None)
                if orientation_value == 3:
                    img = img.rotate(180, expand=True)
                elif orientation_value == 6:
                    img = img.rotate(270, expand=True)
                elif orientation_value == 8:
                    img = img.rotate(90, expand=True)
        except Exception as e:
            print(f"Error obtaining EXIF information for {image_path}: {e}\nUsing default orientation...")
            pass

        # This nifty function handles the scaling for us!
        img.thumbnail(screen_size, Image.LANCZOS)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Convert Pillow image to pygame surface
        img_surface = pygame.image.fromstring(img.tobytes(), img.size, 'RGB').convert()
    except Exception as e:
        print(f"Error loading image with PIL {image_path}: {e}")
        try:
            img = pygame.image.load(image_path)
            img_width, img_height = img.get_size()
            screen_width, screen_height = screen_size

            # Calculate the aspect ratio of the image and screen
            image_aspect_ratio = img_width / img_height
            screen_aspect_ratio = screen_width / screen_height

            # Scale the image to fit the screen without distortion
            if image_aspect_ratio > screen_aspect_ratio:
                # Fit to screen width
                new_img_width = screen_width
                new_img_height = int(screen_width / image_aspect_ratio)
            else:
                # Fit to screen height
                new_img_height = screen_height
                new_img_width = int(screen_height * image_aspect_ratio)

            # Scale the image
            img_surface = pygame.transform.scale(img, (new_img_width, new_img_height)).convert()
        except Exception as e:
            print(f"Error loading image with Pygame {image_path}: {e}")
            return None
    return img_surface

async def load_video(video_path):
    try:
        cap = cv2.VideoCapture(video_path)
        return cap
    except Exception as e:
        print(f"Error loading video with opencv {video_path}: {e}")
        return None
    
async def prepare_media_queue(screen_size):
    while True:
        announcement_files = []
        for directory_path, _, file_names in os.walk(announcement_directory):
            for announcement_filename in file_names:
                announcement_files.append(os.path.join(directory_path, announcement_filename))

        media_files = []
        for directory_path, _, file_names in os.walk(local_media_directory):
            for media_filename in file_names:
                media_files.append(os.path.join(directory_path, media_filename))

        for media_file in media_files:
            queue_full = (len(media_queue) >= 5)
            while queue_full:
                await asyncio.sleep(0.1)
                print("Queue full, waiting for media to be displayed.")
                queue_full = (len(media_queue) >= 5)

            media_type = None
            if media_file.lower().endswith(supported_image_formats):
                media = await load_image(media_file, screen_size)
                media_type = "Image"
            elif media_file.lower().endswith(supported_video_formats):
                media = await load_video(media_file)
                media_type = "Video"
            else:
                print(f"Unsupported media file: {media_file}")
            if media:
                media_queue.append(media)
                print(f"{media_type} added to queue.")

async def display_image(image, screen, fade_duration=1000, slide_duration=slide_duration):
    image_rect = image.get_rect(center=screen.get_rect().center)
    for alpha in range(0, 255, 5):  # Adjust step size to get brighter quicker or slower
        faded_alpha = alpha
        image.set_alpha(faded_alpha)
        screen.fill((0, 0, 0)) # Clear the screen with a black background
        # Blit the image onto the screen and update the display
        screen.blit(image, image_rect)
        events_to_handle = list(pygame.event.get())
        await handle_events(events_to_handle)
        pygame.display.update()
        clock.tick(60)
        # await asyncio.sleep(fade_duration // 5100) 
        pygame.time.delay(fade_duration // 51)
    pygame.display.update()
    clock.tick(60)
    events_to_handle = list(pygame.event.get())
    await handle_events(events_to_handle)
    await asyncio.sleep(slide_duration)
    for alpha in range(0, 255, 5):  # Adjust step size to get brighter quicker or slower
        faded_alpha = 255 - alpha
        image.set_alpha(faded_alpha)
        screen.fill((0, 0, 0)) # Clear the screen with a black background
        # Blit the image onto the screen and update the display
        screen.blit(image, image_rect)
        events_to_handle = list(pygame.event.get())
        await handle_events(events_to_handle)
        pygame.display.update()
        clock.tick(60)
        pygame.time.delay(fade_duration // 51)
        # await asyncio.sleep(fade_duration // 5100) 

async def scale_video_frame(frame, screen_size):
    frame_height, frame_width = frame.shape[:2]
    screen_width, screen_height = screen_size

    # Calculate the aspect ratios
    frame_aspect_ratio = frame_width / frame_height
    screen_aspect_ratio = screen_width / screen_height

    # Determine the scaling factor
    if frame_aspect_ratio > screen_aspect_ratio:
        # Video is wider than the screen, scale based on width
        new_width = screen_width
        new_height = int(screen_width / frame_aspect_ratio)
    else:
        # Video is taller or fits well, scale based on height
        new_height = screen_height
        new_width = int(screen_height * frame_aspect_ratio)

    # Resize the frame with the calculated dimensions
    scaled_frame = cv2.resize(frame, (new_width, new_height))
    return scaled_frame


async def display_video(video, screen):
    cap = video
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        # Convert OpenCV frame to pygame surface
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = await scale_video_frame(frame, screen_size) # Scale to screen size
        surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        screen.blit(surface, surface.get_rect(center=screen.get_rect().center))
        events_to_handle = list(pygame.event.get())
        await handle_events(events_to_handle)
        pygame.display.update()
        clock.tick(60)  # Frame rate for video
    cap.release()

async def pygame_loop(framerate_limit=60):
    task = asyncio.create_task(prepare_media_queue(screen_size))
    while True:
        if len(media_queue) > 0:
            media = media_queue.popleft()
            if isinstance(media, pygame.Surface):
                await display_image(media, screen)
            elif isinstance(media, cv2.VideoCapture):
                await display_video(media, screen)
            else:
                print(f"Unrecognized object. {type(media)}")
            events_to_handle = list(pygame.event.get())
            await handle_events(events_to_handle)
        else:
            await asyncio.sleep(0.1)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit() 
                exit() # Exit on quit event

if __name__ == "__main__":
    asyncio.run(pygame_loop(60))
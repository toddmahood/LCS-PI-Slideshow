import os
import json
import pygame
import asyncio
import logging
from PIL import Image
from collections import deque
from pyvidplayer2 import Video
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
log_path = data["log_directory"]
supported_image_formats = ('.ras', '.im', '.grib', '.qoi', '.jfif', '.pxr', '.pbm', '.rgb', '.pnm', '.hdf', '.sgi', '.jpf', '.icns', '.blp', '.jpeg', '.bw', '.rgba', '.ppm', '.tiff', '.pgm', '.xpm', '.mpeg', '.ftu', '.bufr', '.gif', '.ftc', '.pcx', '.jpg', '.fits', '.pcd', '.ps', '.apng', '.pfm', '.emf', '.jpe', '.tif', '.vst', '.fli', '.cur', '.dib', '.jp2', '.gbr', '.tga', '.icb', '.j2c', '.webp', '.ico', '.png', '.jpc', '.vda', '.h5', '.flc', '.msp', '.eps', '.j2k', '.iim', '.wmf', '.bmp', '.dcx', '.jpx', '.psd', '.fit', '.xbm', '.mpg', '.dds', '.heic', '.avif', '.exif', '.xmp', '.iptc', '.svg', '.lbm')
supported_video_formats = ('.avi', '.mp4', '.mov') # Probably more, but no official opencv list due to differences in codecs per install?

logging.basicConfig(filename=f'{log_path}', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S', level=logging.DEBUG)

# Set up the display
pygame.init()
pygame.display.set_caption("LCS Slideshow")
screen = pygame.display.set_mode((pygame.display.Info().current_w, pygame.display.Info().current_h), pygame.SCALED)
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
        if (img_width < 1200) or (img_height < 720):
            logging.info(f"Omitting image: {image_path}, too small...")
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
            logging.debug(f"Error obtaining EXIF information for {image_path}: {e}\nUsing default orientation...")

        # This nifty function handles the scaling for us!
        img.thumbnail(screen_size, Image.LANCZOS)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Convert Pillow image to pygame surface
        img_surface = pygame.image.fromstring(img.tobytes(), img.size, 'RGB').convert()
    except Exception as e:
        logging.error(f"Error loading image with PIL {image_path}: {e}")
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
            logging.error(f"Error loading image with Pygame {image_path}: {e}")
            return None
    return img_surface

async def load_video(video_path):
    try: 
        vid = Video(video_path)
        vid.change_resolution(screen_size[1])
        return vid
    except Exception as e:
        logging.error(f"Error loading video with pyvidplayer2 {video_path}: {e}")
        return None
    
async def prepare_media_queue(screen_size):
    while True:
        media_files = []
        num_announcements = 0
        for directory_path, _, file_names in os.walk(announcement_directory):
            for media_filename in file_names:
                media_files.append(os.path.join(directory_path, media_filename))
                num_announcements += 1

        for directory_path, _, file_names in os.walk(local_media_directory):
            for media_filename in file_names:
                media_files.append(os.path.join(directory_path, media_filename))

        for media_file in media_files:
            queue_full = (len(media_queue) >= 5)
            while queue_full:
                await asyncio.sleep(0.1)
                logging.info("Queue full, waiting for media to be displayed.")
                queue_full = (len(media_queue) >= 5)

            media_type = None
            if media_file.lower().endswith(supported_image_formats):
                media = await load_image(media_file, screen_size)
                if num_announcements != 0:
                    media_type = "Announcement"
                    num_announcements -= 1
                else:
                    media_type = "Image"
            elif media_file.lower().endswith(supported_video_formats):
                media = await load_video(media_file)
                if num_announcements != 0:
                    media_type = "Announcement"
                    num_announcements -= 1
                else:
                    media_type = "Video"
            else:
                logging.error(f"Unsupported media file: {media_file}")
                if num_announcements != 0:
                    media_type = "Announcement"
                    num_announcements -= 1
            if media != None:
                if media_type == "Announcement":
                    media_queue.append((media, True))
                else:
                    media_queue.append((media, False))
                logging.info(f"{media_type} added to queue.")

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

async def display_video(video, screen):
    video_width, video_height = video.current_size
    x_pos = (screen_size[0] - video_width) // 2
    y_pos = (screen_size[1] - video_height) // 2
    video_frame_rate = video.frame_rate
    logging.debug(f"Video Frame Rate: {video_frame_rate}")
    # Create overlay to mimic fading in and out.
    overlay = pygame.Surface(screen_size)
    overlay.fill((0, 0, 0))

    total_video_duration = video.duration  
    fade_in_duration = 1
    fade_out_duration = 1

    if total_video_duration < (fade_in_duration + fade_out_duration):
        scale_factor = total_video_duration / (fade_in_duration + fade_out_duration)
        fade_in_duration *= scale_factor
        fade_out_duration *= scale_factor

    while video.active:
        current_video_time = video.get_pos()
        if current_video_time < fade_in_duration:  # Fade-in
            fade_alpha = int(255 - (current_video_time / fade_in_duration) * 255)  # Start at 255, decrease to 0
        elif current_video_time >= (total_video_duration - fade_out_duration):
            fade_alpha = int(((current_video_time - (total_video_duration - fade_out_duration)) / fade_out_duration) * 255)  # Start at 0, increase to 255
        else:
            fade_alpha = 0
        logging.debug(f"Fade Alpha: {fade_alpha}")

        if video.draw(screen, (x_pos,y_pos), force_draw=False):
            if fade_alpha > 0:
                overlay.set_alpha(fade_alpha)
                screen.blit(overlay, (0, 0))
            pygame.display.update()
        events_to_handle = list(pygame.event.get())
        await handle_events(events_to_handle)
        clock.tick(video_frame_rate)  # Frame rate for video
    video.close()

async def pygame_loop(framerate_limit=60):
    try:
        task = asyncio.create_task(prepare_media_queue(screen_size))
        while True:
            try:
                if len(media_queue) > 0:
                    media, isAnnouncement = media_queue.popleft()
                    if isinstance(media, pygame.Surface):
                        if isAnnouncement:
                            await display_image(media, screen, slide_duration=announcement_duration)
                        else:
                            await display_image(media, screen)
                    elif isinstance(media, Video): 
                        await display_video(media, screen)
                    else:
                        logging.error(f"Unrecognized object. {type(media)}")
                    events_to_handle = list(pygame.event.get())
                    await handle_events(events_to_handle)
                else:
                    await asyncio.sleep(0.1)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit() 
                        exit() # Exit on quit event
            except Exception as e:
                logging.error(f"Error displaying image or processing events: {e}")
    except Exception as e:
        logging.error(f"Error in pygame_loop: {e}")

if __name__ == "__main__":
    asyncio.run(pygame_loop(60))

import os
import cv2
import json
import time
import pygame

# Initialize pygame
pygame.init()

with open("config.json") as file:
  data = json.load(file)

local_media_directory = data["local_media_directory"]

# Set up the display
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)  # Fullscreen mode
clock = pygame.time.Clock()

# Helper function to scale an image without distortion
def load_image_no_distortion(image_path, screen_size):
    # EXIF support needed, auto image rotation, 
    # Load the image
    img = pygame.image.load(image_path)
    
    # Get the original image dimensions
    image_width, image_height = img.get_size()
    screen_width, screen_height = screen_size

    # Calculate the aspect ratio of the image and screen
    image_aspect_ratio = image_width / image_height
    screen_aspect_ratio = screen_width / screen_height

    # Scale the image to fit the screen without distortion
    if image_aspect_ratio > screen_aspect_ratio:
        # Fit to screen width
        new_width = screen_width
        new_height = int(screen_width / image_aspect_ratio)
    else:
        # Fit to screen height
        new_height = screen_height
        new_width = int(screen_height * image_aspect_ratio)

    # Scale the image
    scaled_image = pygame.transform.scale(img, (new_width, new_height))

    return scaled_image

# Helper function for playing a video using OpenCV
def play_video(video_path, screen):
    cap = cv2.VideoCapture(video_path)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        # Convert OpenCV frame to pygame surface
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, screen.get_size())  # Scale to screen size
        surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        screen.blit(surface, (0, 0))
        pygame.display.update()
        clock.tick(30)  # Frame rate for video
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cap.release()
                return
    cap.release()

# Function to fade in/out an image
def fade_in_out(image, screen, fade_in=True, duration=1000):
    alpha_surface = pygame.Surface(screen.get_size())
    alpha_surface.fill((0, 0, 0))  # Black overlay
    for alpha in range(0, 255, 5):  # Adjust step size for speed of fade
        image_rect = image.get_rect(center=screen.get_rect().center)
        screen.blit(image, image_rect.topleft)
        if fade_in:
            alpha_surface.set_alpha(255 - alpha)
        else:
            alpha_surface.set_alpha(alpha)
        screen.blit(alpha_surface, (0, 0))
        pygame.display.update()
        pygame.time.delay(duration // 51)  # Adjust time for smoother fade

# Function to handle the slideshow
def run_slideshow(media_files):
    screen_size = screen.get_size()
    for media in media_files:
        if media.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.heic')):
            # Load and display image with fade-in and fade-out
            image = load_image_no_distortion(media, screen_size)
            image_rect = image.get_rect(center=screen.get_rect().center)
            fade_in_out(image, screen, fade_in=True)
            screen.blit(image, image_rect.topleft)

            pygame.display.update()
            time.sleep(2)  # Display for 2 seconds
            fade_in_out(image, screen, fade_in=False)
        
        elif media.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            # Play video
            play_video(media, screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return  # Exit on quit event

# Main loop
def main():

    # List of media files (mix of images and videos)
    media_filenames = []
    for directory_path, directory_name, file_names in os.walk(local_media_directory):
        for media_filename in file_names:
            media_filenames.append(os.path.join(directory_path, media_filename))

    run_slideshow(media_filenames)

    pygame.quit()

if __name__ == '__main__':
    main()









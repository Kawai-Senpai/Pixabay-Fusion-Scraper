import os
import time
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import TimeoutException
from ultraprint.logging import logger as create_logger  # renamed to avoid collision
from tqdm import tqdm  # For loading bar during chunk download
from dotenv import load_dotenv
from ultraconfiguration import UltraConfig

# load the configuration
config = UltraConfig("config.json")

# Load environment variables from .env file
load_dotenv()
API_KEY = os.environ.get("API_KEY")

TARGET_DOWNLOADS = config.get("target_downloads")
firefox_binary = config.get("firefox_binary")
download_format = config.get("download_format")
download_delay = config.get("download_delay")

# -----------------------------------------------------------------------------
# CONTENT TYPE SELECTION & CONFIGURATION
# -----------------------------------------------------------------------------
content_type = input("Choose content type (photos/videos): ").strip().lower()
if content_type == "photos":
    DOWNLOAD_FOLDER = os.path.join("data", "images", "photo_files")
    PROGRESS_FILE = os.path.join("data", "images", "progress.json")
    metadata_file = os.path.join("data", "images", "metadata.json")
    BASE_URL = "https://pixabay.com/photos/search/?order=ec&pagi={}"
else:
    DOWNLOAD_FOLDER = os.path.join("data", "videos", "video_files")
    PROGRESS_FILE = os.path.join("data", "videos", "progress.json")
    metadata_file = os.path.join("data", "videos", "metadata.json")
    BASE_URL = "https://pixabay.com/videos/search/?order=ec&pagi={}"

# -----------------------------------------------------------------------------
# CONFIGURATION & SETUP
# -----------------------------------------------------------------------------
# All data is stored under data folder; video files are in data/videos/video_files
for folder in [DOWNLOAD_FOLDER, os.path.dirname(PROGRESS_FILE)]:
    os.makedirs(folder, exist_ok=True)
log = create_logger('scraping_log', include_extra_info=False, write_to_file=False, log_level='DEBUG')
log.debug("Required directories are created or already exist")

# -----------------------------------------------------------------------------
# PROGRESS HANDLING
# -----------------------------------------------------------------------------
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            log.debug("Progress file loaded")
            return json.load(f)
    else:
        log.debug("No progress file found. Starting fresh.")
        return {"current_page": 1, "processed_urls": [], "total_downloaded": 0}

def update_progress(progress_data):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress_data, f, indent=2)
    log.debug("Progress updated")

progress = load_progress()

# -----------------------------------------------------------------------------
# FIREFOX DRIVER SETUP
# -----------------------------------------------------------------------------
options = Options()
options.binary_location = firefox_binary
if not os.path.exists(firefox_binary):
    log.error(f"Firefox binary not found at: {firefox_binary}")
    exit(1)
options.set_preference("browser.download.dir", DOWNLOAD_FOLDER)
options.set_preference("browser.download.folderList", 2)
options.set_preference("browser.helperApps.neverAsk.saveToDisk", download_format)
service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=service, options=options)
log.debug("Firefox WebDriver initialized")

# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS
# -----------------------------------------------------------------------------
def wait_for_element(driver, by, value, timeout=20):
    log.debug(f"Waiting for element by {by} with value {value} (timeout: {timeout}s)")
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except TimeoutException:
        log.error(f"Timeout waiting for element: {by} {value}")
        raise

# -----------------------------------------------------------------------------
# VIDEO PROCESSING
# -----------------------------------------------------------------------------
def process_video(url):
    log.info(f"Started processing video URL: {url}")
    if url in progress["processed_urls"]:
        log.info("Skipping already processed URL")
        return False
    
    try:
        # Open new tab and wait for load
        driver.execute_script(f"window.open('{url}');")
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(3)
        video_id = url.rstrip("/").split("-")[-1]
        log.debug(f"Extracted video ID: {video_id}")

        # Call Pixabay API for video metadata
        api_url = f"https://pixabay.com/api/videos/?key={API_KEY}&id={video_id}"
        log.debug(f"Requesting API: {api_url}")
        resp = requests.get(api_url)
        if resp.status_code != 200:
            log.error("API call failed")
            return False

        data = resp.json()
        if not data.get("hits"):
            log.error("No video data returned from API")
            return False

        video_info = data["hits"][0]
        log.info("Video info retrieved from API successfully")
        
        # Download the highest resolution video file
        # Select proper video resolution variant
        variants = video_info.get("videos", {})
        selected_variant = None
        for key in ["large", "medium", "small"]:
            variant = variants.get(key)
            if variant and variant.get("width", 0) >= 1920 and variant.get("height", 0) >= 1080:
                selected_variant = variant
                break
        if not selected_variant:
            log.error("No suitable resolution found (skipping video)")
            return False
        highest_url = selected_variant["url"]
        log.debug(f"Selected resolution URL: {highest_url}")
        
        video_resp = requests.get(highest_url, stream=True)
        if video_resp.status_code == 200:
            file_name = f"{video_id}_source.mp4"
            out_path = os.path.join(DOWNLOAD_FOLDER, file_name)
            
            total_size = int(video_resp.headers.get("Content-Length", 0))
            # Use tqdm progress bar if total_size is known
            if total_size:
                progress_bar = tqdm(total=total_size, unit="B", unit_scale=True, desc="Downloading")
            else:
                progress_bar = None

            with open(out_path, "wb") as f:
                for chunk in video_resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        if progress_bar:
                            progress_bar.update(len(chunk))
            if progress_bar:
                progress_bar.close()

            log.info(f"Downloaded video file: {file_name}")

            # Prepare and save metadata
            item_data = {
                "page": progress["current_page"],
                "page_link": url,
                "video_id": video_id,
                "download_file": file_name,
                "download_path": out_path,
                "metadata": video_info,
                "timestamp": datetime.now().isoformat()
            }
            with open(metadata_file, "a") as f:
                f.write(json.dumps(item_data))
                f.write("\n")
            log.debug("Appended video metadata to file")

            # Update progress data
            progress["processed_urls"].append(url)
            progress["total_downloaded"] += 1
            log.info(f"Processed {progress['total_downloaded']} videos so far")
            return True
        else:
            log.error("Video download failed")
            return False
    except Exception as e:
        log.error(f"Error processing video URL: {str(e)}")
        return False
    finally:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        update_progress(progress)

# -----------------------------------------------------------------------------
# PHOTO PROCESSING
# -----------------------------------------------------------------------------
def process_photo(url):
    log.info(f"Started processing photo URL: {url}")
    if url in progress["processed_urls"]:
        log.info("Skipping already processed URL")
        return False
    
    try:
        driver.execute_script(f"window.open('{url}');")
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(3)
        photo_id = url.rstrip("/").split("-")[-1]
        log.debug(f"Extracted photo ID: {photo_id}")

        api_url = f"https://pixabay.com/api/?key={API_KEY}&id={photo_id}"
        log.debug(f"Requesting API: {api_url}")
        resp = requests.get(api_url)
        if resp.status_code != 200:
            log.error("API call failed")
            return False

        data = resp.json()
        if not data.get("hits"):
            log.error("No photo data returned from API")
            return False

        photo_info = data["hits"][0]
        log.info("Photo info retrieved from API successfully")
        
        # Choose high resolution image - prefer largeImageURL, fallback to webformatURL
        image_url = photo_info.get("largeImageURL") or photo_info.get("webformatURL")
        if not image_url:
            log.error("No suitable image URL found (skipping photo)")
            return False
        log.debug(f"Selected image URL: {image_url}")
        
        image_resp = requests.get(image_url, stream=True)
        if image_resp.status_code == 200:
            file_name = f"{photo_id}_source.jpg"
            out_path = os.path.join(DOWNLOAD_FOLDER, file_name)
            
            total_size = int(image_resp.headers.get("Content-Length", 0))
            progress_bar = tqdm(total=total_size, unit="B", unit_scale=True, desc="Downloading") if total_size else None

            with open(out_path, "wb") as f:
                for chunk in image_resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        if progress_bar:
                            progress_bar.update(len(chunk))
            if progress_bar:
                progress_bar.close()

            log.info(f"Downloaded photo file: {file_name}")

            item_data = {
                "page": progress["current_page"],
                "page_link": url,
                "photo_id": photo_id,
                "download_file": file_name,
                "download_path": out_path,
                "metadata": photo_info,
                "timestamp": datetime.now().isoformat()
            }
            with open(metadata_file, "a") as f:
                f.write(json.dumps(item_data))
                f.write("\n")
            log.debug("Appended photo metadata to file")

            progress["processed_urls"].append(url)
            progress["total_downloaded"] += 1
            log.info(f"Processed {progress['total_downloaded']} photos so far")
            return True
        else:
            log.error("Photo download failed")
            return False
    except Exception as e:
        log.error(f"Error processing photo URL: {str(e)}")
        return False
    finally:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        update_progress(progress)

# -----------------------------------------------------------------------------
# MAIN SCRAPING LOOP
# -----------------------------------------------------------------------------
def main():
    try:
        while progress["total_downloaded"] < TARGET_DOWNLOADS:
            page = progress["current_page"]
            log.info(f"Processing page {page}")
            driver.get(BASE_URL.format(page))
            
            if content_type == "videos":
                input("Press Enter after you have logged in. [Enter]")

            # Scroll to load all items
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(download_delay)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    log.debug("Reached end of page scrolling")
                    break
                last_height = new_height

            links = [el.get_attribute("href")
                    for el in driver.find_elements(By.CSS_SELECTOR, "a.link--WHWzm")]
            log.info(f"Found {len(links)} links on page {page}")
            
            for url in links:
                if url in progress["processed_urls"]:
                    continue
                if progress["total_downloaded"] >= TARGET_DOWNLOADS:
                    log.info("Reached target download count")
                    break
                if content_type == "videos":
                    if process_video(url):
                        log.info(f"Progress: {progress['total_downloaded']}/{TARGET_DOWNLOADS}")
                else:
                    if process_photo(url):
                        log.info(f"Progress: {progress['total_downloaded']}/{TARGET_DOWNLOADS}")
            
            progress["current_page"] += 1
            update_progress(progress)
    except Exception as e:
        log.error(f"Fatal error during scraping: {str(e)}")
    finally:
        driver.quit()
        log.info("Scraping completed")

if __name__ == "__main__":
    main()
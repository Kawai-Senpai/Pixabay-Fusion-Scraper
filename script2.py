import os
import time
import json
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('pixabay_video_scraper')

BASE_STORAGE = "/Volumes/SSD_PrakharPandey/pixabay data"
VIDEO_FOLDER = os.path.join(BASE_STORAGE, "videos")
METADATA_FOLDER = os.path.join(BASE_STORAGE, "metadata")
PROGRESS_FILE = os.path.join(BASE_STORAGE, "scrape_progress.json")

# Create directories
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(METADATA_FOLDER, exist_ok=True)

# Initialize progress
try:
    with open(PROGRESS_FILE, "r") as f:
        progress = json.load(f)
except FileNotFoundError:
    progress = {
        "current_page": 1,
        "processed_urls": [],
        "total_downloaded": 0
    }

# Firefox setup
options = Options()
# Change firefox binary location to a valid Windows path using a raw string:
options.binary_location = "C:/Program Files/Mozilla Firefox/firefox.exe"

# Verify that the binary exists and is executable
if not os.path.exists(options.binary_location):
    logger.error(f"Firefox binary not found at: {options.binary_location}")
    exit(1)

options.set_preference("browser.download.dir", VIDEO_FOLDER)
options.set_preference("browser.download.folderList", 2)
options.set_preference("browser.helperApps.neverAsk.saveToDisk", "video/mp4")

service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=service, options=options)

def wait_for_element(driver, by, value, timeout=20):
    logger.debug(f"Waiting for element by {by} with value {value} and timeout {timeout}")
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def get_metadata(driver, url):
    logger.info(f"Extracting metadata from URL: {url}")
    try:
        # Get description from URL
        video_slug = url.split("/")[-2]
        description = " ".join(video_slug.split("-")[:-1])  # Remove ID number
        logger.debug(f"Extracted description: {description}")
        
        # Get likes
        likes_element = wait_for_element(driver, By.CSS_SELECTOR, "div.text--MrmlD")
        likes = likes_element.text
        logger.debug(f"Extracted likes: {likes}")
        
        # Get views and downloads
        stats = driver.find_elements(By.CSS_SELECTOR, "span.rowLabel--VPSZI")
        views = stats[0].text if len(stats) > 0 else "N/A"
        downloads = stats[1].text if len(stats) > 1 else "N/A"
        logger.debug(f"Extracted views: {views}, downloads: {downloads}")
        
        # Get tags
        tags = [tag.text for tag in driver.find_elements(
            By.CSS_SELECTOR, "div.tagsSection--8gH54 .label--Ngqjq"
        )]
        logger.debug(f"Extracted tags: {tags}")
        
        return {
            "description": description,
            "views": views,
            "downloads": downloads,
            "likes": likes,
            "tags": tags
        }
    except Exception as e:
        logger.error(f"Metadata extraction failed: {str(e)}")
        return None

def handle_download(driver):
    max_attempts = 3
    logger.info("Starting download process")
    
    for attempt in range(max_attempts):
        logger.debug(f"Attempt {attempt + 1} of {max_attempts}")
        try:
            # 1. Click the primary download button (arrow)
            download_arrow_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.fullWidthTrigger--c4aeO"))
            )
            driver.execute_script("arguments[0].click();", download_arrow_btn)
            logger.info("Clicked the download arrow button.")
            time.sleep(2)  # Wait for resolution options to appear
            
            # 2. Select the "video-<id>_source.mp4" resolution
            try:
                # Wait for dropdown menu to appear
                resolution_options = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "label.input--b6Wi1"))
                )
                
                source_option = None
                for option in resolution_options:
                    input_element = option.find_element(By.TAG_NAME, "input")  # Find the <input> element
                    value = input_element.get_attribute("value")  # Get the value attribute
                    if "_source.mp4" in value:  # Check if it's the source.mp4 option
                        source_option = option
                        break
                
                if source_option:
                    # Click the label associated with the source.mp4 option
                    driver.execute_script("arguments[0].click();", source_option)  # Use JavaScript click on label
                    logger.info(f"Selected 'source.mp4' resolution: {value}")
                    time.sleep(2)  # Allow time for selection
                    
                    # 3. Handle download confirmation (if required)
                    try:
                        final_btn = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.buttonBase--r4opq:not([target='_blank'])"))
                        )
                        driver.execute_script("arguments[0].click();", final_btn)
                        logger.info("Clicked final download confirmation.")
                    except TimeoutException:
                        logger.info("No confirmation needed, proceeding with default.")
                    
                    # 4. Verify download started
                    initial_files = set(os.listdir(VIDEO_FOLDER))
                    start_time = time.time()
                    while time.time() - start_time < 10:  # Increased timeout to 10 seconds
                        current_files = set(os.listdir(VIDEO_FOLDER))
                        new_files = current_files - initial_files
                        if any(f.endswith('.mp4') for f in new_files):
                            logger.info("Download detected!")
                            return True
                        time.sleep(2)
                    
                    logger.warning(f"Download not detected after attempt {attempt + 1}.")
                else:
                    logger.warning("'source.mp4' option not found. Skipping to next video.")
                    return False  # Skip to next video if source.mp4 is not found
            except (TimeoutException, NoSuchElementException) as e:
                logger.warning(f"Failed to select resolution: {str(e)}. Skipping to next video.")
                return False
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Refreshing and trying again.")
            time.sleep(2)
            driver.refresh()  # Reset page state
            continue
    
    logger.error("All download attempts failed for this video. Skipping to next video.")
    return False

def process_video(url):
    logger.info(f"Processing video URL: {url}")
    if url in progress["processed_urls"]:
        logger.info(f"URL already processed: {url}")
        return False
    
    try:
        driver.execute_script(f"window.open('{url}');")
        driver.switch_to.window(driver.window_handles[1])
        
        metadata = get_metadata(driver, url)
        if not metadata:
            return False
        
        if handle_download(driver):
            # Save metadata
            video_id = url.split("/")[-2]
            metadata.update({
                "video_id": video_id,
                "download_time": datetime.now().isoformat(),
                "source_url": url
            })
            
            with open(os.path.join(METADATA_FOLDER, f"{video_id}.json"), "w") as f:
                json.dump(metadata, f, indent=2)
            
            progress["processed_urls"].append(url)
            progress["total_downloaded"] += 1
            logger.info(f"Successfully processed: {video_id}")
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        return False
    finally:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)

def main():
    try:
        # Change for range
        while progress["total_downloaded"] < 6000:
            page = progress["current_page"]
            logger.info(f"Processing page {page}")
            
            driver.get(f"https://pixabay.com/videos/search/?order=ec&pagi={page}")
            
            # Load all videos
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Get video links
            video_links = [
                el.get_attribute("href")
                for el in driver.find_elements(By.CSS_SELECTOR, "a.link--WHWzm")
            ]
            
            for url in video_links:
                # Change accordingly
                if progress["total_downloaded"] >= 6000:
                    break
                if process_video(url):
                    # Updated progress display
                    logger.info(f"Progress: {progress['total_downloaded']}/6000")
            
            progress["current_page"] += 1
            with open(PROGRESS_FILE, "w") as f:
                json.dump(progress, f, indent=2)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        driver.quit()
        logger.info("Scraping completed")

if __name__ == "__main__":
    main()
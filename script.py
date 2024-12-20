import time
import json
import os
from seleniumwire import webdriver  # Import from seleniumwire
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from ultraprint.logging import logger

# Create a logger object
log = logger('scraping_log', include_extra_info=False, write_to_file=False, log_level='DEBUG')

# Initialize the driver
log.debug("Initializing the Firefox WebDriver")

# Parameters
base_url = "https://pixabay.com/music/search/?order=ec&pagi="
audio_folder = "data\\audio_files"
metadata_dile = "data\\metadata.json"
max_pages = 100
start_page = 1

# set default download directory
download_dir = os.path.join(os.getcwd(), audio_folder)

# Set the download directory
log.debug(f"Setting the download directory to {download_dir}")
profile = webdriver.FirefoxProfile()
profile.set_preference("browser.download.folderList", 2)
profile.set_preference("browser.download.manager.showWhenStarting", False)
profile.set_preference("browser.download.dir", download_dir)
profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "audio/mpeg")
profile.set_preference("browser.download.useDownloadDir", True)
profile.set_preference("browser.download.panel.shown", False)

options = Options()
options.profile = profile
driver = webdriver.Firefox(options=options)

# Load the page
log.debug(f"Loading the page at {base_url}")
driver.get(base_url+str(start_page))

if not os.path.exists(audio_folder):
    log.debug(f"Creating audio folder at {audio_folder}")
    os.makedirs(audio_folder)

def get_downloaded_file_name():
    for request in driver.requests:
        if request.response and 'cdn.pixabay.com/download/audio' in request.url:
            file_name = request.url.split('filename=')[-1]
            return file_name

def wait_for_element(driver, by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def scroll_to_element(driver, element):
    driver.execute_script("arguments[0].scrollIntoView();", element)

for page in range(start_page, max_pages+1):
    log.debug(f"Processing page {page}")
    
    media_items = driver.find_elements(By.CLASS_NAME, "name--q8l1g")
    log.debug(f"Found {len(media_items)} media items on page {page}")

    for item in media_items:
        try:
            # get the href
            audio_page_link = item.get_attribute("href")
            log.debug(f"Found audio page link: {audio_page_link}")

            # Load the audio page (new tab)
            log.debug(f"Loading the audio page at {audio_page_link}")

            # Open a new tab
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[1])
            driver.get(audio_page_link)

            # Wait for elements to be available
            title_card = wait_for_element(driver, By.CLASS_NAME, "title--VRujt")
            music_name = title_card.text
            log.info(f"Music name: {music_name}")

            attribution_card = wait_for_element(driver, By.CLASS_NAME, "userName--owby3")
            credits = attribution_card.get_attribute("href")
            log.info(f"Credits link: {credits}")

            tags_parent = wait_for_element(driver, By.CLASS_NAME, "tagsSection--8gH54")
            scroll_to_element(driver, tags_parent)
            # Re-fetch the tags_parent element to avoid stale element reference
            tags_parent = wait_for_element(driver, By.CLASS_NAME, "tagsSection--8gH54")
            tags_cards = tags_parent.find_elements(By.CLASS_NAME, "label--Ngqjq")
            tags = [tag.text for tag in tags_cards]
            log.info(f"Tags: {tags}")
            
            side_panel = wait_for_element(driver, By.CLASS_NAME, "sidePanel--XFASR")
            scroll_to_element(driver, side_panel)
            download_button = side_panel.find_element(By.CLASS_NAME, "triggerWrapper--NACCC")
            final_download_button = download_button.find_element(By.TAG_NAME, "button")
            final_download_button.click()
            log.debug("Clicked download button")

            time.sleep(1)

            # Wait for the download button to appear
            download_button = wait_for_element(driver, By.CLASS_NAME, "buttons--cqw3Y")
            button = download_button.find_element(By.CLASS_NAME, "label--Ngqjq")
            button.click()
            log.debug("Clicked final download button")

            log.debug("Waiting for download to complete...")
            while not get_downloaded_file_name():
                time.sleep(1)
            
            file_name = get_downloaded_file_name()
            log.debug(f"Downloaded file name: {file_name}")

            data = {
                "music_name": music_name,
                "credits": credits,
                "tags": tags,
                "file_name": file_name
            }

            # Save the data (append to the file)
            with open(metadata_dile, "a") as f:
                f.write(json.dumps(data))
                f.write("\n")
            log.debug("Saved metadata to file")

        except Exception as e:
            log.error(f"Error processing item: {e}")
        
        finally:
            # Close the current tab and switch back to the main tab
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            log.debug("Closed current tab and switched back to main tab")

    driver.get(base_url+str(page+1))
    log.debug(f"Loaded next page: {base_url+str(page+1)}")
import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import requests

# Set up Chrome WebDriver with options
options = Options()
options.headless = False  # Set to True to run without opening the browser window

# Initialize the driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Base URL and audio folder setup
base_url = "https://pixabay.com/music/search/?order=ec&pagi="
audio_folder = "audio_files"
if not os.path.exists(audio_folder):
    os.makedirs(audio_folder)


# Function to get audio details from each individual audio page
def get_audio_details(audio_url):
    driver.get(audio_url)
    time.sleep(2)  # Wait for the page to load

    # Extracting audio details
    title = driver.find_element(By.CSS_SELECTOR, 'h1').text.strip()
    genre = driver.find_element(By.CSS_SELECTOR, '.category').text.strip()
    singer_album = driver.find_element(By.CSS_SELECTOR, '.artist').text.strip()
    description = driver.find_element(By.CSS_SELECTOR, '.description').text.strip()

    # Get the audio file URL
    audio_file = driver.find_element(By.CSS_SELECTOR, 'audio').get_attribute('src')

    return {
        'title': title,
        'genre': genre,
        'singer_album': singer_album,
        'description': description,
        'audio_file': audio_file
    }


# Function to scrape all audio files on a single page
def scrape_audio_on_page(page_num):
    url = base_url + str(page_num)
    driver.get(url)
    time.sleep(3)  # Wait for the page to load

    # Find each audio entry on the page
    audio_links = driver.find_elements(By.CSS_SELECTOR, 'a.media__item')
    page_audio_data = []

    for audio in audio_links:
        audio_url = audio.get_attribute('href')

        # Navigate to audio page, scrape data, and then return to the main page
        driver.get(audio_url)
        time.sleep(2)  # Wait for the audio page to load

        audio_details = get_audio_details(audio_url)
        page_audio_data.append(audio_details)

        # Go back to the main page after scraping the audio
        driver.back()
        time.sleep(2)  # Wait for the page to load

    return page_audio_data


# Save data to a JSON file
def save_data_to_json(data, filename='audio_data.json'):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# Scrape all pages
def scrape_all_pages(total_pages=4745):
    all_audio_data = []

    for page_num in range(1, total_pages + 1):
        try:
            print(f"Scraping page {page_num}...")
            page_data = scrape_audio_on_page(page_num)
            all_audio_data.extend(page_data)

            # Save data after each page
            save_data_to_json(all_audio_data)

            # Optionally, download the audio files
            for idx, data in enumerate(page_data):
                audio_url = data['audio_file']
                audio_response = requests.get(audio_url)
                audio_filename = f"{audio_folder}/audio_{len(all_audio_data)}_{idx + 1}.mp3"

                with open(audio_filename, 'wb') as audio_file:
                    audio_file.write(audio_response.content)

            # Wait before scraping the next page to avoid overwhelming the server
            time.sleep(2)  # Adjust the sleep time as needed (e.g., 1-3 seconds)

        except Exception as e:
            print(f"Error scraping page {page_num}: {e}")
            continue

    print("Scraping complete.")


# Start the scraping process
scrape_all_pages(total_pages=4745)

# Quit the WebDriver after scraping is complete
driver.quit()

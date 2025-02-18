# Pixabay Scraper :camera: :video_camera:

:tada: Welcome to **Pixabay Scraper**! A versatile and user-friendly tool designed to effortlessly download high-quality photos and videos from Pixabay. :tada:

---

## :eyes: Overview

This program provides a menu-driven interface, allowing you to choose between scraping photos or videos from Pixabay. Leveraging the Pixabay API and Selenium for browser automation, it ensures high-quality media downloads with ease.

---

## :sparkles: Features

-   :keyboard: **Menu-Driven Interface**: Select between photos and videos at the start of the program.
-   :arrow_down: **High-Quality Downloads**:
    -   For videos, the scraper intelligently selects the best available resolution, excluding low-quality "tiny" options.
    -   For photos, it prioritizes `largeImageURL` and gracefully falls back to `webformatURL` when necessary.
-   :recycle: **Progress Handling**: Automatically saves progress, allowing you to resume scraping sessions without losing your place.
-   :scroll: **Detailed Logging**: Utilizes a custom logger to provide comprehensive debug and activity logs, ensuring transparency and easy troubleshooting.
-   :wrench: **Highly Configurable**: Easily adjust settings via a `config.json` file and environment variables, tailoring the scraper to your specific needs.

---

## :gear: Prerequisites

Before you begin, ensure you have the following:

-   :snake: **Python 3.x**: Make sure Python 3 or higher is installed.
-   :firefox: **Firefox Browser**: The scraper relies on Firefox for browser automation.
-   :globe_with_meridians: **GeckoDriver**: WebDriver Manager automatically handles GeckoDriver installation.
-   :package: **Required Python Packages**:
    -   Selenium
    -   webdriver-manager
    -   requests
    -   tqdm
    -   python-dotenv
    -   ultraprint
    -   ultraconfiguration

    Install the dependencies using pip:

    ```bash
    pip install -r requirements.txt
    ```

    > :bulb: *Note*: Ensure you have a valid `.env` file with your Pixabay API key.

---

## :hammer: Setup

Follow these steps to set up the Pixabay Scraper:

1.  **:file_folder: Configuration**:

    -   Create a `config.json` file to customize the scraper's behavior. This file allows you to specify settings such as:
        -   `target_downloads`: The number of media items to download.
        -   `firefox_binary`: The path to your Firefox binary.
        -   `download_format`: The file format for downloads.
        -   `download_delay`: The delay between each download request.

    Example `config.json`:

    ```json
    {
        "target_downloads": 100,
        "firefox_binary": "/usr/bin/firefox",
        "download_format": "application/mp4",
        "download_delay": 2
    }
    ```

2.  **:key: API Key Setup**:

    -   Obtain a Pixabay API key from the [Pixabay website](https://pixabay.com/api/docs/).
    -   Create a `.env` file in the root directory of the project and add your API key:

    ```properties
    API_KEY=your_pixabay_api_key
    ```

3.  **:open_file_folder: Folder Structure**:

    -   Video downloads will be stored in the `data/audio/audio_files` directory.
    -   Photo downloads will be stored in the `data/images/photo_files` directory.
    -   Progress and metadata are stored in corresponding `progress.json` and `metadata.json` files within their respective directories.

---

## :rocket: Usage

1.  :terminal: Open your terminal and navigate to the project directory.

2.  :running: Run the scraper:

    ```bash
    python scrape.py
    ```

3.  :point_up: When prompted, select the content type by typing **photos** or **videos** and press Enter.

4.  :lock: For videos, if login is required, follow the on-screen instructions and press Enter once you've logged in.

5.  :mag_right: The scraper will automatically scroll through the page, download media, and update its progress.

---

## :clipboard: Logging

The scraper provides detailed logs to the console, allowing you to monitor its progress and troubleshoot any issues. You can customize the logging level in the configuration section.

---

## :wrench: Troubleshooting

-   :no_entry_sign: **Firefox Binary Not Found**:
    -   Ensure the correct path to your Firefox binary is specified in the `config.json` file.
-   :warning: **API Issues**:
    -   Verify that your API key is correct and that the Pixabay API is reachable.
-   :hourglass: **Incomplete Downloads**:
    -   The scraper saves progress in `progress.json`, allowing you to resume interrupted sessions.

---

## :page_facing_up: License

This tool is provided "as is", without any warranty. Use at your own risk.

---

:smiley: Happy Scraping! :smiley:
````

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Change this to your Django homepage URL
DJANGO_HOME_URL = "http://127.0.0.1:8000"
SCREENSHOTS = {
    "homepage":"http://127.0.0.1:8000",
    "blog":"http://127.0.0.1:8000/blog",
    "blog_details":"http://127.0.0.1:8000/blog/serverless-functions-and-ai-building-scalable-event-driven-ml-pipelines/",
    "admin":"http://127.0.0.1:8000/admin",
}
def take_screenshot(url, output_file="screenshots/homepage.png"):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1280,800")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    time.sleep(15)  # wait for the page to load (adjust if needed)
    driver.save_screenshot(output_file)
    driver.quit()
    print(f"Screenshot saved to {output_file}")

if __name__ == "__main__":
    for key, val in SCREENSHOTS.items():
        path = 'screenshots/' + key + ".png"
        take_screenshot(val, path)

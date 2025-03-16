"""
Direct scraper to get season URLs from Vogue.
This is to debug the season extraction issue.
"""

import sys
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Function to set up Chrome driver
def setup_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument('--user-agent=Fashion Research (beborico16@gmail.com)')
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.implicitly_wait(10)
    return driver

# Function to save page source
def save_page_source(driver, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(f"Saved page source to {filename}")

# Function to extract seasons using a different approach
def extract_seasons_direct(driver):
    print("Getting seasons from Vogue fashion shows page")
    
    try:
        driver.get("https://www.vogue.com/fashion-shows")
        time.sleep(5)  # Wait for page to load
        
        # Save the page source for inspection
        save_page_source(driver, "ultrafast/data/fashion_shows_page.html")
        
        # Try to find season links directly
        all_links = driver.find_elements(By.TAG_NAME, "a")
        print(f"Found {len(all_links)} links on the page")
        
        season_links = []
        for link in all_links:
            try:
                href = link.get_attribute("href")
                text = link.text.strip()
                
                if href and text and "/fashion-shows/" in href:
                    if any(season in text for season in ["SPRING", "FALL", "RESORT", "COUTURE"]):
                        print(f"Found season link: {text} - {href}")
                        season_links.append({"text": text, "url": href})
            except Exception as e:
                pass
        
        print(f"Found {len(season_links)} season links")
        
        # Try to find any season navigation sections with XPath
        print("Looking for season navigation sections with XPath...")
        nav_sections = driver.find_elements(
            By.XPATH, "//nav[contains(@class, 'Navigation')]"
        )
        print(f"Found {len(nav_sections)} navigation sections")
        
        for i, section in enumerate(nav_sections):
            print(f"Navigation section {i+1} classes: {section.get_attribute('class')}")
            
            # Try to find headers
            headers = section.find_elements(By.TAG_NAME, "h2")
            for header in headers:
                print(f"Header in section {i+1}: {header.text}")
            
            # Try to find links
            links = section.find_elements(By.TAG_NAME, "a")
            print(f"Found {len(links)} links in section {i+1}")
            for link in links:
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    if href and text:
                        print(f"  Link: {text} - {href}")
                except:
                    pass
        
        # Look for any list with runway links
        print("Looking for lists with runway links...")
        lists = driver.find_elements(By.TAG_NAME, "ul")
        for i, list_elem in enumerate(lists):
            try:
                links = list_elem.find_elements(By.TAG_NAME, "a")
                if links and len(links) > 0:
                    runway_links = [link for link in links if link.get_attribute("href") and "/fashion-shows/" in link.get_attribute("href")]
                    if runway_links and len(runway_links) > 5:  # Likely a season list if it has many runway links
                        print(f"Potential season list #{i} with {len(runway_links)} runway links")
                        for link in runway_links[:5]:  # Show first 5 links
                            print(f"  {link.text} - {link.get_attribute('href')}")
            except:
                pass
                
        return season_links
        
    except Exception as e:
        print(f"Error extracting seasons: {str(e)}")
        return []
    finally:
        # Take a screenshot for debugging
        driver.save_screenshot("ultrafast/data/fashion_shows_screenshot.png")
        print("Saved screenshot to ultrafast/data/fashion_shows_screenshot.png")

if __name__ == "__main__":
    driver = None
    try:
        driver = setup_chrome_driver()
        seasons = extract_seasons_direct(driver)
        print(f"Extracted {len(seasons)} seasons")
        
        # Save seasons to file
        if seasons:
            with open("ultrafast/data/seasons_direct.txt", "w") as f:
                for season in seasons:
                    f.write(f"{season['text']} - {season['url']}\n")
            print("Saved seasons to ultrafast/data/seasons_direct.txt")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if driver:
            driver.quit()
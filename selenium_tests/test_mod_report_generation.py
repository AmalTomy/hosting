import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import time
from pathlib import Path

def test_mod_booking_report():
    """Test moderator bus booking report generation functionality"""
    print("\n=== Starting Moderator Bus Booking Report Test ===")
    
    # Setup Chrome options for download
    chrome_options = webdriver.ChromeOptions()
    download_dir = str(Path.home() / "Downloads")
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True
    })
    
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    
    try:
        # Step 1: Login
        print("Step 1: Logging in as moderator...")
        driver.get("http://localhost:8000/login")
        
        # Wait for login form and enter credentials
        email_input = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Type your email']"))
        )
        password_input = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Type your password']"))
        )
        
        email_input.send_keys("antonthomas4u@gmail.com")
        password_input.send_keys("Anton@123")
        print("Credentials entered")
        
        # Click login button
        login_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Login']"))
        )
        login_button.click()
        print("Login button clicked")

        # Step 2: Click Bus Bookings button with more specific locator and wait
        print("\nStep 2: Clicking Bus Bookings button...")
        time.sleep(2)  # Wait for page to fully load
        
        try:
            # Try multiple approaches to find the button
            try:
                # First attempt - by link text
                bus_bookings_link = wait.until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Bus Bookings"))
                )
            except:
                try:
                    # Second attempt - by partial link text
                    bus_bookings_link = wait.until(
                        EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Bus Bookings"))
                    )
                except:
                    try:
                        # Third attempt - by specific XPath
                        bus_bookings_link = wait.until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Bus Bookings')]"))
                        )
                    except:
                        # Fourth attempt - by CSS selector
                        bus_bookings_link = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.nav-link[href*='bus_bookings']"))
                        )

            print("Found Bus Bookings button")
            
            # Scroll the button into view
            driver.execute_script("arguments[0].scrollIntoView(true);", bus_bookings_link)
            time.sleep(1)  # Wait for scroll to complete
            
            # Try JavaScript click if regular click doesn't work
            try:
                bus_bookings_link.click()
            except:
                driver.execute_script("arguments[0].click();", bus_bookings_link)
                
            print("Clicked Bus Bookings button")
            
            # Wait for the bookings page to load
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "bus-card"))
            )
            print("Bus Bookings page loaded successfully")
            
        except Exception as e:
            print(f"Error clicking Bus Bookings button: {str(e)}")
            print("Current URL:", driver.current_url)
            print("Page source:", driver.page_source)
            raise

        # Step 3: Find and click View Bus Schedules for AStar Travels
        print("\nStep 3: Opening bus schedules...")
        view_schedules_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'bus-card')]//div[contains(text(), 'AStar Travels')]/..//button[contains(@class, 'view-schedules-btn')]"))
        )
        view_schedules_btn.click()
        print("Clicked View Bus Schedules button")
        
        # Step 4: Find and click View Bookings for specific schedule
        print("\nStep 4: Opening bookings for specific schedule...")
        time.sleep(2)  # Wait for modal to load
        
        try:
            # Find the specific schedule row and its View Bookings button
            schedule_row_xpath = "//tr[contains(., 'Kochi') and contains(., 'Havelock Island') and contains(., '2024-10-29') and contains(., '12:05') and contains(., '3500.00')]//button[contains(@class, 'view-bookings-btn')]"
            view_bookings_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, schedule_row_xpath))
            )
            
            # Scroll the button into view if needed
            driver.execute_script("arguments[0].scrollIntoView(true);", view_bookings_btn)
            time.sleep(1)  # Wait for scroll to complete
            
            # Click the button
            try:
                view_bookings_btn.click()
            except:
                driver.execute_script("arguments[0].click();", view_bookings_btn)
                
            print("Clicked View Bookings button for Kochi to Havelock Island schedule")
            
        except Exception as e:
            print(f"Error finding/clicking View Bookings button: {str(e)}")
            print("Available schedules:")
            schedules = driver.find_elements(By.XPATH, "//tr")
            for schedule in schedules:
                print(schedule.text)
            raise

        # Step 5: Download PDF report
        print("\nStep 5: Downloading PDF report...")
        time.sleep(2)  # Wait for bookings to load
        
        # Delete existing file if it exists
        filename = "Bus_Bookings_AStar Travels.pdf"
        filepath = os.path.join(download_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Removed existing file: {filepath}")
        
        download_btn = wait.until(
            EC.element_to_be_clickable((By.CLASS_NAME, "download-btn"))
        )
        download_btn.click()
        print("Clicked Download PDF button")
        
        # Wait for download to complete
        print("Waiting for download to complete...")
        timeout = time.time() + 30
        downloaded = False
        
        while time.time() < timeout:
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'rb') as file:
                        file.read()
                        downloaded = True
                        print(f"File downloaded successfully: {filepath}")
                        break
                except (IOError, PermissionError):
                    pass
            time.sleep(1)
            
        if downloaded:
            print("\n✅ MODERATOR BOOKING REPORT TEST PASSED!")
            print("=====================================")
            print("✓ Successfully logged in as moderator")
            print("✓ Navigated to Bus Bookings")
            print("✓ Viewed bus schedules")
            print("✓ Viewed bookings")
            print("✓ Downloaded PDF report")
            print("=====================================")
        else:
            print("\n❌ DOWNLOAD TEST FAILED!")
            print("=====================================")
            print("✗ PDF download failed or timeout")
            print("=====================================")
            raise TimeoutException("Download timeout")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        raise
        
    finally:
        print("\nClosing browser...")
        driver.quit()
        print("Test completed")

if __name__ == "__main__":
    test_mod_booking_report()
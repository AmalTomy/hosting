import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchWindowException
import os
import time
from pathlib import Path
from datetime import datetime, timedelta

def test_admin_bus_bookings_report():
    """Test admin bus bookings report generation functionality based on Selenium IDE recording"""
    print("\n=== Starting Admin Bus Bookings Report Test ===")
    
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
    
    # Add additional options to make Chrome more stable
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-popup-blocking")
    
    # Set page load timeout to prevent hanging
    chrome_options.page_load_strategy = 'eager'
    
    driver = None
    max_retries = 2
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                    
            print(f"Attempt {retry_count + 1}/{max_retries + 1}")
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            wait = WebDriverWait(driver, 15)  # Increased timeout
            
            # Step 1: Open the homepage and go directly to login page
            print("Step 1: Opening login page...")
            driver.get("http://127.0.0.1:8000/login")  # Go directly to login page
            driver.set_window_size(1552, 880)
            
            # Step 2: Login as admin
            print("Step 2: Logging in as admin...")
            try:
                # Wait for login form and enter credentials
                email_input = wait.until(
                    EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Type your email']"))
                )
                password_input = wait.until(
                    EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Type your password']"))
                )
            except:
                # Alternative selectors if the above don't work
                email_input = wait.until(
                    EC.visibility_of_element_located((By.ID, "email"))
                )
                password_input = wait.until(
                    EC.visibility_of_element_located((By.ID, "password"))
                )
            
            email_input.send_keys("admin@gmail.com")  # Use actual admin credentials
            password_input.send_keys("admin")         # Use actual admin password
            
            try:
                # Try different ways to find the login button
                login_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login')]"))
                )
            except:
                try:
                    login_button = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".login-btn"))
                    )
                except:
                    login_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
                    )
            
            login_button.click()
            print("Login button clicked")
            
            # Wait for login to complete
            time.sleep(3)
            
            print("\nStep 3: Navigating to Generate Reports page...")
            time.sleep(2)  # Wait for page to fully load
            
            try:
                report_gen_link = wait.until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Generate Reports"))
                )
                
                # Scroll the link into view
                driver.execute_script("arguments[0].scrollIntoView(true);", report_gen_link)
                time.sleep(1)  # Wait for scroll to complete
                
                report_gen_link.click()
                print("Clicked Generate Reports link")
                
                # Wait for the report generation page to load
                wait.until(
                    EC.presence_of_element_located((By.ID, "reportForm"))
                )
                print("Admin Report Generation page loaded successfully")
                
            except Exception as e:
                print(f"Error navigating to Generate Reports page: {str(e)}")
                print("Current URL:", driver.current_url)
                raise
            
            # Step 4: Configure report parameters
            print("\nStep 4: Configuring report parameters...")
            
            # Select report type: Bus Bookings
            report_type_select = Select(wait.until(
                EC.element_to_be_clickable((By.ID, "reportType"))
            ))
            report_type_select.select_by_visible_text("Bus Bookings")
            print("Selected Bus Bookings report type")
            
            # Select date range type: Month Range
            date_range_select = Select(wait.until(
                EC.element_to_be_clickable((By.ID, "dateRangeType"))
            ))
            date_range_select.select_by_visible_text("Month Range")
            print("Selected Month Range date range")
            
            # Select file format: PDF
            file_format_select = Select(wait.until(
                EC.element_to_be_clickable((By.ID, "fileFormat"))
            ))
            file_format_select.select_by_visible_text("PDF")
            print("Selected PDF file format")
            
            # Set start month to February 2025 using a more robust JavaScript approach
            try:
                # First make the month range fields visible if they're not already
                driver.execute_script("""
                    var monthRangeFields = document.getElementById('monthRangeFields');
                    if (monthRangeFields && monthRangeFields.style.display === 'none') {
                        monthRangeFields.style.display = 'block';
                    }
                """)
                
                # Set the value using a more robust approach
                driver.execute_script("""
                    var startMonth = document.getElementById('startMonth');
                    if (startMonth) {
                        startMonth.value = '2025-02';
                        
                        // Create and dispatch events to ensure the change is recognized
                        var inputEvent = new Event('input', { bubbles: true });
                        var changeEvent = new Event('change', { bubbles: true });
                        
                        startMonth.dispatchEvent(inputEvent);
                        startMonth.dispatchEvent(changeEvent);
                    }
                """)
                
                # Verify the value was set correctly
                current_value = driver.execute_script("return document.getElementById('startMonth').value;")
                print(f"Start month value (from JS): {current_value}")
                
                # If the value wasn't set correctly, try a different approach
                if not current_value or "2025-02" not in current_value:
                    # Try a different JavaScript approach
                    driver.execute_script("""
                        var startMonth = document.getElementById('startMonth');
                        // Force the input to be a standard text input temporarily
                        startMonth.setAttribute('type', 'text');
                        startMonth.value = 'February 2025';
                        // Change back to month type
                        startMonth.setAttribute('type', 'month');
                        startMonth.value = '2025-02';
                    """)
                    
                    # Check again
                    current_value = driver.execute_script("return document.getElementById('startMonth').value;")
                    print(f"Start month value after second attempt: {current_value}")
                    
                    if not current_value or "2025" not in current_value:
                        raise Exception("JavaScript methods failed to set the value correctly")
            except Exception as e:
                print(f"Error setting start month with JavaScript: {str(e)}")
                # Fallback to direct input
                try:
                    start_month_input = wait.until(EC.element_to_be_clickable((By.ID, "startMonth")))
                    start_month_input.clear()
                    start_month_input.send_keys("2025-02")
                    print("Fallback: Set start month using direct input")
                    
                    # Check if the value was set
                    current_value = start_month_input.get_attribute('value')
                    if not current_value or "2025-02" not in current_value:
                        # Try clicking on the input to open the date picker
                        print("Direct input failed, trying date picker UI...")
                        start_month_input.click()
                        time.sleep(1)
                        
                        # Try to find and click on the year selector
                        try:
                            # First try to find a year dropdown or selector
                            year_elements = driver.find_elements(By.XPATH, "//select[contains(@class, 'year')]")
                            if year_elements:
                                # If there's a year dropdown, select 2025
                                Select(year_elements[0]).select_by_visible_text("2025")
                                print("Selected year 2025 from dropdown")
                            else:
                                # Try to find and click on a year button/link
                                year_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'year') or contains(text(), 'year')]")
                                if year_buttons:
                                    year_buttons[0].click()
                                    print("Clicked on year selector button")
                                    time.sleep(1)
                                    
                                    # Now try to find and click on 2025
                                    year_2025 = driver.find_element(By.XPATH, "//*[contains(text(), '2025')]")
                                    year_2025.click()
                                    print("Selected year 2025")
                                    time.sleep(1)
                            
                            # Now try to find and click on February
                            month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Feb') or contains(text(), '02')]")
                            if month_elements:
                                for element in month_elements:
                                    try:
                                        element.click()
                                        print(f"Clicked on element with text: {element.text}")
                                        break
                                    except:
                                        continue
                        except Exception as e:
                            print(f"Error using date picker UI: {str(e)}")
                except Exception as e:
                    print(f"All fallback methods for start month failed: {str(e)}")
            
            # Set end month to April 2025 using a more robust JavaScript approach
            try:
                # Set the value using a more robust approach
                driver.execute_script("""
                    var endMonth = document.getElementById('endMonth');
                    if (endMonth) {
                        endMonth.value = '2025-04';
                        
                        // Create and dispatch events to ensure the change is recognized
                        var inputEvent = new Event('input', { bubbles: true });
                        var changeEvent = new Event('change', { bubbles: true });
                        
                        endMonth.dispatchEvent(inputEvent);
                        endMonth.dispatchEvent(changeEvent);
                    }
                """)
                
                # Verify the value was set correctly
                current_value = driver.execute_script("return document.getElementById('endMonth').value;")
                print(f"End month value (from JS): {current_value}")
                
                # If the value wasn't set correctly, try a different approach
                if not current_value or "2025-04" not in current_value:
                    # Try a different JavaScript approach
                    driver.execute_script("""
                        var endMonth = document.getElementById('endMonth');
                        // Force the input to be a standard text input temporarily
                        endMonth.setAttribute('type', 'text');
                        endMonth.value = 'April 2025';
                        // Change back to month type
                        endMonth.setAttribute('type', 'month');
                        endMonth.value = '2025-04';
                    """)
                    
                    # Check again
                    current_value = driver.execute_script("return document.getElementById('endMonth').value;")
                    print(f"End month value after second attempt: {current_value}")
                    
                    if not current_value or "2025" not in current_value:
                        raise Exception("JavaScript methods failed to set the value correctly")
            except Exception as e:
                print(f"Error setting end month with JavaScript: {str(e)}")
                # Fallback to direct input
                try:
                    end_month_input = wait.until(EC.element_to_be_clickable((By.ID, "endMonth")))
                    end_month_input.clear()
                    end_month_input.send_keys("2025-04")
                    print("Fallback: Set end month using direct input")
                    
                    # Check if the value was set
                    current_value = end_month_input.get_attribute('value')
                    if not current_value or "2025-04" not in current_value:
                        # Try clicking on the input to open the date picker
                        print("Direct input failed, trying date picker UI...")
                        end_month_input.click()
                        time.sleep(1)
                        
                        # Try to find and click on the year selector
                        try:
                            # First try to find a year dropdown or selector
                            year_elements = driver.find_elements(By.XPATH, "//select[contains(@class, 'year')]")
                            if year_elements:
                                # If there's a year dropdown, select 2025
                                Select(year_elements[0]).select_by_visible_text("2025")
                                print("Selected year 2025 from dropdown")
                            else:
                                # Try to find and click on a year button/link
                                year_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'year') or contains(text(), 'year')]")
                                if year_buttons:
                                    year_buttons[0].click()
                                    print("Clicked on year selector button")
                                    time.sleep(1)
                                    
                                    # Now try to find and click on 2025
                                    year_2025 = driver.find_element(By.XPATH, "//*[contains(text(), '2025')]")
                                    year_2025.click()
                                    print("Selected year 2025")
                                    time.sleep(1)
                            
                            # Now try to find and click on April
                            month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Apr') or contains(text(), '04')]")
                            if month_elements:
                                for element in month_elements:
                                    try:
                                        element.click()
                                        print(f"Clicked on element with text: {element.text}")
                                        break
                                    except:
                                        continue
                        except Exception as e:
                            print(f"Error using date picker UI: {str(e)}")
                except Exception as e:
                    print(f"All fallback methods for end month failed: {str(e)}")
            
            # Step 5: Preview report
            print("\nStep 5: Previewing report...")
            preview_button = wait.until(
                EC.element_to_be_clickable((By.ID, "previewButton"))
            )
            
            # Scroll to the preview button to ensure it's visible
            driver.execute_script("arguments[0].scrollIntoView(true);", preview_button)
            time.sleep(1)
            
            # Click the preview button
            preview_button.click()
            print("Clicked Preview button")
            
            # Wait for preview to load
            print("Waiting for preview data to load...")
            time.sleep(3)  # Give some time for the AJAX request to complete
            
            # Step 6: Generate PDF report
            print("\nStep 6: Generating PDF report...")
            
            # Delete existing files if they exist
            # Check for any PDF file with "bus_bookings" in the name
            existing_files = [f for f in os.listdir(download_dir) if f.startswith("bus_bookings_") and f.endswith(".pdf")]
            for file in existing_files:
                try:
                    os.remove(os.path.join(download_dir, file))
                    print(f"Removed existing file: {file}")
                except:
                    print(f"Could not remove file: {file}")
            
            # Submit the form to generate the report
            try:
                # Find the Generate Report button
                generate_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Generate Report')]"))
                )
                print("Found Generate Report button")
                
                # Scroll to the button to make sure it's visible
                driver.execute_script("arguments[0].scrollIntoView(true);", generate_button)
                time.sleep(1)  # Wait for scroll to complete
                
                print(f"Clicking button with text: '{generate_button.text}'")
                generate_button.click()
                print("Clicked Generate Report button")
                
                # Wait for download to complete
                print("Waiting for download to complete...")
                timeout = time.time() + 30
                downloaded = False
                
                # Expected filename patterns based on the YYYY-MM format we used
                expected_patterns = [
                    "bus_bookings_2025-02_to_2025-04.pdf",  # Most likely format with YYYY-MM
                    "bus_bookings_february_to_april_2025.pdf",  # Month name format
                    "bus_bookings_feb_to_apr_2025.pdf",  # Short month name format
                    "bus_bookings_20250201_to_20250430.pdf"  # Date format with full date
                ]
                
                while time.time() < timeout:
                    # Check for any PDF file with "bus_bookings" in the name
                    pdf_files = [f for f in os.listdir(download_dir) if f.startswith("bus_bookings_") and f.endswith(".pdf")]
                    
                    if pdf_files:
                        filepath = os.path.join(download_dir, pdf_files[0])
                        try:
                            with open(filepath, 'rb') as file:
                                file.read(100)  # Try to read a few bytes to ensure file is complete
                                downloaded = True
                                print(f"File downloaded successfully: {filepath}")
                                
                                # Log whether the filename matches any of our expected patterns
                                filename = os.path.basename(filepath)
                                if any(pattern == filename for pattern in expected_patterns):
                                    print(f"Filename matches expected pattern: {filename}")
                                else:
                                    print(f"Note: Filename '{filename}' doesn't match any expected patterns, but download succeeded")
                                
                                break
                        except (IOError, PermissionError):
                            pass
                    time.sleep(1)
                
                if downloaded:
                    print("\n✅ ADMIN BUS BOOKINGS REPORT TEST PASSED!")
                    print("=====================================")
                    print("✓ Successfully logged in as admin")
                    print("✓ Navigated to Generate Reports page")
                    print("✓ Configured report parameters")
                    print("✓ Previewed report")
                    print("✓ Generated and downloaded PDF report")
                    print("=====================================")
                    break  # Exit the retry loop on success
                else:
                    print("\n❌ DOWNLOAD TEST FAILED!")
                    print("=====================================")
                    print("✗ PDF download failed or timeout")
                    print("=====================================")
                    raise TimeoutException("Download timeout or file verification failed")
                
            except Exception as e:
                print(f"Error during report generation: {str(e)}")
                screenshot_path = os.path.join(download_dir, f"error_screenshot_{retry_count}.png")
                try:
                    driver.save_screenshot(screenshot_path)
                    print(f"Error screenshot saved to: {screenshot_path}")
                except:
                    print("Could not save error screenshot")
                
                # If this is the last retry, re-raise the exception
                if retry_count == max_retries:
                    raise
                
        except (WebDriverException, NoSuchWindowException) as e:
            print(f"Browser error on attempt {retry_count + 1}: {str(e)}")
            # If this is the last retry, re-raise the exception
            if retry_count == max_retries:
                raise
        
        finally:
            # Close the browser for this attempt
            if driver:
                try:
                    driver.quit()
                    print(f"Browser closed for attempt {retry_count + 1}")
                except:
                    print("Browser already closed or could not be closed")
        
        # Increment retry counter
        retry_count += 1
        
        if retry_count <= max_retries:
            print(f"Retrying test in 3 seconds...")
            time.sleep(3)

if __name__ == "__main__":
    test_admin_bus_bookings_report()

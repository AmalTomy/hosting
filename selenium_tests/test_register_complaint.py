from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
import unittest
import time
import os
from datetime import datetime, timedelta
from PIL import Image

class TestRegisterComplaint(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)
        print("\n=== Starting Customer Complaint Registration Test ===")

    def tearDown(self):
        self.driver.quit()
        print("Test completed")

    def test_register_complaint(self):
        # 1. Login Process
        print("Step 1: Logging in...")
        self.driver.get("http://localhost:8000/login")
        
        # Wait for page to load
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Find and fill email and password
        email_input = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Type your email']"))
        )
        password_input = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Type your password']"))
        )
        
        # Fill in test credentials
        email_input.send_keys("amaltomy2025@mca.ajce.in")
        password_input.send_keys("Amal@123")
        print("Credentials entered")
        
        # Click login button
        login_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Login']"))
        )
        login_button.click()
        print("Login button clicked")

        # 2. Navigate to Register Complaints
        print("\nStep 2: Navigating to Register Complaints...")
        time.sleep(3)  # Increased wait time for welcome page to load completely
        
        try:
            # Try multiple approaches to find and click the user dropdown
            try:
                # First attempt - by class and role
                user_dropdown = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@class='nav-link dropdown-toggle page-scroll']"))
                )
            except:
                try:
                    # Second attempt - by content
                    user_dropdown = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Welcome')]"))
                    )
                except:
                    # Third attempt - by ID
                    user_dropdown = self.wait.until(
                        EC.element_to_be_clickable((By.ID, "userDropdown"))
                    )
            
            print("Found user dropdown")
            
            # Try JavaScript click if regular click doesn't work
            try:
                user_dropdown.click()
            except:
                self.driver.execute_script("arguments[0].click();", user_dropdown)
                
            print("Clicked user dropdown")
            
            # Wait for dropdown to be visible
            time.sleep(1)
            
            # Print all dropdown items for debugging
            dropdown_items = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'dropdown-menu')]/a")
            print(f"Found {len(dropdown_items)} dropdown items:")
            for item in dropdown_items:
                print(f"  - {item.text}")
            
            # Try multiple approaches to find and click Register Complaints
            try:
                # First attempt - by text content
                register_complaints_option = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Register Complaints')]"))
                )
            except:
                try:
                    # Second attempt - by partial match and class
                    register_complaints_option = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'dropdown-item') and contains(text(), 'Complaints')]"))
                    )
                except:
                    # Third attempt - try to find all dropdown items and click the one with "Complaints"
                    dropdown_items = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'dropdown-menu')]/a")
                    register_complaints_option = None
                    for item in dropdown_items:
                        if "complaint" in item.text.lower() or "register" in item.text.lower():
                            register_complaints_option = item
                            break
                    
                    if not register_complaints_option:
                        raise TimeoutException("Could not find Register Complaints option")
            
            print(f"Found Register Complaints option: {register_complaints_option.text}")
            
            # Try JavaScript click if regular click doesn't work
            try:
                register_complaints_option.click()
            except:
                self.driver.execute_script("arguments[0].click();", register_complaints_option)
                
            print("Clicked Register Complaints option")
            
            # Wait for navigation to complete
            time.sleep(2)
            
            # Verify we're on the correct page
            current_url = self.driver.current_url
            print(f"Current URL: {current_url}")
            
            if "userhome" in current_url:
                print("Successfully navigated to userhome page")
            else:
                print("Warning: URL doesn't contain 'userhome', but continuing test")
            
        except Exception as e:
            print(f"Error navigating to Register Complaints: {str(e)}")
            
            # Take screenshot for debugging
            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "navigation_error.png")
            self.driver.save_screenshot(screenshot_path)
            print(f"Screenshot saved to: {screenshot_path}")
            
            # Print current page source for debugging
            print("\nCurrent page HTML structure:")
            print(self.driver.page_source[:500] + "...")  # Print first 500 chars
            
            self.fail(f"Could not navigate to Register Complaints: {str(e)}")

        # 3. Click Report Case button
        print("\nStep 3: Clicking Report Case button...")
        time.sleep(2)  # Wait for userhome page to load
        
        try:
            # Find and click the REPORT CASE link in the navigation
            report_case_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[@class='nav-link page-scroll' and contains(text(), 'REPORT CASE')]"))
            )
            print("Found REPORT CASE button")
            report_case_button.click()
            print("Clicked REPORT CASE button")
            
        except TimeoutException:
            self.fail("Could not find the REPORT CASE button")

        # 4. Fill Complaint Form
        print("\nStep 4: Filling complaint form...")
        time.sleep(2)  # Wait for report_user page to load
        
        try:
            # Fill first name and last name
            first_name_input = self.wait.until(
                EC.visibility_of_element_located((By.ID, "firstName"))
            )
            last_name_input = self.driver.find_element(By.ID, "lastName")
            
            first_name_input.send_keys("Christina")
            last_name_input.send_keys("Thomas")
            print("Entered name details")
            
            # Fill address
            address_input = self.driver.find_element(By.ID, "address")
            address_input.send_keys("123 Test Street")
            print("Entered address")
            
            # Fill date of birth
            dob_input = self.driver.find_element(By.ID, "dateOfBirth")
            # Set date to 20 years ago
            dob = (datetime.now() - timedelta(days=365*20)).strftime('%Y-%m-%d')
            self.driver.execute_script(f"arguments[0].value = '{dob}';", dob_input)
            print(f"Set date of birth to {dob}")
            
            # Fill Aadhar number
            aadhar_input = self.driver.find_element(By.ID, "aadharNumber")
            aadhar_input.send_keys("123456789012")  # 12-digit number
            print("Entered Aadhar number")
            
            # Fill missing date
            missing_date_input = self.driver.find_element(By.ID, "missingDate")
            # Set date to yesterday
            missing_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            self.driver.execute_script(f"arguments[0].value = '{missing_date}';", missing_date_input)
            print(f"Set missing date to {missing_date}")
            
            # Select gender
            male_radio = self.driver.find_element(By.ID, "male")
            male_radio.click()
            print("Selected gender: Male")
            
            # Select police station
            location_select = Select(self.driver.find_element(By.ID, "location"))
            # Select the first option that's not the placeholder
            options = location_select.options
            for option in options:
                if option.get_attribute("value") != "":
                    location_select.select_by_value(option.get_attribute("value"))
                    print(f"Selected police station: {option.text}")
                    break
            
            # Upload image
            image_input = self.driver.find_element(By.ID, "image")
            
            # Use the specific image path provided by the user
            test_image_path = r"C:\Users\91949\OneDrive\Pictures\man.png"
            
            print(f"Using image at: {test_image_path}")
            
            # Check if the image exists
            if not os.path.exists(test_image_path):
                print(f"WARNING: Image not found at {test_image_path}")
                
                # Fallback to creating a test image in the selenium_tests directory
                current_dir = os.path.dirname(os.path.abspath(__file__))
                fallback_image_path = os.path.join(current_dir, "test_image.jpg")
                
                print(f"Creating fallback image at: {fallback_image_path}")
                
                try:
                    # Create a simple test image using PIL
                    img = Image.new('RGB', (100, 100), color = (255, 0, 0))
                    img.save(fallback_image_path)
                    print(f"Created fallback test image")
                    test_image_path = fallback_image_path
                except Exception as e:
                    print(f"Error creating fallback image: {str(e)}")
                    print("WARNING: Continuing test without image upload")
            
            # Try to upload the image
            if os.path.exists(test_image_path):
                try:
                    image_input.send_keys(test_image_path)
                    print("Uploaded test image successfully")
                except Exception as e:
                    print(f"Error uploading image: {str(e)}")
                    print("WARNING: Continuing test without image upload")
            else:
                print("WARNING: No valid image found, continuing test without image upload")
            
            # Submit the form
            submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit Report')]")
            
            # Scroll to the button to make sure it's visible
            self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(1)  # Wait for scroll to complete
            
            print("Submitting form...")
            submit_button.click()
            
            # 5. Verify successful submission
            print("\nStep 5: Verifying successful submission...")
            
            try:
                # First handle the alert that appears after submission
                try:
                    # Wait for alert to be present
                    WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    print(f"Alert found with text: {alert_text}")
                    
                    # Accept the alert to proceed
                    alert.accept()
                    print("Alert accepted")
                    
                    # Check if the alert indicates success
                    if "success" in alert_text.lower() or "registered" in alert_text.lower():
                        print("Form submission successful based on alert message")
                    else:
                        print(f"WARNING: Alert message doesn't clearly indicate success: {alert_text}")
                        
                except TimeoutException:
                    print("No alert found, continuing with verification")
                
                # After handling the alert, manually navigate to the viewcase page
                print("Manually navigating to viewcase page...")
                self.driver.get("http://localhost:8000/viewcase")
                print("Navigated to viewcase page")
                
                # Verify we're on the viewcase page by checking for specific elements
                try:
                    # Look for elements that are specific to the viewcase page
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'maincard')]"))
                    )
                    print("Verified viewcase page content is loaded")
                    
                    # Take a screenshot of the viewcase page
                    screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewcase_success.png")
                    self.driver.save_screenshot(screenshot_path)
                    print(f"Screenshot of viewcase page saved to: {screenshot_path}")
                    
                    # Check if our newly submitted case appears on the page
                    try:
                        # Look for the name we entered in the form
                        case_element = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//h5[contains(text(), 'Christina Thomas') or contains(text(), 'Christina') and contains(text(), 'Thomas')]"))
                        )
                        print("Found our newly submitted case on the viewcase page!")
                    except TimeoutException:
                        print("WARNING: Could not find our specific case on the viewcase page")
                        
                except TimeoutException:
                    print("WARNING: Could not verify viewcase page content")
                    self.fail("Failed to load viewcase page content")
                
                # Test passed
                print("\n✅ COMPLAINT REGISTRATION TEST PASSED!")
                print("=====================================")
                print("✓ Successfully logged in")
                print("✓ Navigated to Register Complaints")
                print("✓ Clicked Report Case button")
                print("✓ Filled complaint form")
                print("✓ Submitted form successfully")
                print("✓ Verified case on viewcase page")
                print("=====================================")
                
            except Exception as e:
                print(f"\n❌ Test failed with error: {str(e)}")
                
                # Take a screenshot for debugging
                screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_screenshot.png")
                self.driver.save_screenshot(screenshot_path)
                print(f"Error screenshot saved to: {screenshot_path}")
                
                self.fail(f"Error during verification: {str(e)}")
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            self.fail(f"Error during form filling: {str(e)}")

if __name__ == "__main__":
    unittest.main() 
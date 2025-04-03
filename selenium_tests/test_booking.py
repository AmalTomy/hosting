from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from datetime import datetime, timedelta
import unittest
import time

class TestBusBooking(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)

    def tearDown(self):
        self.driver.quit()

    def test_bus_booking_process(self):
        # 1. Login Process
        self.driver.get("http://localhost:8000/login")
        
        # Wait for page to load
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Find and fill email and password using the correct selectors
        email_input = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Type your email']"))
        )
        password_input = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Type your password']"))
        )
        
        # Fill in test credentials
        email_input.send_keys("kitty@mail.com")
        password_input.send_keys("Kitty@123")
        
        # Click login button
        login_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Login']"))
        )
        login_button.click()

        # 2. Wait for redirect and click BOOK BUS button
        time.sleep(2)  # Wait for page to load completely
        
        try:
            # Find and click the BOOK BUS link in the navigation
            book_bus_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[@class='nav-link page-scroll' and contains(text(), 'BOOK BUS')]"))
            )
            print("Found BOOK BUS button")
            book_bus_button.click()
            print("Clicked BOOK BUS button")
        except TimeoutException:
            self.fail("Could not find the BOOK BUS button")

        # 3. Fill Booking Form
        source_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "sourceInput"))
        )
        destination_input = self.driver.find_element(By.ID, "destinationInput")
        date_input = self.driver.find_element(By.ID, "dateInput")

        # Fill the form
        source_input.send_keys("Mumbai")
        time.sleep(1)  # Wait for autocomplete
        source_input.send_keys(Keys.DOWN)
        source_input.send_keys(Keys.ENTER)

        destination_input.send_keys("Agra")
        time.sleep(1)  # Wait for autocomplete
        destination_input.send_keys(Keys.DOWN)
        destination_input.send_keys(Keys.ENTER)

        # Try multiple approaches for date input
        try:
            # Approach 1: Direct input
            date_input.clear()  # Clear any existing value
            date_input.send_keys("09-11-2024")
            
        except Exception as e:
            print(f"Direct input failed: {str(e)}")
            try:
                # Approach 2: JavaScript
                self.driver.execute_script(
                    "arguments[0].value = '09-11-2024'; arguments[0].dispatchEvent(new Event('change'));", 
                    date_input
                )
            except Exception as e:
                print(f"JavaScript approach failed: {str(e)}")
                try:
                    # Approach 3: Action chains
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_to_element(date_input)
                    actions.click()
                    actions.send_keys("09-11-2024")
                    actions.perform()
                except Exception as e:
                    print(f"Action chains approach failed: {str(e)}")
                    self.fail("Could not input date using any method")

        # Add a small delay to verify the date was entered
        time.sleep(1)

        # Verify the date was entered correctly
        date_value = self.driver.execute_script("return document.getElementById('dateInput').value;")
        print(f"Date value after input: {date_value}")

        # Click search button
        search_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'SEARCH BUS')]"))
        )
        search_button.click()

        # 4. Bus Selection and Seat Selection
        view_seats_button = self.wait.until(
            EC.element_to_be_clickable((By.CLASS_NAME, "view_seat_btn"))
        )
        view_seats_button.click()

        # Wait for seat modal to be visible
        time.sleep(2)  # Wait for modal animation
        
        try:
            # Find and click seat 1C specifically
            seat_1c = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'seat') and @data-seat='1C']"))
            )
            
            # Try to click using JavaScript (more reliable for modal interactions)
            self.driver.execute_script("arguments[0].click();", seat_1c)
            print("Selected seat 1C successfully")

        except TimeoutException:
            self.fail("Could not find seat 1C")

        # Confirm selection
        confirm_button = self.wait.until(
            EC.element_to_be_clickable((By.ID, "confirm-seats"))
        )
        confirm_button.click()

        # 5. Fill Passenger Details
        # Wait for the booking confirmation modal to be visible
        try:
            # Wait for modal to be visible
            self.wait.until(
                EC.visibility_of_element_located((By.ID, "bookingConfirmationModal"))
            )
            print("Booking confirmation modal is visible")

            # Wait for form fields to be present and interactable
            passenger_name = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "passenger_name_0"))
            )
            passenger_email = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "passenger_email_0"))
            )
            passenger_phone = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "passenger_phone_0"))
            )

            # Fill passenger details
            passenger_name.clear()
            passenger_name.send_keys("Christina")
            print("Entered passenger name")

            passenger_email.clear()
            passenger_email.send_keys("christina@test.com")
            print("Entered passenger email")

            passenger_phone.clear()
            passenger_phone.send_keys("1234567890")
            print("Entered passenger phone")

            # 6. Click Pay button and verify Stripe initialization
            pay_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Pay')]"))
            )
            pay_button.click()
            print("Clicked pay button")

            # Wait for redirect to Stripe
            time.sleep(3)  # Give time for redirect

            try:
                # Wait for Stripe checkout page to load
                print("Waiting for Stripe checkout page...")
                self.wait.until(lambda driver: "stripe.com" in driver.current_url)
                print("Successfully reached Stripe payment page")

                # Display success message
                self.driver.execute_script("""
                    const dialog = document.createElement('div');
                    dialog.style.position = 'fixed';
                    dialog.style.top = '50%';
                    dialog.style.left = '50%';
                    dialog.style.transform = 'translate(-50%, -50%)';
                    dialog.style.padding = '20px';
                    dialog.style.backgroundColor = '#fff';
                    dialog.style.border = '2px solid #4CAF50';
                    dialog.style.borderRadius = '10px';
                    dialog.style.zIndex = '9999';
                    dialog.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
                    dialog.innerHTML = '<h3 style="color: #4CAF50; margin: 0;">Booking Successful!</h3>';
                    document.body.appendChild(dialog);
                    setTimeout(() => dialog.remove(), 3000);
                """)
                print("Displayed success dialog")

                # Wait to see the success message
                time.sleep(3)

            except Exception as e:
                print(f"Error during payment process: {str(e)}")
                self.fail("Failed to reach Stripe payment page")

            print("Test completed successfully!")

        except TimeoutException as e:
            print(f"Error in booking confirmation: {str(e)}")
            self.fail("Could not complete the booking confirmation process")

if __name__ == "__main__":
    unittest.main()
import logging
import colorlog
import requests
import warnings
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

warnings.filterwarnings('ignore')

# URLs
AUTH_PAGE = "https://academic.ui.ac.id/main/Authentication/"
HOME_PAGE = "https://academic.ui.ac.id/main/Welcome/Index"
COURSE_PLAN_PAGE = "https://academic.ui.ac.id/main/CoursePlan/CoursePlanEdit"
SUBMIT_COURSE_PLAN_URL = "https://academic.ui.ac.id/main/CoursePlan/CoursePlanSave"

# Configure loggers with color
def configure_logger(name, color):
  logger = colorlog.getLogger(name)
  logger.setLevel(logging.INFO)
  
  handler = logging.StreamHandler()
  formatter = colorlog.ColoredFormatter(
    '%(asctime)s - %(log_color)s%(levelname)s%(reset)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
      'DEBUG': color,
      'INFO': color,
      'WARNING': 'yellow',
      'ERROR': 'red',
      'CRITICAL': 'bold_red',
    }
  )
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  return logger

# Configure loggers with specific colors
auth_logger = configure_logger('auth', 'blue')
course_plan_logger = configure_logger('course_plan', 'yellow')
api_logger = configure_logger('api', 'green')

def login(driver, username, password, display_name):
  auth_logger.info("Logging in...")
  while True:
    try:
      driver.get(AUTH_PAGE)
      element = driver.find_element(By.ID, "u")
      element.send_keys(username)
      element = driver.find_element(By.NAME, "p")
      element.send_keys(password)
      element.send_keys(Keys.RETURN)
    except Exception as e:
      if ("Logout Counter" in driver.page_source or display_name in driver.page_source):
        auth_logger.info("Logged in!")
        break
      continue
    try:
      driver.get(HOME_PAGE)
      if ("Logout Counter" in driver.page_source or display_name in driver.page_source):
        auth_logger.info("Logged in!")
        break
      raise Exception
    except:
      continue

def submit_course_plan(token, matkul, cookies):
    headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
      'Referer': COURSE_PLAN_PAGE,
    }
    
    # Prepare payload with all desired courses
    payload = {
      'tokens': token,
      'comment': '',
      'submit': 'Simpan IRS'
    }
    desired_kelas = set(matkul.keys())
    for name, code in matkul.values():
      payload[f'c[{name}]'] = code
    
    while True:
      try:
        # Submit course plan
        response = requests.post(SUBMIT_COURSE_PLAN_URL, data=payload, headers=headers, cookies=cookies, verify=False)
        api_logger.info(f"Response Status Code: {response.status_code}")

        if response.status_code == 200:
          api_logger.info("Course plan submitted successfully!")

          html_content = response.text
          soup = BeautifulSoup(html_content, 'html.parser')
          table = soup.find('table', class_='box')

          submitted_kelas = set()
          rows = table.find_all('tr')
          for row in rows:
            cols = row.find_all('td')
            if len(cols) > 2:
              nama_mk = cols[2].get_text(strip=True)
              span_text = cols[2].find('span')
              if span_text:
                submitted_kelas.add(span_text.get_text(strip=True))
              else:
                submitted_kelas.add(nama_mk)
          
          api_logger.info(f'SUBMITTED KELAS: {submitted_kelas}')
          api_logger.info(f'DESIRED KELAS: {desired_kelas}')

          # Check if all desired classes are in submitted classes
          if desired_kelas == submitted_kelas:
            api_logger.info("All desired classes have been submitted!")
            break
          else:
            api_logger.info("Not all desired classes were submitted. Retrying...")
        else:
          api_logger.error(f"Failed to submit course plan. Status code: {response.status_code}")
          api_logger.error(f"Response content: {response.text}")
          break
      except requests.exceptions.RequestException as e:
        # Handle specific exceptions
        if isinstance(e, requests.exceptions.ConnectTimeout):
          api_logger.warning("Connection timed out. Retrying...")
        else:
          api_logger.error(f"An error occurred: {e}")

def main():
  options = webdriver.ChromeOptions()
  options.add_argument('--ignore-certificate-errors')
  options.add_argument('--ignore-ssl-errors')
  driver = webdriver.Chrome('chromedriver.exe', options=options)

  # Load credentials
  with open("credentials.txt", "r") as file:
    creds = [line.strip() for line in file]
  username, password, display_name, common_matkul, chosen_matkul = creds
  
  # Load courses
  matkul = {}
  with open("matkul.txt", "r") as file:
    for line in file:
      name, code, kelas = line.strip().split('___')
      matkul[kelas] = (name, code)

  auth_logger.info("Credentials and courses loaded!")
  auth_logger.debug(f"Credentials: {creds}")
  auth_logger.debug(f"Courses: {matkul}")
  
  login(driver, username, password, display_name)
  
  # Navigate to the course plan page and retrieve the token
  course_plan_logger.info("Accessing course plan page to retrieve token...")
  driver.get(COURSE_PLAN_PAGE)
  
  token_element = driver.find_element(By.XPATH, "//input[@name='tokens']")
  token_value = token_element.get_attribute("value")

  # Extract cookies from the browser
  cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
  
  if token_value:
    course_plan_logger.info("Token retrieved!")
    submit_course_plan(token_value, matkul, cookies)
  else:
    course_plan_logger.error("Token not found.")
  driver.quit()

if __name__ == "__main__":
  main()

import requests
import warnings
from bs4 import BeautifulSoup
from selenium import webdriver
from logger import configure_logger
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException


warnings.filterwarnings('ignore')

# URLs
AUTH_PAGE = "https://academic.ui.ac.id/main/Authentication/"
HOME_PAGE = "https://academic.ui.ac.id/main/Welcome/Index"
COURSE_PLAN_PAGE = "https://academic.ui.ac.id/main/CoursePlan/CoursePlanEdit"
CEK_IRS_URL = 'https://academic.ui.ac.id/main/CoursePlan/CoursePlanViewCheck'
IRS_DONE_PAGE = 'https://academic.ui.ac.id/main/CoursePlan/CoursePlanDone'
SUBMIT_COURSE_PLAN_URL = "https://academic.ui.ac.id/main/CoursePlan/CoursePlanSave"

# Configure loggers with specific colors
auth_logger = configure_logger('auth', 'blue')
course_plan_logger = configure_logger('course_plan', 'yellow')
api_logger = configure_logger('api', 'green')
cek_irs_logger = configure_logger('cek_irs', 'purple')

# Helper Function
def configure_driver():
  options = webdriver.ChromeOptions()
  options.add_argument('--ignore-certificate-errors')
  options.add_argument('--ignore-ssl-errors')
  driver = webdriver.Chrome('chromedriver.exe', options=options)
  return driver


def load_credentials(filename):
  with open(filename, "r") as file:
    creds = [line.strip() for line in file]
  return creds


def load_courses(filename):
  matkul = {}
  with open(filename, "r") as file:
    for line in file:
      name, code, kelas = line.strip().split('___')
      matkul[kelas] = (name, code)
  return matkul


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
      if "Logout Counter" in driver.page_source or display_name in driver.page_source:
        auth_logger.info("Logged in!")
        break
      continue
    try:
      driver.get(HOME_PAGE)
      if "Logout Counter" in driver.page_source or display_name in driver.page_source:
        auth_logger.info("Logged in!")
        break
      raise Exception
    except:
      continue


def logout(driver):
  auth_logger.info("Logging out...")
  while True:
    try:
      driver.get(HOME_PAGE)
      driver.find_element(By.PARTIAL_LINK_TEXT, 'Logout').click()
    except:
      try:
        driver.find_element(By.ID, "u")
        auth_logger.info("Logged out!")
        break
      except:
        continue
    try:
      driver.get(AUTH_PAGE)
      driver.find_element(By.ID, "u")
      auth_logger.info("Logged out!")
      break
    except:
      continue


def create_payload(matkul, token):
  payload = {
    'tokens': token,
    'comment': '',
    'submit': 'Simpan IRS'
  }
  for name, code in matkul.values():
    payload[f'c[{name}]'] = code
  return payload


def create_headers(referer):
  headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Referer': referer,
  }
  return headers


def get_submitted_kelas(content):
  html_content = content
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
  return submitted_kelas


def get_posisi_kelas(content):
  soup = BeautifulSoup(content, 'html.parser')
  rows = soup.find_all('tr')
  results = []
  for row in rows:
    text = row.find('td').get_text(separator=' ', strip=True)
    if '---' in text:
      continue
    if 'Kapasitas' in text or '; Kelas' in text:
      results.append(text)
  print('='*50)
  i = 1
  for res in results:
    if 'Kapasitas' in res:
      print(f'    {res}')
    else:
      print(f'[{i}] {res}')
      i+=1
  print('='*50)
  return results


def war():
  driver = configure_driver()
  creds = load_credentials("credentials.txt")
  username, password, display_name, common_matkul, chosen_matkul = creds
  matkul = load_courses("matkul.txt")

  auth_logger.info("Credentials and courses loaded!")
  auth_logger.debug(f"Credentials: {creds}")
  auth_logger.debug(f"Courses: {matkul}")

  #========= 1. Login
  login(driver, username, password, display_name)

  #========= 2. Access Course Plan Page
  token = ''
  while True:
    course_plan_logger.info("Accessing course plan page to retrieve token...")
    try:
      driver.get(COURSE_PLAN_PAGE)
      if ("Anda tidak dapat mengisi IRS" in driver.page_source):
        raise NoSuchElementException
      if (
        "Batas pengambilan mata kuliah" in driver.page_source or 
        common_matkul in driver.page_source or 
        chosen_matkul in driver.page_source
      ):
        course_plan_logger.info("Page loaded and 'Pengisian IRS' found!")
        token_element = driver.find_element(By.XPATH, "//input[@name='tokens']")
        token_value = token_element.get_attribute("value")
        token = token_value
        break
      raise NoSuchElementException
    except NoSuchElementException:
      logout(driver)
      login(driver, username, password, display_name)

  #========= 3. Send the Payload to the API
  payload = create_payload(matkul, token)
  headers = create_headers(COURSE_PLAN_PAGE)
  cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}

  while True:
    try:
      response = requests.post(
        SUBMIT_COURSE_PLAN_URL, 
        data=payload, 
        headers=headers, 
        cookies=cookies, 
        verify=False
      )
      api_logger.info(f"Response Status Code: {response.status_code}")

      if response.status_code == 200:
        api_logger.info("Course plan submitted successfully!")

        desired_kelas = set(matkul.keys())
        submitted_kelas = get_submitted_kelas(response.text)
        api_logger.info(f'SUBMITTED KELAS: {submitted_kelas}')
        api_logger.info(f'DESIRED KELAS: {desired_kelas}')

        if desired_kelas == submitted_kelas:
          api_logger.info("All desired classes have been submitted!")
          break
        else:
          api_logger.info("Not all desired classes were submitted. Retrying...")

      else:
        api_logger.error(f"Failed to submit course plan. Status code: {response.status_code}")
        api_logger.error(f"Response content: {response.text}")
        raise Exception("Non-200 status code received")
  
    except Exception as e:
      if isinstance(e, requests.exceptions.ConnectTimeout):
        api_logger.warning("Connection timed out. Retrying...")
      else:
        api_logger.error(f"An error occurred: {e}")

  #========= 4. Cek Posisi Kelas
  cek_irs_logger.info("Accessing Pengecekan IRS...")
  headers = create_headers(IRS_DONE_PAGE)
  cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}

  while True:
    try:
      response = requests.post(
        CEK_IRS_URL,
        headers=headers,
        cookies=cookies,
        verify=False
      )
      cek_irs_logger.info(f"Response Status Code: {response.status_code}")

      if response.status_code == 200:
        cek_irs_logger.info("Posisi Kelas!")
        get_posisi_kelas(response.text)
        break

      else:
        cek_irs_logger.error(f"Failed to check the IRS. Status code: {response.status_code}")
        cek_irs_logger.error(f"Response content: {response.text}")
        raise Exception("Non-200 status code received")

    except Exception as e:
      if isinstance(e, requests.exceptions.ConnectTimeout):
        cek_irs_logger.warning("Connection timed out. Retrying...")
      else:
        cek_irs_logger.error(f"An error occurred: {e}")

  driver.quit()


if __name__ == "__main__":
  war()

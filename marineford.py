from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import requests

# URLs
AUTH_PAGE = "https://academic.ui.ac.id/main/Authentication/"
HOME_PAGE = "https://academic.ui.ac.id/main/Welcome/Index"
COURSE_PLAN_PAGE = "https://academic.ui.ac.id/main/CoursePlan/CoursePlanEdit"
SUBMIT_COURSE_PLAN_URL = "https://academic.ui.ac.id/main/CoursePlan/CoursePlanSave"

def login(driver, username, password, display_name):
    print("Logging in...")
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
                print("Logged in!")
                break
            continue
        try:
            driver.get(HOME_PAGE)
            if ("Logout Counter" in driver.page_source or display_name in driver.page_source):
                print("Logged in!")
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
    payload = {
        'tokens': token,
        'comment': '',
        'submit': 'Simpan IRS'
    }
    
    for name, code in matkul.items():
        payload[f'c[{name}]'] = code
    try:
        response = requests.post(SUBMIT_COURSE_PLAN_URL, data=payload, headers=headers, cookies=cookies, verify=False)
        print(response)
        if response.status_code == 200:
            print("Course plan submitted successfully!")

            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table', class_='box')

            submitted_matkul = []
            rows = table.find_all('tr')
            for row in rows:
              cols = row.find_all('td')
              if len(cols) > 2:
                nama_mk = cols[2].get_text(strip=True)
                span_text = cols[2].find('span')
                if span_text:
                    submitted_matkul.append(span_text.get_text(strip=True))
                else:
                    submitted_matkul.append(nama_mk)
        else:
            print(f"Failed to submit course plan. Status code: {response.status_code}")
            print("Response content:", response.text)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

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
            name, code = line.split()
            matkul[name] = code

    print("Credentials and courses loaded!")
    print(creds)
    print(matkul)
    
    login(driver, username, password, display_name)
    
    # Navigate to the course plan page and retrieve the token
    driver.get(COURSE_PLAN_PAGE)
    time.sleep(1)  # Wait for the page to load
    
    token_element = driver.find_element(By.XPATH, "//input[@name='tokens']")
    token_value = token_element.get_attribute("value")

    # Extract cookies from the browser
    cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
    
    if token_value:
        print("Token retrieved!")
        submit_course_plan(token_value, matkul, cookies)
    else:
        print("Token not found.")
    driver.quit()

if __name__ == "__main__":
    main()

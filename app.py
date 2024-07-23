from flask import Flask, render_template, request, jsonify, send_file
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import os

app = Flask(__name__)

def scrape_daraz(product_name, num_pages_to_scrape):
    chrome_options = webdriver.ChromeOptions()
    chrome_service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get("https://www.daraz.pk/")
    
    search_bar = driver.find_element(By.XPATH, "//*[@id='q']")
    search_bar.send_keys(product_name)
    search_bar.submit()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//*[@id='root']/div/div[3]/div/div/div[1]/div[3]/div[2]/div/ul/li"))
    )

    total_pages = get_total_pages(driver)

    if num_pages_to_scrape > total_pages or num_pages_to_scrape < 1:
        driver.quit()
        return "Invalid number of pages."

    product_names = []
    product_prices = []
    product_ratings = []
    product_people_rated = []
    product_units_sold = []

    for page_num in range(num_pages_to_scrape):
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//*[@id='id-title']"))
        )

        products = driver.find_elements(By.XPATH, "//*[@id='id-title']")
        prices = driver.find_elements(By.XPATH, "//*[@id='id-price']/div/div[1]/span[@class='currency--GVKjl']")
        ratings = driver.find_elements(By.XPATH, "//*[@class = 'ratig-num--KNake rating--pwPrV']")
        people_rated = driver.find_elements(By.XPATH, "//*[@class = 'rating__review--ygkUy rating--pwPrV']")
        units_sold = driver.find_elements(By.XPATH, "//div[contains(text(), 'Sold')]")

        for i in range(len(products)):
            product_names.append(products[i].text)
            product_prices.append(prices[i].text if i < len(prices) else '0')
            product_ratings.append(ratings[i].text if i < len(ratings) else '0')
            product_people_rated.append(people_rated[i].text if i < len(people_rated) else '0')
            product_units_sold.append(units_sold[i].text.split(' ')[0] if i < len(units_sold) else '0')
        
        if page_num < num_pages_to_scrape - 1:
            retry_count = 0
            max_retries = 5
            while retry_count < max_retries:
                try:
                    next_button = driver.find_element(By.XPATH, "//*[@id='root']/div/div[3]/div/div/div[1]/div[3]/div[2]/div/ul/li[9]/a")
                    driver.execute_script("arguments[0].scrollIntoView();", next_button)
                    next_button.click()
                    time.sleep(5)
                    break
                except ElementClickInterceptedException:
                    retry_count += 1
                    time.sleep(2)
                except TimeoutException:
                    break

    df = pd.DataFrame({
        'Product Name': product_names,
        'Price': product_prices,
        'Rating': product_ratings,
        'People Rated': product_people_rated,
        'Units Sold': product_units_sold
    })

    # Save the file in a known directory
    file_path = os.path.join(os.getcwd(), 'daraz_product_search.xlsx')
    df.to_excel(file_path, index=False)
    driver.quit()
    return file_path

def get_total_pages(driver):
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, "//*[@id='root']/div/div[3]/div/div/div[1]/div[3]/div[2]/div/ul/li"))
    )
    pages = driver.find_elements(By.XPATH, "//*[@id='root']/div/div[3]/div/div/div[1]/div[3]/div[2]/div/ul/li")
    return int(pages[-2].text)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_total_pages', methods=['POST'])
def get_pages():
    product_name = request.form['product_name']
    chrome_options = webdriver.ChromeOptions()
    chrome_service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get("https://www.daraz.pk/")
    
    search_bar = driver.find_element(By.XPATH, "//*[@id='q']")
    search_bar.send_keys(product_name)
    search_bar.submit()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//*[@id='root']/div/div[3]/div/div/div[1]/div[3]/div[2]/div/ul/li"))
    )

    total_pages = get_total_pages(driver)
    driver.quit()
    return jsonify({'total_pages': total_pages})

@app.route('/scrape', methods=['POST'])
def scrape():
    product_name = request.form['product_name']
    num_pages = int(request.form['num_pages'])
    file_path = scrape_daraz(product_name, num_pages)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found.", 404

if __name__ == "__main__":
    app.run(debug=True)

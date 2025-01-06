from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shoes.db'  # Same database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Shoes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(250), nullable=False)
    product_subtitle = db.Column(db.String(250), nullable=True)
    product_gender = db.Column(db.String(250), nullable=True)
    product_price = db.Column(db.String(250), nullable=True)
    first_image_link = db.Column(db.String(250), nullable=True)
    product_data = db.Column(db.String, nullable=True)  # Storing serialized dictionary data


# Create tables in the database
with app.app_context():
    db.create_all()

# Set up the WebDriver (in this case, ChromeDriver)
driver = webdriver.Chrome()

# URL of the webpage you want to scrape
# url = "https://www.nike.com/ca/w/mens-shoes-nik1zy7ok"
url = "https://www.nike.com/ca/w/womens-shoes-5e1x6zy7ok"

# Open the webpage
driver.get(url)

SCROLL_PAUSE_TIME = 5

# Get the total height of the page and scroll down multiple times
last_height = driver.execute_script("return document.body.scrollHeight")

while True:
    # Scroll down to the bottom
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Wait for the page to load
    time.sleep(SCROLL_PAUSE_TIME)

    # Calculate new scroll height and compare with the last scroll height
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

# After scrolling is complete, scrape all items
title_elements = driver.find_elements(By.CLASS_NAME, "product-card__title")
subtitle_elements = driver.find_elements(By.CLASS_NAME, "product-card__subtitle")
img_elements = driver.find_elements(By.CLASS_NAME, "product-card__hero-image")
price_elements = driver.find_elements(By.CLASS_NAME, "product-price")
product_links = driver.find_elements(By.CLASS_NAME, "product-card__link-overlay")

all_items = []
for img_element in img_elements:
    img_src = img_element.get_attribute("src")
    all_items.append(img_src)
    print(f"Found image: {img_src}")

all_product_links = []
all_product_names = []
for i in range(0, len(title_elements)):
    print(i)
    title = title_elements[i].text
    subtitle = subtitle_elements[i].text
    price = price_elements[i].text
    img = img_elements[i].get_attribute("src")
    product_link = product_links[i].get_attribute("href")
    if 'launch' in product_link:
        continue
    if 'by-you' in product_link:
        continue
    if 'custom' in product_link:
        continue
    all_product_names.append(title)
    all_product_links.append(product_link)
    print(f"Title: {title}, Subtitle: {subtitle}, Price: {price}, Image Link: {img}, Product Link: {product_link}")
    with app.app_context():
        new_product = Shoes(product_name=title,
                            product_subtitle=subtitle,
                            product_gender='F',
                            # product_gender='M',
                            product_price=price,
                            first_image_link=img)
        db.session.add(new_product)
        db.session.commit()

print(f"Total items scraped: {len(all_items)}")
print(all_product_links)
print(len(all_product_links))
print(all_product_names)
print(len(all_product_names))

# for product in all_product_names:
# for i in range(0, len(all_product_names)):
for product_link in all_product_links:
    # print(all_product_names.index(product))
    # print(link)
    driver.get(product_link)
    # time.sleep(5)
    # Find image elements
    images = driver.find_elements(By.CLASS_NAME, "css-euolf")
    first_image = driver.find_element(By.CLASS_NAME, "css-1vqvh57")

    # Try to find the video element
    try:
        video_element = driver.find_element(By.CLASS_NAME, "css-k7hb9y")
        video_element_link = video_element.get_attribute("src")
        print("Video Element found: " + video_element_link)
    except Exception as e:
        print("Video element not found")
        video_element_link = "Video element not found"

    other_media = []
    # Print image sources
    for image in images:
        img_src = image.get_attribute("src")
        other_media.append(img_src)
        print(img_src)

    # Print first image source
    first_image_link = first_image.get_attribute("src")
    print(first_image_link)

    with app.app_context():
        shoes_data = {
            "first_image_link": first_image_link,
            "video_link": video_element_link,
            "other_media": other_media
        }
        data_str = json.dumps(shoes_data)
        print(data_str)
        shoe = Shoes.query.filter_by(product_name=all_product_names[all_product_links.index(product_link)]).first()
        print(all_product_names[all_product_links.index(product_link)])
        # shoe = db.get_or_404(Shoes, all_product_links.index(product_link))
        # print(shoe.product_name)
        if shoe:
            shoe.product_data = data_str
            db.session.commit()

# Close the browser session
driver.quit()

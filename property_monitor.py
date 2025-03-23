import requests
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import logging
import json
from datetime import datetime
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("property_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PropertyMonitor")

class PropertyMonitor:
    def __init__(self, target_street, postal_code, email_to=None):
        self.target_street = target_street.lower()
        self.postal_code = postal_code
        self.email_to = email_to
        self.previous_listings = self.load_previous_listings()
        
        # Define the websites to monitor - URLs adjusted for your specific search
        self.sites = [
            {
                "name": "Boliga",
                "url": f"https://www.boliga.dk/resultat?q={self.target_street}&postnr={self.postal_code}",
                "parser": self.parse_boliga
            },
            {
                "name": "Home",
                "url": f"https://home.dk/ejendomme?searchtext={self.target_street}%20{self.postal_code}",
                "parser": self.parse_home
            },
            {
                "name": "Nybolig",
                "url": f"https://www.nybolig.dk/til-salg/ejerlejlighed/{self.postal_code}/{self.target_street}",
                "parser": self.parse_nybolig
            },
            {
                "name": "EDC",
                "url": f"https://www.edc.dk/alle-boliger/{self.postal_code}/{self.target_street}/ejerlejlighed/",
                "parser": self.parse_edc
            },
            {
                "name": "Danbolig",
                "url": f"https://www.danbolig.dk/bolig/s%C3%B8g/?propertytype=5&zipcode={self.postal_code}&address={self.target_street}",
                "parser": self.parse_danbolig
            },
            {
                "name": "Boligsiden",
                "url": f"https://www.boligsiden.dk/adresse/{self.target_street.replace(' ', '-')}-{self.postal_code}",
                "parser": self.parse_boligsiden
            }
        ]
    
    def load_previous_listings(self):
        """Load previously found listings from JSON file"""
        filename = "previous_listings.json"
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading previous listings: {e}")
                return {}
        return {}
    
    def save_listings(self, listings):
        """Save current listings to JSON file"""
        with open("previous_listings.json", 'w') as f:
            json.dump(listings, f, indent=2)
    
    def run(self):
        """Main method to run the property monitor"""
        logger.info(f"Starting property monitor for street: {self.target_street} in {self.postal_code}")
        
        all_current_listings = {}
        new_listings = []
        
        for site in self.sites:
            try:
                logger.info(f"Checking {site['name']}...")
                response = requests.get(site['url'], headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }, timeout=30)
                
                if response.status_code == 200:
                    listings = site['parser'](response.text)
                    all_current_listings[site['name']] = listings
                    
                    # Check for new listings
                    previous = self.previous_listings.get(site['name'], [])
                    for listing in listings:
                        is_new = True
                        for prev_listing in previous:
                            if listing['address'] == prev_listing['address'] and listing['price'] == prev_listing['price']:
                                is_new = False
                                break
                        
                        if is_new:
                            new_listings.append({
                                "site": site['name'],
                                "details": listing
                            })
                else:
                    logger.error(f"Failed to access {site['name']}, status code: {response.status_code}")
            
            except Exception as e:
                logger.error(f"Error processing {site['name']}: {e}")
        
        # Save current listings for future comparison
        self.save_listings(all_current_listings)
        
        # Notify if new listings found
        if new_listings:
            logger.info(f"Found {len(new_listings)} new listings!")
            self.send_notification(new_listings)
        else:
            logger.info("No new listings found")
        
        return new_listings
    
    # Parser implementations for each site
    def parse_boliga(self, html_content):
        """Parse listings from Boliga"""
        soup = BeautifulSoup(html_content, 'html.parser')
        listings = []
        
        # This parser needs to be adjusted based on actual site structure
        property_cards = soup.select('.propertyitem')  # Example selector
        
        for card in property_cards:
            try:
                # Extract address, check if it contains target street
                address_elem = card.select_one('.address')
                if not address_elem:
                    continue
                    
                address = address_elem.text.strip()
                
                if self.target_street.lower() in address.lower():
                    price_elem = card.select_one('.price')
                    size_elem = card.select_one('.size')
                    link_elem = card.select_one('a.property-link')
                    
                    price = price_elem.text.strip() if price_elem else "Price not available"
                    size = size_elem.text.strip() if size_elem else "Size not available"
                    link = "https://www.boliga.dk" + link_elem['href'] if link_elem else "#"
                    
                    listings.append({
                        "address": address,
                        "price": price,
                        "size": size,
                        "link": link,
                        "found_date": datetime.now().strftime("%Y-%m-%d")
                    })
            except Exception as e:
                logger.error(f"Error parsing Boliga property: {e}")
        
        return listings
    
    def parse_home(self, html_content):
        """Parse listings from Home"""
        soup = BeautifulSoup(html_content, 'html.parser')
        listings = []
        
        property_cards = soup.select('.property-list-item')  # Example selector
        
        for card in property_cards:
            try:
                address_elem = card.select_one('.property-address')
                if not address_elem:
                    continue
                    
                address = address_elem.text.strip()
                
                if self.target_street.lower() in address.lower():
                    price_elem = card.select_one('.property-price')
                    size_elem = card.select_one('.property-size')
                    link_elem = card.select_one('a.property-url')
                    
                    price = price_elem.text.strip() if price_elem else "Price not available"
                    size = size_elem.text.strip() if size_elem else "Size not available"
                    link = "https://home.dk" + link_elem['href'] if link_elem else "#"
                    
                    listings.append({
                        "address": address,
                        "price": price,
                        "size": size,
                        "link": link,
                        "found_date": datetime.now().strftime("%Y-%m-%d")
                    })
            except Exception as e:
                logger.error(f"Error parsing Home property: {e}")
        
        return listings
    
    def parse_nybolig(self, html_content):
        """Parse listings from Nybolig"""
        soup = BeautifulSoup(html_content, 'html.parser')
        listings = []
        
        property_cards = soup.select('.propertyCard')  # Example selector
        
        for card in property_cards:
            try:
                address_elem = card.select_one('.propertyCard__address')
                if not address_elem:
                    continue
                    
                address = address_elem.text.strip()
                
                if self.target_street.lower() in address.lower():
                    price_elem = card.select_one('.propertyCard__price')
                    size_elem = card.select_one('.propertyCard__areaSize')
                    link_elem = card.select_one('a.propertyCard__link')
                    
                    price = price_elem.text.strip() if price_elem else "Price not available"
                    size = size_elem.text.strip() if size_elem else "Size not available"
                    link = "https://www.nybolig.dk" + link_elem['href'] if link_elem else "#"
                    
                    listings.append({
                        "address": address,
                        "price": price,
                        "size": size,
                        "link": link,
                        "found_date": datetime.now().strftime("%Y-%m-%d")
                    })
            except Exception as e:
                logger.error(f"Error parsing Nybolig property: {e}")
        
        return listings
    
    def parse_edc(self, html_content):
        """Parse listings from EDC"""
        soup = BeautifulSoup(html_content, 'html.parser')
        listings = []
        
        property_cards = soup.select('.propertyCard')  # Example selector
        
        for card in property_cards:
            try:
                address_elem = card.select_one('.propertyCard__address')
                if not address_elem:
                    continue
                    
                address = address_elem.text.strip()
                
                if self.target_street.lower() in address.lower():
                    price_elem = card.select_one('.propertyCard__price')
                    size_elem = card.select_one('.propertyCard__areaSize')
                    link_elem = card.select_one('a.propertyCard__link')
                    
                    price = price_elem.text.strip() if price_elem else "Price not available"
                    size = size_elem.text.strip() if size_elem else "Size not available"
                    link = "https://www.edc.dk" + link_elem['href'] if link_elem else "#"
                    
                    listings.append({
                        "address": address,
                        "price": price,
                        "size": size,
                        "link": link,
                        "found_date": datetime.now().strftime("%Y-%m-%d")
                    })
            except Exception as e:
                logger.error(f"Error parsing EDC property: {e}")
        
        return listings
    
    def parse_danbolig(self, html_content):
        """Parse listings from Danbolig"""
        soup = BeautifulSoup(html_content, 'html.parser')
        listings = []
        
        property_cards = soup.select('.property-list-item')  # Example selector
        
        for card in property_cards:
            try:
                address_elem = card.select_one('.property-address')
                if not address_elem:
                    continue
                    
                address = address_elem.text.strip()
                
                if self.target_street.lower() in address.lower():
                    price_elem = card.select_one('.property-price')
                    size_elem = card.select_one('.property-size')
                    link_elem = card.select_one('a.property-link')
                    
                    price = price_elem.text.strip() if price_elem else "Price not available"
                    size = size_elem.text.strip() if size_elem else "Size not available"
                    link = "https://www.danbolig.dk" + link_elem['href'] if link_elem else "#"
                    
                    listings.append({
                        "address": address,
                        "price": price,
                        "size": size,
                        "link": link,
                        "found_date": datetime.now().strftime("%Y-%m-%d")
                    })
            except Exception as e:
                logger.error(f"Error parsing Danbolig property: {e}")
        
        return listings
    
    def parse_boligsiden(self, html_content):
        """Parse listings from Boligsiden"""
        soup = BeautifulSoup(html_content, 'html.parser')
        listings = []
        
        property_cards = soup.select('.propertyListItem')  # Example selector
        
        for card in property_cards:
            try:
                address_elem = card.select_one('.propertyListItem__address')
                if not address_elem:
                    continue
                    
                address = address_elem.text.strip()
                
                if self.target_street.lower() in address.lower():
                    price_elem = card.select_one('.propertyListItem__price')
                    size_elem = card.select_one('.propertyListItem__areaSize')
                    link_elem = card.select_one('a.propertyListItem__link')
                    
                    price = price_elem.text.strip() if price_elem else "Price not available"
                    size = size_elem.text.strip() if size_elem else "Size not available"
                    link = "https://www.boligsiden.dk" + link_elem['href'] if link_elem else "#"
                    
                    listings.append({
                        "address": address,
                        "price": price,
                        "size": size,
                        "link": link,
                        "found_date": datetime.now().strftime("%Y-%m-%d")
                    })
            except Exception as e:
                logger.error(f"Error parsing Boligsiden property: {e}")
        
        return listings
    
    def send_notification(self, new_listings):
        """Send email notification with new listings"""
        if not self.email_to:
            logger.info("No email address configured, skipping notification")
            return
        
        try:
            # Create email content
            msg = MIMEMultipart()
            msg['Subject'] = f"New Property Listings on {self.target_street}"
            msg['From'] = "your-email@example.com"  # Configure your email
            msg['To'] = self.email_to
            
            # Create email body with listings
            email_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .property {{ margin-bottom: 20px; border-bottom: 1px solid #ddd; padding-bottom: 15px; }}
                    .property h3 {{ margin-bottom: 5px; color: #444; }}
                    .details {{ margin-left: 15px; }}
                    .source {{ color: #888; font-style: italic; }}
                    .view-link {{ background-color: #4CAF50; color: white; padding: 5px 10px; 
                                text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 10px; }}
                </style>
            </head>
            <body>
                <h2>New apartments found on {self.target_street}, {self.postal_code}</h2>
                <p>Here are the new listings found in our latest scan:</p>
            """
            
            for item in new_listings:
                listing = item["details"]
                email_body += f"""
                <div class="property">
                    <h3>{listing['address']}</h3>
                    <div class="details">
                        <p><strong>Price:</strong> {listing['price']}</p>
                        <p><strong>Size:</strong> {listing['size']}</p>
                        <p class="source">Found on: {item['site']} (on {listing['found_date']})</p>
                        <a href="{listing['link']}" class="view-link">View Property</a>
                    </div>
                </div>
                """
            
            email_body += """
                <p>This is an automated notification from your Property Monitor.</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(email_body, 'html'))
            
            # Configure your email server settings
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login("your-email@gmail.com", "your-password")  # Use app password for Gmail
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Notification email sent to {self.email_to}")
        
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")


if __name__ == "__main__":
    # Configuration
    TARGET_STREET = "Havneholmen"  # Your target street
    POSTAL_CODE = "1561"  # Your postal code
    EMAIL_ADDRESS = "your-email@example.com"  # Replace with your email
    
    # Run the monitor
    monitor = PropertyMonitor(TARGET_STREET, POSTAL_CODE, EMAIL_ADDRESS)
    new_listings = monitor.run()
    
    # Output findings
    if new_listings:
        print(f"Found {len(new_listings)} new properties on {TARGET_STREET}!")
        for item in new_listings:
            print(f"\nFrom {item['site']}:")
            print(f"  Address: {item['details']['address']}")
            print(f"  Price: {item['details']['price']}")
            print(f"  Size: {item['details']['size']}")
            print(f"  Link: {item['details']['link']}")
    else:
        print(f"No new properties found on {TARGET_STREET}")

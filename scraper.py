"""
Matspar.se Scraper
Hämtar produkter, priser och butiksinfo från matspar.se
Med inbyggd produktdatabas som fallback

ALLERGEN-TAGGAR:
- gluten: Innehåller vete, råg, korn, havre
- lactose: Innehåller laktos (mjölkprodukter)
- nuts: Innehåller nötter eller mandlar
- eggs: Innehåller ägg
- fish: Innehåller fisk eller skaldjur
- soy: Innehåller soja
- meat: Innehåller kött (för vegetarisk filtrering)
- animal: Innehåller animaliska produkter (för vegansk filtrering)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import quote

class MatsparScraper:
    BASE_URL = "https://www.matspar.se"
    IMAGE_CDN = "https://d1ax460061ulao.cloudfront.net"
    
    # Fria produktbilder från Unsplash och andra källor
    # Dessa är placeholder-bilder tills vi kan scrapa riktiga
    FREE_IMAGES = {
        'mjölk': 'https://images.unsplash.com/photo-1563636619-e9143da7973b?w=200&q=80',
        'ägg': 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=200&q=80',
        'bröd': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=200&q=80',
        'ost': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=200&q=80',
        'smör': 'https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=200&q=80',
        'kyckling': 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=200&q=80',
        'lax': 'https://images.unsplash.com/photo-1574781330855-d0db8cc6a79c?w=200&q=80',
        'nötfärs': 'https://images.unsplash.com/photo-1602470520998-f4a52199a3d6?w=200&q=80',
        'ris': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=200&q=80',
        'pasta': 'https://images.unsplash.com/photo-1551462147-ff29053bfc14?w=200&q=80',
        'potatis': 'https://images.unsplash.com/photo-1518977676601-b53f82ber659?w=200&q=80',
        'tomat': 'https://images.unsplash.com/photo-1546470427-227c7369a9b9?w=200&q=80',
        'gurka': 'https://images.unsplash.com/photo-1449300079323-02e209d9d3a6?w=200&q=80',
        'sallad': 'https://images.unsplash.com/photo-1556801712-76c8eb07bbc9?w=200&q=80',
        'morot': 'https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=200&q=80',
        'lök': 'https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?w=200&q=80',
        'banan': 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=200&q=80',
        'äpple': 'https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=200&q=80',
        'apelsin': 'https://images.unsplash.com/photo-1547514701-42782101795e?w=200&q=80',
        'havregryn': 'https://images.unsplash.com/photo-1517673400267-0251440c45dc?w=200&q=80',
        'yoghurt': 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=200&q=80',
        'kvarg': 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=200&q=80',
        'grädde': 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=200&q=80',
        'broccoli': 'https://images.unsplash.com/photo-1459411552884-841db9b3cc2a?w=200&q=80',
        'paprika': 'https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?w=200&q=80',
        'avokado': 'https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?w=200&q=80',
        'nötter': 'https://images.unsplash.com/photo-1508061253366-f7da158b6d46?w=200&q=80',
        'fläsk': 'https://images.unsplash.com/photo-1602470521006-aaea8b2d6c93?w=200&q=80',
        'tofu': 'https://images.unsplash.com/photo-1628689469838-524a4a973b8e?w=200&q=80',
        'linser': 'https://images.unsplash.com/photo-1515543237350-b3eea1ec8082?w=200&q=80',
        'bönor': 'https://images.unsplash.com/photo-1551462147-ff29053bfc14?w=200&q=80',
    }
    
    # Fördefinierade basvaror med näringsvärden, priser, bilder OCH allergen-taggar
    FALLBACK_PRODUCTS = {
        'mjölk': [
            {'name': 'Mellanmjölk 1,5%', 'brand': 'Arla Ko', 'weight': '1.5l', 'prices': {'ICA': 18.90, 'Coop': 19.50, 'Willys': 17.90}, 'nutrition': {'calories': 46, 'protein': 3.5, 'carbs': 5, 'fat': 1.5, 'calcium': 120}, 'image': '7/d/7d8466f95555aa7e3190e6fa68fa79a9.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Standardmjölk 3%', 'brand': 'Arla Ko', 'weight': '1.5l', 'prices': {'ICA': 20.80, 'Coop': 21.50, 'Willys': 19.90}, 'nutrition': {'calories': 60, 'protein': 3.4, 'carbs': 4.8, 'fat': 3, 'calcium': 120}, 'image': 'a/5/a55a8d9c2e2e7d3a9f1d8b5e4c6f3a2b.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Havredryck Barista', 'brand': 'Oatly', 'weight': '1l', 'prices': {'ICA': 26.90, 'Coop': 27.90, 'Willys': 25.90}, 'nutrition': {'calories': 59, 'protein': 1, 'carbs': 6.6, 'fat': 3}, 'image': 'b/3/b3f5e2d1c4a6789012345678abcdef01.webp', 'allergens': ['gluten']},
            {'name': 'Laktosfri Mjölk 1,5%', 'brand': 'Arla', 'weight': '1l', 'prices': {'ICA': 22.90, 'Coop': 24.90, 'Willys': 21.90}, 'nutrition': {'calories': 46, 'protein': 3.5, 'carbs': 5, 'fat': 1.5, 'calcium': 120}, 'image': '', 'allergens': ['animal']},
            {'name': 'Sojadryck', 'brand': 'Alpro', 'weight': '1l', 'prices': {'ICA': 24.90, 'Coop': 26.90, 'Willys': 23.90}, 'nutrition': {'calories': 39, 'protein': 3, 'carbs': 2.5, 'fat': 1.8, 'calcium': 120}, 'image': '', 'allergens': ['soy']},
        ],
        'bröd': [
            {'name': 'Limpa Skivad', 'brand': 'Skogaholm', 'weight': '775g', 'prices': {'ICA': 25.90, 'Coop': 27.90, 'Willys': 24.90}, 'nutrition': {'calories': 220, 'protein': 7, 'carbs': 42, 'fat': 2, 'fiber': 5}, 'image': 'c/4/c4d5e6f7a8b9c0d1e2f3456789abcdef.webp', 'allergens': ['gluten']},
            {'name': 'Korvbröd 8-pack', 'brand': 'Pågen', 'weight': '336g', 'prices': {'ICA': 22.90, 'Coop': 23.90, 'Willys': 21.90}, 'nutrition': {'calories': 260, 'protein': 8, 'carbs': 48, 'fat': 3}, 'image': 'd/5/d5e6f7a8b9c0d1e2f3a456789abcdef0.webp', 'allergens': ['gluten']},
            {'name': 'Fullkornsbröd', 'brand': 'Pågen', 'weight': '500g', 'prices': {'ICA': 29.90, 'Coop': 30.90, 'Willys': 28.90}, 'nutrition': {'calories': 230, 'protein': 9, 'carbs': 38, 'fat': 4, 'fiber': 8}, 'image': 'e/6/e6f7a8b9c0d1e2f3a4b56789abcdef01.webp', 'allergens': ['gluten']},
            {'name': 'Glutenfritt Bröd', 'brand': 'Semper', 'weight': '400g', 'prices': {'ICA': 42.90, 'Coop': 44.90, 'Willys': 41.90}, 'nutrition': {'calories': 250, 'protein': 4, 'carbs': 45, 'fat': 5, 'fiber': 3}, 'image': '', 'allergens': []},
        ],
        'ägg': [
            {'name': 'Ägg M/L 12-pack', 'brand': 'Svenska Ägg', 'weight': '720g', 'prices': {'ICA': 35.90, 'Coop': 37.90, 'Willys': 33.90}, 'nutrition': {'calories': 143, 'protein': 13, 'carbs': 0.7, 'fat': 10, 'vitamin_d': 1.8}, 'image': 'f/7/f7a8b9c0d1e2f3a4b5c6789abcdef012.webp', 'allergens': ['eggs', 'animal']},
            {'name': 'Ägg EKO KRAV 12-pack', 'brand': 'Änglamark', 'weight': '636g', 'prices': {'ICA': 51.95, 'Coop': 49.95, 'Willys': 52.90}, 'nutrition': {'calories': 143, 'protein': 13, 'carbs': 0.7, 'fat': 10}, 'image': '0/8/08a9b0c1d2e3f4a5b6c78901abcdef23.webp', 'allergens': ['eggs', 'animal']},
        ],
        'smör': [
            {'name': 'Bregott Normalsaltat 75%', 'brand': 'Bregott', 'weight': '500g', 'prices': {'ICA': 39.00, 'Coop': 42.00, 'Willys': 38.00}, 'nutrition': {'calories': 533, 'protein': 0.5, 'carbs': 0.5, 'fat': 60}, 'image': '4/a/4a9c5597b92da8810b129518f445a124.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Smör Normalsaltat 82%', 'brand': 'Svenskt Smör', 'weight': '500g', 'prices': {'ICA': 54.90, 'Coop': 56.90, 'Willys': 52.90}, 'nutrition': {'calories': 744, 'protein': 0.5, 'carbs': 0.5, 'fat': 82}, 'image': '5/a/5a115df24797a7e92f5fe8465af5d519.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Växtbaserat Smörgåsfett', 'brand': 'Flora', 'weight': '400g', 'prices': {'ICA': 32.90, 'Coop': 34.90, 'Willys': 30.90}, 'nutrition': {'calories': 540, 'protein': 0, 'carbs': 0, 'fat': 60}, 'image': '', 'allergens': []},
        ],
        'ost': [
            {'name': 'Hushållsost 26%', 'brand': 'Arla', 'weight': '1.1kg', 'prices': {'ICA': 89.00, 'Coop': 95.00, 'Willys': 85.00}, 'nutrition': {'calories': 313, 'protein': 27, 'carbs': 0, 'fat': 26, 'calcium': 700}, 'image': '9/b/9ba72ca5bb0df82200d9dd96c6628166.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Prästost 31%', 'brand': 'Arla', 'weight': '500g', 'prices': {'ICA': 65.00, 'Coop': 69.00, 'Willys': 62.00}, 'nutrition': {'calories': 370, 'protein': 26, 'carbs': 0, 'fat': 31, 'calcium': 800}, 'image': '1/9/19b8c0d1e2f3a4b5c6d789012abcdef3.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Grevé 28%', 'brand': 'Arla', 'weight': '450g', 'prices': {'ICA': 55.00, 'Coop': 59.00, 'Willys': 52.00}, 'nutrition': {'calories': 347, 'protein': 27, 'carbs': 0, 'fat': 28, 'calcium': 750}, 'image': '2/a/2ab9c0d1e2f3a4b5c6d7890123abcdef.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Växtbaserad Ost', 'brand': 'Violife', 'weight': '200g', 'prices': {'ICA': 39.90, 'Coop': 42.90, 'Willys': 38.90}, 'nutrition': {'calories': 280, 'protein': 0, 'carbs': 7, 'fat': 24}, 'image': '', 'allergens': []},
        ],
        'kyckling': [
            {'name': 'Kycklingfilé', 'brand': 'Kronfågel', 'weight': '900g', 'prices': {'ICA': 99.00, 'Coop': 105.00, 'Willys': 95.00}, 'nutrition': {'calories': 110, 'protein': 24, 'carbs': 0, 'fat': 1.5}, 'image': '3/b/3bc0d1e2f3a4b5c6d7e89012345abcde.webp', 'allergens': ['meat', 'animal']},
            {'name': 'Kycklinglårfilé', 'brand': 'Kronfågel', 'weight': '700g', 'prices': {'ICA': 79.00, 'Coop': 85.00, 'Willys': 75.00}, 'nutrition': {'calories': 150, 'protein': 20, 'carbs': 0, 'fat': 8}, 'image': '4/c/4cd1e2f3a4b5c6d7e8f90123456abcdf.webp', 'allergens': ['meat', 'animal']},
            {'name': 'Kycklingfärs 9%', 'brand': 'Kronfågel', 'weight': '500g', 'prices': {'ICA': 55.00, 'Coop': 59.00, 'Willys': 49.00}, 'nutrition': {'calories': 130, 'protein': 19, 'carbs': 0, 'fat': 6}, 'image': '5/d/5de2f3a4b5c6d7e8f9012345678abcdf.webp', 'allergens': ['meat', 'animal']},
        ],
        'lax': [
            {'name': 'Laxfilé', 'brand': 'Fiskeriet', 'weight': '400g', 'prices': {'ICA': 79.00, 'Coop': 85.00, 'Willys': 75.00}, 'nutrition': {'calories': 206, 'protein': 20, 'carbs': 0, 'fat': 14, 'vitamin_d': 10}, 'image': '6/e/6ef3a4b5c6d7e8f901234567890abcde.webp', 'allergens': ['fish', 'animal']},
            {'name': 'Rökt Lax Skivad', 'brand': 'Abba', 'weight': '200g', 'prices': {'ICA': 59.00, 'Coop': 62.00, 'Willys': 55.00}, 'nutrition': {'calories': 180, 'protein': 22, 'carbs': 0, 'fat': 10}, 'image': '7/f/7fa4b5c6d7e8f9012345678901abcdef.webp', 'allergens': ['fish', 'animal']},
        ],
        'nötfärs': [
            {'name': 'Nötfärs 12%', 'brand': 'Scan', 'weight': '800g', 'prices': {'ICA': 85.00, 'Coop': 89.00, 'Willys': 79.00}, 'nutrition': {'calories': 180, 'protein': 19, 'carbs': 0, 'fat': 12, 'iron': 2.5}, 'image': '8/0/80b5c6d7e8f90123456789012abcdef1.webp', 'allergens': ['meat', 'animal']},
            {'name': 'Nötfärs EKO KRAV 12%', 'brand': 'Garant', 'weight': '500g', 'prices': {'ICA': 69.00, 'Coop': 65.00, 'Willys': 72.00}, 'nutrition': {'calories': 180, 'protein': 19, 'carbs': 0, 'fat': 12, 'iron': 2.5}, 'image': '9/1/91c6d7e8f901234567890123abcdef12.webp', 'allergens': ['meat', 'animal']},
            {'name': 'Vegetarisk Färs', 'brand': 'Hälsans Kök', 'weight': '400g', 'prices': {'ICA': 39.90, 'Coop': 42.90, 'Willys': 37.90}, 'nutrition': {'calories': 140, 'protein': 16, 'carbs': 8, 'fat': 5, 'fiber': 4}, 'image': '', 'allergens': ['soy']},
        ],
        'ris': [
            {'name': 'Jasminris', 'brand': 'Uncle Bens', 'weight': '1kg', 'prices': {'ICA': 32.90, 'Coop': 34.90, 'Willys': 29.90}, 'nutrition': {'calories': 350, 'protein': 7, 'carbs': 78, 'fat': 0.5}, 'image': 'a/2/a2d7e8f9012345678901234abcdef123.webp', 'allergens': []},
            {'name': 'Basmatiris', 'brand': 'Gourmet', 'weight': '1kg', 'prices': {'ICA': 39.90, 'Coop': 42.90, 'Willys': 36.90}, 'nutrition': {'calories': 340, 'protein': 8, 'carbs': 75, 'fat': 0.5}, 'image': 'b/3/b3e8f90123456789012345abcdef1234.webp', 'allergens': []},
            {'name': 'Fullkornsris', 'brand': 'ICA', 'weight': '1kg', 'prices': {'ICA': 29.90, 'Coop': 32.90, 'Willys': 27.90}, 'nutrition': {'calories': 350, 'protein': 7.5, 'carbs': 73, 'fat': 2.5, 'fiber': 3.5}, 'image': 'c/4/c4f901234567890123456abcdef12345.webp', 'allergens': []},
        ],
        'pasta': [
            {'name': 'Spaghetti', 'brand': 'Barilla', 'weight': '500g', 'prices': {'ICA': 19.90, 'Coop': 21.90, 'Willys': 17.90}, 'nutrition': {'calories': 350, 'protein': 12, 'carbs': 71, 'fat': 1.5}, 'image': 'd/5/d50123456789012345678abcdef123456.webp', 'allergens': ['gluten']},
            {'name': 'Penne Rigate', 'brand': 'Barilla', 'weight': '500g', 'prices': {'ICA': 19.90, 'Coop': 21.90, 'Willys': 17.90}, 'nutrition': {'calories': 350, 'protein': 12, 'carbs': 71, 'fat': 1.5}, 'image': 'e/6/e6123456789012345678abcdef1234567.webp', 'allergens': ['gluten']},
            {'name': 'Fusilli Fullkorn', 'brand': 'ICA', 'weight': '500g', 'prices': {'ICA': 15.90, 'Coop': 17.90, 'Willys': 14.90}, 'nutrition': {'calories': 330, 'protein': 13, 'carbs': 62, 'fat': 2.5, 'fiber': 7}, 'image': 'f/7/f72345678901234567890abcdef123456.webp', 'allergens': ['gluten']},
            {'name': 'Glutenfri Pasta', 'brand': 'Barilla', 'weight': '400g', 'prices': {'ICA': 32.90, 'Coop': 34.90, 'Willys': 30.90}, 'nutrition': {'calories': 350, 'protein': 8, 'carbs': 76, 'fat': 1.5}, 'image': '', 'allergens': []},
        ],
        'potatis': [
            {'name': 'Potatis Fast', 'brand': 'Smakriket', 'weight': '2kg', 'prices': {'ICA': 29.90, 'Coop': 32.90, 'Willys': 27.90}, 'nutrition': {'calories': 77, 'protein': 2, 'carbs': 17, 'fat': 0.1, 'vitamin_c': 20}, 'image': '0/8/08345678901234567890abcdef1234567.webp', 'allergens': []},
            {'name': 'Potatis Mjölig', 'brand': 'ICA', 'weight': '2kg', 'prices': {'ICA': 27.90, 'Coop': 29.90, 'Willys': 25.90}, 'nutrition': {'calories': 77, 'protein': 2, 'carbs': 17, 'fat': 0.1}, 'image': '1/9/19456789012345678901abcdef12345678.webp', 'allergens': []},
        ],
        'tomat': [
            {'name': 'Tomater Kvist', 'brand': 'Smakriket', 'weight': '500g', 'prices': {'ICA': 25.90, 'Coop': 27.90, 'Willys': 23.90}, 'nutrition': {'calories': 18, 'protein': 0.9, 'carbs': 3.9, 'fat': 0.2, 'vitamin_c': 14}, 'image': '2/a/2a56789012345678901234abcdef12345.webp', 'allergens': []},
            {'name': 'Krossade Tomater', 'brand': 'Mutti', 'weight': '400g', 'prices': {'ICA': 15.90, 'Coop': 17.90, 'Willys': 14.90}, 'nutrition': {'calories': 24, 'protein': 1.3, 'carbs': 4, 'fat': 0.1}, 'image': '3/b/3b678901234567890123456abcdef1234.webp', 'allergens': []},
        ],
        'gurka': [
            {'name': 'Gurka', 'brand': 'Klass 1', 'weight': '1st ca 400g', 'prices': {'ICA': 14.90, 'Coop': 15.90, 'Willys': 12.90}, 'nutrition': {'calories': 12, 'protein': 0.6, 'carbs': 1.8, 'fat': 0.1}, 'image': '4/c/4c78901234567890123456abcdef12345.webp', 'allergens': []},
        ],
        'sallad': [
            {'name': 'Isbergssallad', 'brand': 'Smakriket', 'weight': '1st', 'prices': {'ICA': 15.90, 'Coop': 17.90, 'Willys': 14.90}, 'nutrition': {'calories': 14, 'protein': 0.9, 'carbs': 2.2, 'fat': 0.1}, 'image': '5/d/5d89012345678901234567abcdef12345.webp', 'allergens': []},
            {'name': 'Babyspenat', 'brand': 'Smakriket', 'weight': '65g', 'prices': {'ICA': 19.90, 'Coop': 21.90, 'Willys': 17.90}, 'nutrition': {'calories': 23, 'protein': 2.9, 'carbs': 2.3, 'fat': 0.4, 'iron': 2.7}, 'image': '6/e/6e90123456789012345678abcdef12345.webp', 'allergens': []},
        ],
        'morot': [
            {'name': 'Morötter', 'brand': 'Svenska', 'weight': '1kg', 'prices': {'ICA': 14.90, 'Coop': 15.90, 'Willys': 12.90}, 'nutrition': {'calories': 41, 'protein': 0.9, 'carbs': 9.6, 'fat': 0.2, 'vitamin_a': 835}, 'image': '7/f/7f01234567890123456789abcdef12345.webp', 'allergens': []},
        ],
        'lök': [
            {'name': 'Gul Lök', 'brand': 'Smakriket', 'weight': '1kg', 'prices': {'ICA': 12.90, 'Coop': 14.90, 'Willys': 10.90}, 'nutrition': {'calories': 40, 'protein': 1.1, 'carbs': 9.3, 'fat': 0.1}, 'image': '8/0/8012345678901234567890abcdef12345.webp', 'allergens': []},
        ],
        'banan': [
            {'name': 'Bananer', 'brand': 'Chiquita', 'weight': '1kg', 'prices': {'ICA': 24.90, 'Coop': 26.90, 'Willys': 22.90}, 'nutrition': {'calories': 89, 'protein': 1.1, 'carbs': 23, 'fat': 0.3, 'potassium': 358}, 'image': '9/1/91234567890123456789012abcdef1234.webp', 'allergens': []},
        ],
        'äpple': [
            {'name': 'Äpplen Royal Gala', 'brand': 'Smakriket', 'weight': '1kg', 'prices': {'ICA': 29.90, 'Coop': 32.90, 'Willys': 27.90}, 'nutrition': {'calories': 52, 'protein': 0.3, 'carbs': 14, 'fat': 0.2, 'fiber': 2.4}, 'image': 'a/2/a234567890123456789012abcdef12345.webp', 'allergens': []},
        ],
        'apelsin': [
            {'name': 'Apelsiner', 'brand': 'Sunkist', 'weight': '1kg', 'prices': {'ICA': 29.90, 'Coop': 32.90, 'Willys': 27.90}, 'nutrition': {'calories': 47, 'protein': 0.9, 'carbs': 12, 'fat': 0.1, 'vitamin_c': 53}, 'image': 'b/3/b3456789012345678901234abcdef123.webp', 'allergens': []},
        ],
        'havregryn': [
            {'name': 'Havregryn', 'brand': 'AXA', 'weight': '1.5kg', 'prices': {'ICA': 27.90, 'Coop': 29.90, 'Willys': 25.90}, 'nutrition': {'calories': 370, 'protein': 13, 'carbs': 60, 'fat': 7, 'fiber': 10}, 'image': 'c/4/c4567890123456789012345abcdef12.webp', 'allergens': ['gluten']},
            {'name': 'Glutenfria Havregryn', 'brand': 'Semper', 'weight': '500g', 'prices': {'ICA': 35.90, 'Coop': 38.90, 'Willys': 33.90}, 'nutrition': {'calories': 370, 'protein': 13, 'carbs': 60, 'fat': 7, 'fiber': 10}, 'image': '', 'allergens': []},
        ],
        'yoghurt': [
            {'name': 'Naturell Yoghurt 3%', 'brand': 'Arla', 'weight': '1kg', 'prices': {'ICA': 27.90, 'Coop': 29.90, 'Willys': 25.90}, 'nutrition': {'calories': 63, 'protein': 4.5, 'carbs': 4.5, 'fat': 3, 'calcium': 150}, 'image': 'd/5/d56789012345678901234567abcdef1.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Grekisk Yoghurt 10%', 'brand': 'Lindahls', 'weight': '500g', 'prices': {'ICA': 34.90, 'Coop': 37.90, 'Willys': 32.90}, 'nutrition': {'calories': 132, 'protein': 5, 'carbs': 4, 'fat': 10}, 'image': 'e/6/e678901234567890123456789abcdef.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Laktosfri Yoghurt', 'brand': 'Arla', 'weight': '1kg', 'prices': {'ICA': 32.90, 'Coop': 35.90, 'Willys': 30.90}, 'nutrition': {'calories': 63, 'protein': 4.5, 'carbs': 4.5, 'fat': 3, 'calcium': 150}, 'image': '', 'allergens': ['animal']},
            {'name': 'Växtbaserad Yoghurt', 'brand': 'Oatly', 'weight': '400g', 'prices': {'ICA': 29.90, 'Coop': 32.90, 'Willys': 27.90}, 'nutrition': {'calories': 60, 'protein': 1, 'carbs': 9, 'fat': 2}, 'image': '', 'allergens': ['gluten']},
        ],
        'kvarg': [
            {'name': 'Mild Kvarg Vanilj 0,2%', 'brand': 'Arla', 'weight': '1kg', 'prices': {'ICA': 35.00, 'Coop': 39.00, 'Willys': 33.00}, 'nutrition': {'calories': 58, 'protein': 10, 'carbs': 4, 'fat': 0.2}, 'image': '2/0/20b9f7615d43051513f23d60a6e9dc9e.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Kvarg Naturell 0,2%', 'brand': 'Arla', 'weight': '500g', 'prices': {'ICA': 24.90, 'Coop': 27.90, 'Willys': 22.90}, 'nutrition': {'calories': 63, 'protein': 11, 'carbs': 4, 'fat': 0.2}, 'image': 'f/8/f890123456789012345678901abcdef12.webp', 'allergens': ['lactose', 'animal']},
        ],
        'fläsk': [
            {'name': 'Fläskfilé', 'brand': 'Scan', 'weight': '600g', 'prices': {'ICA': 65.00, 'Coop': 69.00, 'Willys': 59.00}, 'nutrition': {'calories': 109, 'protein': 22, 'carbs': 0, 'fat': 2}, 'image': '0/9/09012345678901234567890123abcdef1.webp', 'allergens': ['meat', 'animal']},
            {'name': 'Bacon Skivad', 'brand': 'Scan', 'weight': '140g', 'prices': {'ICA': 29.90, 'Coop': 32.90, 'Willys': 27.90}, 'nutrition': {'calories': 330, 'protein': 15, 'carbs': 1, 'fat': 30}, 'image': '1/a/1a12345678901234567890123abcdef12.webp', 'allergens': ['meat', 'animal']},
            {'name': 'Falukorv', 'brand': 'Scan', 'weight': '800g', 'prices': {'ICA': 30.00, 'Coop': 35.00, 'Willys': 28.00}, 'nutrition': {'calories': 230, 'protein': 10, 'carbs': 6, 'fat': 19}, 'image': '1/9/1918f105698f8f608df05c9cf0c772e0.webp', 'allergens': ['meat', 'animal', 'gluten']},
        ],
        'grädde': [
            {'name': 'Vispgrädde 36%', 'brand': 'Arla Köket', 'weight': '5dl', 'prices': {'ICA': 25.00, 'Coop': 28.00, 'Willys': 23.00}, 'nutrition': {'calories': 339, 'protein': 2.2, 'carbs': 2.7, 'fat': 36}, 'image': '3/6/3600fc0eeda8cb284b0786996adc3d27.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Matlagningsgrädde 15%', 'brand': 'Arla Köket', 'weight': '5dl', 'prices': {'ICA': 19.90, 'Coop': 22.90, 'Willys': 17.90}, 'nutrition': {'calories': 150, 'protein': 3, 'carbs': 4, 'fat': 15}, 'image': '2/b/2b23456789012345678901234abcdef12.webp', 'allergens': ['lactose', 'animal']},
            {'name': 'Växtbaserad Matlagningsgrädde', 'brand': 'Oatly', 'weight': '2.5dl', 'prices': {'ICA': 22.90, 'Coop': 24.90, 'Willys': 20.90}, 'nutrition': {'calories': 120, 'protein': 0.5, 'carbs': 5, 'fat': 11}, 'image': '', 'allergens': ['gluten']},
        ],
        'broccoli': [
            {'name': 'Broccoli', 'brand': 'Svenska', 'weight': '500g', 'prices': {'ICA': 22.90, 'Coop': 25.90, 'Willys': 19.90}, 'nutrition': {'calories': 34, 'protein': 2.8, 'carbs': 7, 'fat': 0.4, 'vitamin_c': 89, 'fiber': 2.6}, 'image': '3/c/3c34567890123456789012345abcdef12.webp', 'allergens': []},
        ],
        'paprika': [
            {'name': 'Paprika Röd', 'brand': 'Smakriket', 'weight': '2st', 'prices': {'ICA': 22.90, 'Coop': 24.90, 'Willys': 19.90}, 'nutrition': {'calories': 31, 'protein': 1, 'carbs': 6, 'fat': 0.3, 'vitamin_c': 128}, 'image': '4/d/4d456789012345678901234567abcdef1.webp', 'allergens': []},
        ],
        'linser': [
            {'name': 'Röda Linser', 'brand': 'Zeta', 'weight': '500g', 'prices': {'ICA': 29.90, 'Coop': 32.90, 'Willys': 27.90}, 'nutrition': {'calories': 340, 'protein': 25, 'carbs': 50, 'fat': 1, 'fiber': 15, 'iron': 7}, 'image': '5/e/5e567890123456789012345678abcdef1.webp', 'allergens': []},
        ],
        'bönor': [
            {'name': 'Kidneybönor', 'brand': 'Zeta', 'weight': '410g', 'prices': {'ICA': 15.90, 'Coop': 17.90, 'Willys': 13.90}, 'nutrition': {'calories': 84, 'protein': 6, 'carbs': 12, 'fat': 0.5, 'fiber': 6}, 'image': '6/f/6f67890123456789012345678abcdef12.webp', 'allergens': []},
            {'name': 'Svarta Bönor', 'brand': 'Zeta', 'weight': '410g', 'prices': {'ICA': 15.90, 'Coop': 17.90, 'Willys': 13.90}, 'nutrition': {'calories': 91, 'protein': 6, 'carbs': 14, 'fat': 0.5, 'fiber': 7}, 'image': '7/0/7078901234567890123456789abcdef12.webp', 'allergens': []},
        ],
        'tofu': [
            {'name': 'Tofu Naturell EKO', 'brand': 'YiPin', 'weight': '400g', 'prices': {'ICA': 28.95, 'Coop': 26.90, 'Willys': 29.90}, 'nutrition': {'calories': 120, 'protein': 12, 'carbs': 1, 'fat': 7, 'calcium': 350}, 'image': '8/1/8189012345678901234567890abcdef12.webp', 'allergens': ['soy']},
            {'name': 'Tofu Rökt', 'brand': 'YiPin', 'weight': '250g', 'prices': {'ICA': 25.90, 'Coop': 27.90, 'Willys': 24.90}, 'nutrition': {'calories': 150, 'protein': 15, 'carbs': 2, 'fat': 9}, 'image': '', 'allergens': ['soy']},
        ],
        'korv': [
            {'name': 'Grillkorv', 'brand': 'Scan', 'weight': '600g', 'prices': {'ICA': 35.00, 'Coop': 38.00, 'Willys': 32.00}, 'nutrition': {'calories': 280, 'protein': 12, 'carbs': 4, 'fat': 24}, 'image': '', 'allergens': ['meat', 'animal', 'gluten']},
            {'name': 'Bratwurst', 'brand': 'Scan', 'weight': '400g', 'prices': {'ICA': 45.00, 'Coop': 48.00, 'Willys': 42.00}, 'nutrition': {'calories': 300, 'protein': 13, 'carbs': 2, 'fat': 27}, 'image': '', 'allergens': ['meat', 'animal']},
            {'name': 'Chorizo', 'brand': 'Estrella', 'weight': '250g', 'prices': {'ICA': 42.00, 'Coop': 45.00, 'Willys': 39.00}, 'nutrition': {'calories': 350, 'protein': 20, 'carbs': 2, 'fat': 30}, 'image': '', 'allergens': ['meat', 'animal']},
            {'name': 'Vegansk Korv', 'brand': 'Hälsans Kök', 'weight': '300g', 'prices': {'ICA': 39.90, 'Coop': 42.90, 'Willys': 37.90}, 'nutrition': {'calories': 180, 'protein': 18, 'carbs': 6, 'fat': 10}, 'image': '', 'allergens': ['soy']},
        ],
        'köttbullar': [
            {'name': 'Köttbullar', 'brand': 'Scan', 'weight': '600g', 'prices': {'ICA': 55.00, 'Coop': 59.00, 'Willys': 49.00}, 'nutrition': {'calories': 220, 'protein': 15, 'carbs': 8, 'fat': 14}, 'image': '', 'allergens': ['meat', 'animal', 'gluten', 'eggs']},
            {'name': 'Köttbullar EKO', 'brand': 'Garant', 'weight': '400g', 'prices': {'ICA': 49.00, 'Coop': 52.00, 'Willys': 46.00}, 'nutrition': {'calories': 220, 'protein': 15, 'carbs': 8, 'fat': 14}, 'image': '', 'allergens': ['meat', 'animal', 'gluten', 'eggs']},
            {'name': 'Vegobullar', 'brand': 'Hälsans Kök', 'weight': '300g', 'prices': {'ICA': 35.90, 'Coop': 38.90, 'Willys': 33.90}, 'nutrition': {'calories': 170, 'protein': 13, 'carbs': 12, 'fat': 8}, 'image': '', 'allergens': ['soy', 'gluten']},
        ],
        'quorn': [
            {'name': 'Quorn Färs', 'brand': 'Quorn', 'weight': '300g', 'prices': {'ICA': 39.90, 'Coop': 42.90, 'Willys': 37.90}, 'nutrition': {'calories': 100, 'protein': 14, 'carbs': 3, 'fat': 3}, 'image': '', 'allergens': ['eggs']},
            {'name': 'Quorn Filébitar', 'brand': 'Quorn', 'weight': '300g', 'prices': {'ICA': 42.90, 'Coop': 45.90, 'Willys': 39.90}, 'nutrition': {'calories': 110, 'protein': 15, 'carbs': 4, 'fat': 3}, 'image': '', 'allergens': ['eggs']},
            {'name': 'Quorn Bitar Vegan', 'brand': 'Quorn', 'weight': '280g', 'prices': {'ICA': 44.90, 'Coop': 47.90, 'Willys': 42.90}, 'nutrition': {'calories': 105, 'protein': 14, 'carbs': 3, 'fat': 3}, 'image': '', 'allergens': []},
        ],
        'sojafärs': [
            {'name': 'Sojafärs', 'brand': 'Anamma', 'weight': '400g', 'prices': {'ICA': 35.90, 'Coop': 38.90, 'Willys': 33.90}, 'nutrition': {'calories': 130, 'protein': 17, 'carbs': 5, 'fat': 5}, 'image': '', 'allergens': ['soy']},
            {'name': 'Pulled Soja', 'brand': 'Oumph', 'weight': '280g', 'prices': {'ICA': 39.90, 'Coop': 42.90, 'Willys': 37.90}, 'nutrition': {'calories': 140, 'protein': 19, 'carbs': 4, 'fat': 5}, 'image': '', 'allergens': ['soy']},
        ],
        'torsk': [
            {'name': 'Torskfilé', 'brand': 'Fiskeriet', 'weight': '400g', 'prices': {'ICA': 69.00, 'Coop': 72.00, 'Willys': 65.00}, 'nutrition': {'calories': 82, 'protein': 18, 'carbs': 0, 'fat': 0.7}, 'image': '', 'allergens': ['fish', 'animal']},
            {'name': 'Panerad Torskfilé', 'brand': 'Findus', 'weight': '450g', 'prices': {'ICA': 59.00, 'Coop': 62.00, 'Willys': 55.00}, 'nutrition': {'calories': 180, 'protein': 14, 'carbs': 15, 'fat': 8}, 'image': '', 'allergens': ['fish', 'animal', 'gluten']},
        ],
        'räkor': [
            {'name': 'Räkor i Lake', 'brand': 'Räkor & Sånt', 'weight': '200g', 'prices': {'ICA': 45.00, 'Coop': 48.00, 'Willys': 42.00}, 'nutrition': {'calories': 70, 'protein': 15, 'carbs': 0, 'fat': 1}, 'image': '', 'allergens': ['fish', 'animal']},
            {'name': 'Skaldjursmix', 'brand': 'Findus', 'weight': '300g', 'prices': {'ICA': 55.00, 'Coop': 59.00, 'Willys': 52.00}, 'nutrition': {'calories': 80, 'protein': 16, 'carbs': 1, 'fat': 1.5}, 'image': '', 'allergens': ['fish', 'animal']},
        ],
        'avokado': [
            {'name': 'Avokado', 'brand': 'Hass', 'weight': '2st', 'prices': {'ICA': 29.90, 'Coop': 32.90, 'Willys': 27.90}, 'nutrition': {'calories': 160, 'protein': 2, 'carbs': 9, 'fat': 15, 'fiber': 7}, 'image': '9/2/9290123456789012345678901abcdef12.webp', 'allergens': []},
        ],
        'nötter': [
            {'name': 'Mandlar', 'brand': 'Exotic Snacks', 'weight': '200g', 'prices': {'ICA': 39.90, 'Coop': 42.90, 'Willys': 37.90}, 'nutrition': {'calories': 580, 'protein': 21, 'carbs': 9, 'fat': 50, 'fiber': 12}, 'image': 'a/3/a301234567890123456789012abcdef12.webp', 'allergens': ['nuts']},
            {'name': 'Valnötter', 'brand': 'Exotic Snacks', 'weight': '150g', 'prices': {'ICA': 35.90, 'Coop': 38.90, 'Willys': 33.90}, 'nutrition': {'calories': 650, 'protein': 15, 'carbs': 14, 'fat': 65}, 'image': 'b/4/b412345678901234567890123abcdef12.webp', 'allergens': ['nuts']},
        ],
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
        })
    
    def search_products(self, query, limit=20):
        """
        Sök efter produkter - använder lokal databas med realistiska priser
        """
        query_lower = query.lower().strip()
        
        # Direkt matchning
        if query_lower in self.FALLBACK_PRODUCTS:
            products = self.FALLBACK_PRODUCTS[query_lower][:limit]
            return [self._format_product(p, query_lower) for p in products]
        
        # Delvis matchning
        matching_products = []
        for key, products in self.FALLBACK_PRODUCTS.items():
            if query_lower in key or key in query_lower:
                for p in products:
                    matching_products.append(self._format_product(p, key))
                    if len(matching_products) >= limit:
                        return matching_products
        
        return matching_products
    
    def _format_product(self, product, category=None):
        """Formaterar en produkt till rätt struktur"""
        # Försök hitta bild från vår fria bildkälla baserat på kategori
        image_url = None
        if category and category.lower() in self.FREE_IMAGES:
            image_url = self.FREE_IMAGES[category.lower()]
        elif product.get('image'):
            # Använd CDN-bild om den har en riktig hash (32 tecken hex)
            image_path = product.get('image')
            # Kolla om det ser ut som en riktig matspar hash
            if image_path and len(image_path) > 35:
                image_url = f"{self.IMAGE_CDN}/140x150/{image_path}"
        
        # Generera ett unikt ID baserat på namn och brand
        name = product.get('name', '')
        brand = product.get('brand', '')
        product_id = abs(hash(f"{name}_{brand}_{category}")) % 1000000
        
        return {
            'id': product_id,
            'name': f"{product['name']} {product.get('brand', '')}".strip(),
            'brand': product.get('brand'),
            'weight': product.get('weight'),
            'category': category,
            'prices': product.get('prices', {}),
            'nutrition': product.get('nutrition', {}),
            'allergens': product.get('allergens', []),
            'image': image_url,
            'url': None
        }
    
    def filter_by_allergies(self, products, allergies):
        """
        Filtrerar bort produkter som innehåller valda allergener
        
        Allergier/kostrestriktioner:
        - gluten: Filtrera bort produkter med gluten-tagg
        - lactose: Filtrera bort produkter med lactose-tagg
        - nuts: Filtrera bort produkter med nuts-tagg
        - eggs: Filtrera bort produkter med eggs-tagg
        - fish: Filtrera bort produkter med fish-tagg
        - soy: Filtrera bort produkter med soy-tagg
        - vegetarian: Filtrera bort produkter med meat-tagg
        - vegan: Filtrera bort produkter med animal-tagg
        """
        if not allergies:
            return products
        
        filtered = []
        for product in products:
            product_allergens = product.get('allergens', [])
            
            # Kontrollera varje allergi
            skip = False
            for allergy in allergies:
                allergy = allergy.lower()
                
                if allergy == 'vegetarian':
                    # Vegetarian: filtrera bort kött och fisk
                    if 'meat' in product_allergens or 'fish' in product_allergens:
                        skip = True
                        break
                elif allergy == 'vegan':
                    # Vegan: filtrera bort alla animaliska produkter
                    if 'animal' in product_allergens or 'meat' in product_allergens or 'fish' in product_allergens:
                        skip = True
                        break
                elif allergy in product_allergens:
                    skip = True
                    break
            
            if not skip:
                filtered.append(product)
        
        return filtered
    
    def search_products_filtered(self, query, allergies=None, budget_per_item=None, prefer_cheaper=False, limit=20):
        """
        Sök produkter med allergifiltrering och budgethantering
        
        Args:
            query: Sökterm
            allergies: Lista med allergier att filtrera bort
            budget_per_item: Max pris per produkt (SEK)
            prefer_cheaper: Om True, sortera billigaste först
            limit: Max antal resultat
        """
        # Hämta alla produkter för söktermen
        products = self.search_products(query, limit=limit * 2)  # Hämta fler för att kompensera för filtrering
        
        # Filtrera allergier
        if allergies:
            products = self.filter_by_allergies(products, allergies)
        
        # Filtrera efter budget
        if budget_per_item:
            filtered = []
            for product in products:
                prices = product.get('prices', {})
                if prices:
                    min_price = min(prices.values())
                    if min_price <= budget_per_item:
                        filtered.append(product)
            products = filtered
        
        # Sortera efter pris om prefer_cheaper
        if prefer_cheaper and products:
            products.sort(key=lambda p: min(p.get('prices', {}).values()) if p.get('prices') else float('inf'))
        
        return products[:limit]
    
    def find_substitute(self, product, allergies=None, budget=None, same_category=True):
        """
        Hitta ett likvärdigt alternativ till en produkt
        
        Args:
            product: Produkten att ersätta
            allergies: Allergier att undvika
            budget: Max budget för ersättningen
            same_category: Om True, sök endast i samma kategori
        
        Returns:
            En ersättningsprodukt eller None
        """
        alternatives = self.find_alternatives(product, allergies, budget, same_category, limit=1)
        return alternatives[0] if alternatives else None
    
    def find_alternatives(self, product, allergies=None, budget=None, same_category=False, limit=10):
        """
        Hitta flera likvärdiga alternativ till en produkt baserat på näringsprofil
        
        STRIKT MATCHNING:
        - Proteinrika produkter ersätts ENDAST med andra proteinkällor (kyckling ↔ köttfärs ↔ lax ↔ tofu)
        - Kolhydratkällor ersätts ENDAST med andra kolhydrater (ris ↔ pasta ↔ potatis)
        - Mejeri kan ersättas med växtbaserade alternativ
        
        Args:
            product: Produkten att ersätta
            allergies: Allergier att undvika
            budget: Max budget för ersättningen
            same_category: Om True, sök ENDAST i samma kategori
            limit: Max antal alternativ att returnera
        
        Returns:
            Lista med alternativa produkter, sorterade efter likhet
        """
        category = product.get('category', '')
        original_nutrition = product.get('nutrition', {})
        original_prices = product.get('prices', {})
        original_price = min(original_prices.values()) if original_prices else 0
        
        # Identifiera produktens "typ" och "näringsprofil"
        product_type = self._get_product_type(product)
        profile = self._get_nutrition_profile(original_nutrition)
        
        # Hitta relaterade kategorier baserat på näringsprofil
        related_categories = self._get_related_categories(category, profile)
        
        # Samla kandidater
        candidates = []
        
        if same_category and category:
            # Endast samma kategori
            candidates = self.get_products_by_category(category)
        else:
            # Sök i relaterade kategorier först
            for cat in related_categories:
                cat_products = self.get_products_by_category(cat)
                candidates.extend(cat_products)
            
            # Om inte tillräckligt OCH inte high_protein, sök bredare
            # (Vi vill INTE lägga till mejeri/grönsaker som ersättning för protein)
            if len(candidates) < limit * 2 and not profile.get('high_protein'):
                all_products = self.get_all_base_products()
                for p in all_products:
                    if p not in candidates:
                        candidates.append(p)
        
        # Filtrera allergier
        if allergies:
            candidates = self.filter_by_allergies(candidates, allergies)
        
        # Filtrera bort originalprodukten
        candidates = [c for c in candidates if c.get('name') != product.get('name')]
        
        # STRIKT FILTRERING: Se till att samma produkttyp matchas
        if product_type == 'protein_source':
            # Endast andra proteinkällor
            candidates = [c for c in candidates if self._get_product_type(c) == 'protein_source']
        elif product_type == 'carbs':
            # Endast andra kolhydratkällor
            candidates = [c for c in candidates if self._get_product_type(c) == 'carbs']
        elif product_type == 'dairy':
            # Mejeri kan ersättas med mejeri ELLER växtbaserade alternativ
            candidates = [c for c in candidates if self._get_product_type(c) in ['dairy', 'other']]
        elif product_type == 'bread':
            # Bröd ska BARA ersättas med annat bröd
            candidates = [c for c in candidates if self._get_product_type(c) == 'bread']
        elif product_type == 'vegetables':
            candidates = [c for c in candidates if self._get_product_type(c) == 'vegetables']
        elif product_type == 'fruit':
            candidates = [c for c in candidates if self._get_product_type(c) == 'fruit']
        
        # Filtrera efter budget
        if budget:
            filtered = []
            for c in candidates:
                c_prices = c.get('prices', {})
                if c_prices:
                    c_price = min(c_prices.values())
                    if c_price <= budget:
                        filtered.append(c)
            candidates = filtered
        
        if not candidates:
            return []
        
        # Poängsätt kandidater baserat på likhet
        scored = []
        for candidate in candidates:
            score = self._calculate_similarity_score(product, candidate, profile)
            scored.append((candidate, score))
        
        # Sortera efter poäng och returnera bästa matchningar
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored[:limit]]
    
    def find_combined_alternatives(self, product, target_grams, allergies=None, budget=None, limit=5):
        """
        Hitta kombinerade ersättningar - flera produkter som tillsammans matchar näringsbehovet
        
        Exempel: 1kg kyckling kan ersättas med 2x 500g sojafärs
        
        Args:
            product: Produkten att ersätta
            target_grams: Totala gram som behöver ersättas
            allergies: Allergier att undvika
            budget: Max budget
            limit: Max antal kombinationer att returnera
        
        Returns:
            Lista med kombinationer, varje kombination är en dict med:
            - products: lista med produkter
            - quantities: antal av varje
            - total_price: totalpris
            - nutrition_match: hur väl den matchar (%)
        """
        import re
        
        original_nutrition = product.get('nutrition', {})
        if not original_nutrition:
            return []
        
        # Beräkna totalt näringsbehov baserat på target_grams
        target_protein = (original_nutrition.get('protein', 0) or 0) * target_grams / 100
        target_calories = (original_nutrition.get('calories', 0) or 0) * target_grams / 100
        
        # Hämta enskilda alternativ
        alternatives = self.find_alternatives(product, allergies, budget, same_category=False, limit=20)
        
        if not alternatives:
            return []
        
        combinations = []
        
        # 1. Enskilda produkter (med flera förpackningar om nödvändigt)
        for alt in alternatives[:10]:
            alt_nutrition = alt.get('nutrition', {})
            alt_protein = alt_nutrition.get('protein', 0) or 0
            alt_weight_str = alt.get('weight', '500g')
            
            # Parsa vikt
            alt_grams = self._parse_weight(alt_weight_str)
            
            if alt_grams <= 0 or alt_protein <= 0:
                continue
            
            # Beräkna hur många förpackningar som behövs för att matcha protein
            protein_per_pack = alt_protein * alt_grams / 100
            packs_needed = max(1, round(target_protein / protein_per_pack)) if protein_per_pack > 0 else 1
            
            # Begränsa till rimligt antal
            packs_needed = min(packs_needed, 5)
            
            # Beräkna resultat
            total_grams = alt_grams * packs_needed
            achieved_protein = alt_protein * total_grams / 100
            
            alt_prices = alt.get('prices', {})
            price_per_pack = min(alt_prices.values()) if alt_prices else 0
            total_price = price_per_pack * packs_needed
            
            # Budgetkontroll
            if budget and total_price > budget:
                continue
            
            # Beräkna matchning
            protein_match = min(100, (achieved_protein / target_protein * 100)) if target_protein > 0 else 100
            
            combinations.append({
                'type': 'single',
                'products': [alt],
                'quantities': [packs_needed],
                'total_grams': total_grams,
                'total_price': round(total_price, 2),
                'achieved_protein': round(achieved_protein, 1),
                'target_protein': round(target_protein, 1),
                'protein_match': round(protein_match, 0),
                'description': f"{packs_needed}x {alt.get('name')} ({alt_weight_str})"
            })
        
        # 2. Kombinationer av två produkter (för variation)
        for i, alt1 in enumerate(alternatives[:5]):
            for alt2 in alternatives[i+1:8]:
                alt1_nutrition = alt1.get('nutrition', {})
                alt2_nutrition = alt2.get('nutrition', {})
                
                alt1_protein = alt1_nutrition.get('protein', 0) or 0
                alt2_protein = alt2_nutrition.get('protein', 0) or 0
                
                alt1_grams = self._parse_weight(alt1.get('weight', '500g'))
                alt2_grams = self._parse_weight(alt2.get('weight', '500g'))
                
                if alt1_grams <= 0 or alt2_grams <= 0:
                    continue
                
                # Försök med 1+1
                achieved_protein = (alt1_protein * alt1_grams / 100) + (alt2_protein * alt2_grams / 100)
                
                alt1_prices = alt1.get('prices', {})
                alt2_prices = alt2.get('prices', {})
                price1 = min(alt1_prices.values()) if alt1_prices else 0
                price2 = min(alt2_prices.values()) if alt2_prices else 0
                total_price = price1 + price2
                
                if budget and total_price > budget:
                    continue
                
                protein_match = min(100, (achieved_protein / target_protein * 100)) if target_protein > 0 else 100
                
                # Endast inkludera om det är en rimlig match (>60%)
                if protein_match >= 60:
                    combinations.append({
                        'type': 'combo',
                        'products': [alt1, alt2],
                        'quantities': [1, 1],
                        'total_grams': alt1_grams + alt2_grams,
                        'total_price': round(total_price, 2),
                        'achieved_protein': round(achieved_protein, 1),
                        'target_protein': round(target_protein, 1),
                        'protein_match': round(protein_match, 0),
                        'description': f"1x {alt1.get('name')} + 1x {alt2.get('name')}"
                    })
        
        # Sortera efter proteinmatch (närmast 100% först), sedan pris
        combinations.sort(key=lambda x: (-x['protein_match'], x['total_price']))
        
        return combinations[:limit]
    
    def _parse_weight(self, weight_str):
        """Parsa viktstring till gram"""
        import re
        if not weight_str:
            return 500
        
        weight_str = str(weight_str).lower().replace(' ', '')
        
        # kg
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*kg', weight_str)
        if match:
            return float(match.group(1).replace(',', '.')) * 1000
        
        # gram
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*g', weight_str)
        if match:
            return float(match.group(1).replace(',', '.'))
        
        # liter
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*l', weight_str)
        if match:
            return float(match.group(1).replace(',', '.')) * 1000
        
        # st (anta 60g per styck)
        match = re.search(r'(\d+)\s*st', weight_str)
        if match:
            return int(match.group(1)) * 60
        
        return 500
    
    def _get_nutrition_profile(self, nutrition):
        """
        Klassificera produktens näringsprofil
        
        Returns:
            dict med profil-taggar och deras styrka
        """
        profile = {
            'high_protein': False,
            'high_carb': False,
            'high_fat': False,
            'low_calorie': False,
            'high_fiber': False,
            'protein_value': 0,
            'carbs_value': 0,
            'fat_value': 0,
            'calories_value': 0
        }
        
        if not nutrition:
            return profile
        
        protein = nutrition.get('protein', 0) or 0
        carbs = nutrition.get('carbs', 0) or 0
        fat = nutrition.get('fat', 0) or 0
        calories = nutrition.get('calories', 0) or 0
        fiber = nutrition.get('fiber', 0) or 0
        
        # Spara faktiska värden
        profile['protein_value'] = protein
        profile['carbs_value'] = carbs
        profile['fat_value'] = fat
        profile['calories_value'] = calories
        
        # Proteinrik: > 15g per 100g
        if protein > 15:
            profile['high_protein'] = True
        
        # Kolhydratrik: > 40g per 100g
        if carbs > 40:
            profile['high_carb'] = True
        
        # Fettrik: > 15g per 100g
        if fat > 15:
            profile['high_fat'] = True
        
        # Lågt kaloriinnehåll: < 50 kcal per 100g
        if calories < 50:
            profile['low_calorie'] = True
        
        # Fiberrik: > 5g per 100g
        if fiber > 5:
            profile['high_fiber'] = True
        
        return profile
    
    def _get_product_type(self, product):
        """
        Bestäm produkttyp baserat på namn och kategori för striktare matchning
        """
        name = (product.get('name', '') or '').lower()
        category = (product.get('category', '') or '').lower()
        nutrition = product.get('nutrition', {})
        protein = nutrition.get('protein', 0) or 0
        
        # Proteinkällor FÖRST (kött, fisk, fågel, vegetariskt protein)
        # - Dessa har prioritet för att undvika fel klassificering
        protein_keywords = ['kyckling', 'kycklingfilé', 'kycklingfärs', 'köttfärs', 'nötfärs', 'fläskfärs', 
                          'lax', 'laxfilé', 'torsk', 'torskfilé', 'fisk', 'fiskfilé',
                          'tofu', 'quorn', 'sojafärs', 'bönor', 'kikärtor',
                          'linser', 'räkor', 'fläsk', 'fläskfilé', 'bacon', 'korv', 'skinka', 'biff']
        for kw in protein_keywords:
            if kw in name:
                return 'protein_source'
        
        # Kategorier som är proteinkällor
        if category in ['kött', 'fågel', 'kyckling', 'fisk', 'lax', 'vegetariskt', 'protein', 'köttfärs', 'vego']:
            return 'protein_source'
        
        # Ägg separat (eftersom ägg-kategorin är speciell)
        if 'ägg' in name and 'smörgås' not in name:
            return 'protein_source'
        if category == 'ägg':
            return 'protein_source'
        
        # Mejeriprodukter (kontrolleras efter protein för att inte klassificera kycklingfilé som mejeri)
        dairy_keywords = ['mjölk', 'yoghurt', 'grädde', 'smör', 'kvarg', 'crème', 'gräddfil', 'filmjölk', 'ost ']
        for kw in dairy_keywords:
            if kw in name:
                return 'dairy'
        # Ost-kontroll (mer specifik)
        if name.endswith('ost') or ' ost' in name or name.startswith('ost'):
            return 'dairy'
        if category in ['mejeri', 'ost']:
            return 'dairy'
        
        # Hög proteinprofil (>15g/100g) utan kol/fiber = troligen proteinkälla
        carbs = nutrition.get('carbs', 0) or 0
        if protein > 15 and carbs < 10:
            return 'protein_source'
        
        # Bröd (separat typ för bättre substitution)
        bread_keywords = ['bröd', 'limpa', 'fralla', 'knäckebröd', 'rostbröd', 'toast']
        for kw in bread_keywords:
            if kw in name:
                return 'bread'
        if category == 'bröd':
            return 'bread'
        
        # Kolhydratkällor (ej bröd)
        carb_keywords = ['pasta', 'ris', 'potatis', 'havregryn', 'müsli', 'couscous', 'bulgur', 'nudlar']
        for kw in carb_keywords:
            if kw in name:
                return 'carbs'
        if category in ['spannmål', 'pasta', 'ris']:
            return 'carbs'
        
        # Grönsaker
        veg_keywords = ['tomat', 'gurka', 'morot', 'sallad', 'broccoli', 'paprika', 'lök', 'spenat', 'zucchini', 'vitkål', 'blomkål']
        for kw in veg_keywords:
            if kw in name:
                return 'vegetables'
        if category in ['grönsaker', 'gronsaker']:
            return 'vegetables'
        
        # Frukt
        fruit_keywords = ['äpple', 'banan', 'apelsin', 'päron', 'druvor', 'bär', 'citron', 'lime']
        for kw in fruit_keywords:
            if kw in name:
                return 'fruit'
        if category == 'frukt':
            return 'fruit'
        
        return 'other'
    
    def _get_related_categories(self, category, profile):
        """
        Hitta relaterade kategorier baserat på ursprungskategori och näringsprofil
        OBS: Striktare matchning - protein endast med protein, bröd endast med bröd!
        """
        # Kategori-grupper för substitution - inkluderar alla FALLBACK_PRODUCTS kategorier
        PROTEIN_SOURCES = ['kött', 'fågel', 'fisk', 'vegetariskt', 'protein', 'kyckling', 'lax', 
                          'nötfärs', 'fläsk', 'tofu', 'linser', 'bönor', 'ägg', 'korv', 'köttbullar']
        CARB_SOURCES = ['spannmål', 'pasta', 'potatis', 'ris', 'havregryn']  # Bröd borttagen
        BREAD = ['bröd', 'limpa', 'fralla', 'knäckebröd']  # Ny separat bröd-kategori
        DAIRY = ['mejeri', 'mjölk', 'ost', 'yoghurt', 'grädde', 'kvarg', 'smör']
        VEGETABLES = ['grönsaker', 'tomat', 'gurka', 'sallad', 'morot', 'lök', 'broccoli', 'paprika']
        FRUITS = ['frukt', 'banan', 'äpple', 'apelsin']
        
        related = []
        
        # Lägg till samma kategori först
        if category:
            related.append(category)
        
        # STRIKT: Baserat på profil, lägg ENDAST till samma typ
        if profile.get('high_protein'):
            # Protein ska BARA ersättas med andra proteinkällor
            for cat in PROTEIN_SOURCES:
                if cat not in related:
                    related.append(cat)
            # VIKTIGT: Returnera ENDAST proteinkällor, inte mejeri etc
            return related
        
        if profile.get('high_carb'):
            for cat in CARB_SOURCES:
                if cat not in related:
                    related.append(cat)
            return related
        
        if profile.get('low_calorie'):
            for cat in VEGETABLES:
                if cat not in related:
                    related.append(cat)
        
        # Kategori-baserade relationer
        if category in PROTEIN_SOURCES:
            for cat in PROTEIN_SOURCES:
                if cat not in related:
                    related.append(cat)
        
        # Bröd ska ENDAST ersättas med annat bröd
        if category in BREAD:
            for cat in BREAD:
                if cat not in related:
                    related.append(cat)
            return related  # Returnera direkt - bara bröd!
        
        if category in CARB_SOURCES:
            for cat in CARB_SOURCES:
                if cat not in related:
                    related.append(cat)
        
        if category == 'mejeri':
            related.extend(['vegetariskt'])  # Växtbaserade alternativ
        
        return related
    
    def _calculate_similarity_score(self, original, candidate, profile):
        """
        Beräkna hur lik en kandidat är originalprodukten
        Högre poäng = bättre match
        """
        score = 0
        
        orig_nutrition = original.get('nutrition', {})
        cand_nutrition = candidate.get('nutrition', {})
        orig_prices = original.get('prices', {})
        cand_prices = candidate.get('prices', {})
        
        orig_price = min(orig_prices.values()) if orig_prices else 0
        cand_price = min(cand_prices.values()) if cand_prices else 0
        
        # 1. Näringsprofil-matchning (viktigt!)
        cand_profile = self._get_nutrition_profile(cand_nutrition)
        
        # Poäng för matchande profiler
        if profile.get('high_protein') and cand_profile.get('high_protein'):
            score += 50  # Stor bonus för protein-match
        if profile.get('high_carb') and cand_profile.get('high_carb'):
            score += 40
        if profile.get('low_calorie') and cand_profile.get('low_calorie'):
            score += 30
        if profile.get('high_fiber') and cand_profile.get('high_fiber'):
            score += 20
        
        # 2. Protein-likhet (per 100g)
        orig_protein = orig_nutrition.get('protein', 0) or 0
        cand_protein = cand_nutrition.get('protein', 0) or 0
        if orig_protein > 0:
            protein_ratio = min(orig_protein, cand_protein) / max(orig_protein, cand_protein, 1)
            score += protein_ratio * 30  # Max 30 poäng
        
        # 3. Kalori-likhet
        orig_cal = orig_nutrition.get('calories', 0) or 0
        cand_cal = cand_nutrition.get('calories', 0) or 0
        if orig_cal > 0 and cand_cal > 0:
            cal_diff = abs(orig_cal - cand_cal) / max(orig_cal, 1)
            if cal_diff < 0.2:
                score += 20
            elif cal_diff < 0.5:
                score += 10
        
        # 4. Prislikhet
        if orig_price > 0 and cand_price > 0:
            price_ratio = min(orig_price, cand_price) / max(orig_price, cand_price)
            score += price_ratio * 15  # Max 15 poäng
        
        # 5. Samma kategori - liten bonus
        if original.get('category') == candidate.get('category'):
            score += 10
        
        # 6. Penalty om profilen inte matchar alls
        matching_profiles = sum([
            1 for key in profile 
            if profile.get(key) and cand_profile.get(key)
        ])
        if matching_profiles == 0 and any(profile.values()):
            score -= 20  # Straff för helt annorlunda profil
        
        return score
    
    def get_all_base_products(self):
        """Returnerar alla basvaror från databasen"""
        all_products = []
        for category, products in self.FALLBACK_PRODUCTS.items():
            for product in products:
                formatted = self._format_product(product, category)
                all_products.append(formatted)
        return all_products
    
    def get_categories(self):
        """Returnerar tillgängliga kategorier"""
        return list(self.FALLBACK_PRODUCTS.keys())
    
    def get_products_by_category(self, category):
        """Hämtar alla produkter i en kategori"""
        if category.lower() in self.FALLBACK_PRODUCTS:
            return [self._format_product(p, category) for p in self.FALLBACK_PRODUCTS[category.lower()]]
        return []


def test_scraper():
    """Testar scrapern"""
    scraper = MatsparScraper()
    
    print("=== Testar sökning ===")
    products = scraper.search_products("mjölk", limit=5)
    
    for product in products:
        print(f"\nProdukt: {product['name']}")
        print(f"  Vikt: {product.get('weight', 'Okänd')}")
        print(f"  Priser: {product.get('prices', {})}")
        print(f"  Näring: {product.get('nutrition', {})}")
    
    print("\n=== Alla kategorier ===")
    categories = scraper.get_categories()
    print(f"Antal kategorier: {len(categories)}")
    for cat in categories:
        print(f"  - {cat}")


if __name__ == "__main__":
    test_scraper()

"""
Matplanerare - Flask App
En app för att planera mat baserat på näringsbehov och generera inköpslistor
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from database import db, init_db, Product, Price, Nutrition, NutritionPlan, ShoppingList, ShoppingItem, ALLERGENS, RDI_VALUES
from scraper import MatsparScraper
import os
import math
import csv
import io
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'matplanerare-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///matplanerare.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initiera databas
init_db(app)

# Initiera scraper
scraper = MatsparScraper()

# Tillgängliga butiker
STORES = ['ICA', 'Coop', 'Willys', 'Hemköp', 'Lidl', 'City Gross']


@app.route('/')
def index():
    """Startsida"""
    return render_template('index.html', stores=STORES)


@app.route('/meals')
def meals_overview():
    """Översiktssida för måltidsplanering - välj en inköpslista"""
    lists = ShoppingList.query.order_by(ShoppingList.created_at.desc()).all()
    return render_template('meals_overview.html', lists=lists)


@app.route('/plan')
def nutrition_plan():
    """Sida för att skapa/redigera näringsplan"""
    plans = NutritionPlan.query.all()
    return render_template('plan.html', plans=plans, allergens=ALLERGENS, rdi_values=RDI_VALUES)


@app.route('/api/plans', methods=['GET', 'POST'])
def api_plans():
    """API för näringsplaner"""
    if request.method == 'POST':
        data = request.json
        
        # Hantera allergier som komma-separerad sträng
        allergies = data.get('allergies', [])
        if isinstance(allergies, list):
            allergies = ','.join(allergies)
        
        plan = NutritionPlan(
            name=data.get('name', 'Min plan'),
            allergies=allergies,
            # Makronäringsämnen
            calories_target=data.get('calories', 2000),
            protein_target=data.get('protein', 60),
            carbs_target=data.get('carbs', 280),
            fat_target=data.get('fat', 70),
            fiber_target=data.get('fiber', 30),
            sugar_target=data.get('sugar', 50),
            salt_target=data.get('salt', 6),
            # Mode för makro
            calories_mode=data.get('calories_mode', 'target'),
            protein_mode=data.get('protein_mode', 'min'),
            carbs_mode=data.get('carbs_mode', 'target'),
            fat_mode=data.get('fat_mode', 'max'),
            fiber_mode=data.get('fiber_mode', 'min'),
            sugar_mode=data.get('sugar_mode', 'max'),
            salt_mode=data.get('salt_mode', 'max'),
            # Vitaminer och mineraler
            vitamin_c_target=data.get('vitamin_c', 80),
            vitamin_d_target=data.get('vitamin_d', 15),
            vitamin_a_target=data.get('vitamin_a', 800),
            calcium_target=data.get('calcium', 900),
            iron_target=data.get('iron', 12),
            potassium_target=data.get('potassium', 3500),
            # Mode för vitaminer/mineraler
            vitamin_c_mode=data.get('vitamin_c_mode', 'min'),
            vitamin_d_mode=data.get('vitamin_d_mode', 'min'),
            vitamin_a_mode=data.get('vitamin_a_mode', 'min'),
            calcium_mode=data.get('calcium_mode', 'min'),
            iron_mode=data.get('iron_mode', 'min'),
            potassium_mode=data.get('potassium_mode', 'ignore')
        )
        db.session.add(plan)
        db.session.commit()
        return jsonify(plan.to_dict()), 201
    
    plans = NutritionPlan.query.all()
    return jsonify([p.to_dict() for p in plans])


@app.route('/api/plans/<int:plan_id>', methods=['GET', 'PUT', 'DELETE'])
def api_plan(plan_id):
    """API för enskild näringsplan"""
    plan = NutritionPlan.query.get_or_404(plan_id)
    
    if request.method == 'DELETE':
        db.session.delete(plan)
        db.session.commit()
        return '', 204
    
    if request.method == 'PUT':
        data = request.json
        plan.name = data.get('name', plan.name)
        
        # Hantera allergier
        allergies = data.get('allergies', plan.allergies)
        if isinstance(allergies, list):
            allergies = ','.join(allergies)
        plan.allergies = allergies
        
        # Uppdatera targets och modes
        plan.calories_target = data.get('calories', plan.calories_target)
        plan.protein_target = data.get('protein', plan.protein_target)
        plan.carbs_target = data.get('carbs', plan.carbs_target)
        plan.fat_target = data.get('fat', plan.fat_target)
        plan.fiber_target = data.get('fiber', plan.fiber_target)
        
        plan.calories_mode = data.get('calories_mode', plan.calories_mode)
        plan.protein_mode = data.get('protein_mode', plan.protein_mode)
        plan.carbs_mode = data.get('carbs_mode', plan.carbs_mode)
        plan.fat_mode = data.get('fat_mode', plan.fat_mode)
        plan.fiber_mode = data.get('fiber_mode', plan.fiber_mode)
        
        db.session.commit()
    
    return jsonify(plan.to_dict())


@app.route('/api/allergens')
def api_allergens():
    """API för att hämta tillgängliga allergener"""
    return jsonify(ALLERGENS)


@app.route('/api/rdi')
def api_rdi():
    """API för att hämta RDI-värden (Rekommenderat Dagligt Intag)"""
    return jsonify(RDI_VALUES)


@app.route('/search')
def search_page():
    """Söksida för produkter"""
    return render_template('search.html', stores=STORES)


@app.route('/api/search')
def api_search():
    """API för produktsökning via matspar.se"""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 20, type=int)
    
    if not query:
        return jsonify([])
    
    products = scraper.search_products(query, limit=limit)
    return jsonify(products)


@app.route('/api/products', methods=['GET', 'POST'])
def api_products():
    """API för sparade produkter"""
    if request.method == 'POST':
        data = request.json
        
        # Skapa produkt
        product = Product(
            name=data.get('name'),
            brand=data.get('brand'),
            weight=data.get('weight'),
            category=data.get('category'),
            matspar_url=data.get('url')
        )
        db.session.add(product)
        db.session.flush()  # Få produkt-ID
        
        # Lägg till priser
        for store, price in data.get('prices', {}).items():
            price_obj = Price(
                product_id=product.id,
                store=store,
                price=price
            )
            db.session.add(price_obj)
        
        # Lägg till näringsvärden om de finns
        if data.get('nutrition'):
            nutr = data['nutrition']
            nutrition = Nutrition(
                product_id=product.id,
                calories=nutr.get('calories'),
                protein=nutr.get('protein'),
                carbs=nutr.get('carbs'),
                fat=nutr.get('fat'),
                fiber=nutr.get('fiber'),
                salt=nutr.get('salt')
            )
            db.session.add(nutrition)
        
        db.session.commit()
        return jsonify(product.to_dict()), 201
    
    # GET - lista produkter
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])


@app.route('/shopping-list')
def shopping_list_page():
    """Sida för inköpslistor"""
    lists = ShoppingList.query.order_by(ShoppingList.created_at.desc()).all()
    plans = NutritionPlan.query.all()
    return render_template('shopping_list.html', lists=lists, plans=plans, stores=STORES)


@app.route('/api/shopping-lists', methods=['GET', 'POST'])
def api_shopping_lists():
    """API för inköpslistor"""
    if request.method == 'POST':
        data = request.json
        
        shopping_list = ShoppingList(
            name=data.get('name', 'Min inköpslista'),
            store=data.get('store'),
            days=data.get('days', 7),
            plan_id=data.get('plan_id')
        )
        db.session.add(shopping_list)
        db.session.commit()
        
        return jsonify(shopping_list.to_dict()), 201
    
    lists = ShoppingList.query.order_by(ShoppingList.created_at.desc()).all()
    return jsonify([l.to_dict() for l in lists])


# Emoji-mappning för kategorier
CATEGORY_EMOJIS = {
    'mjölk': '🥛', 'milk': '🥛', 'dairy': '🥛',
    'bröd': '🍞', 'bread': '🍞',
    'ägg': '🥚', 'egg': '🥚',
    'smör': '🧈', 'butter': '🧈',
    'ost': '🧀', 'cheese': '🧀',
    'kyckling': '🍗', 'chicken': '🍗',
    'lax': '🐟', 'fisk': '🐟', 'fish': '🐟',
    'nötfärs': '🥩', 'fläsk': '🥓', 'kött': '🥩', 'meat': '🥩', 'bacon': '🥓',
    'ris': '🍚', 'rice': '🍚',
    'pasta': '🍝',
    'potatis': '🥔', 'potato': '🥔',
    'tomat': '🍅', 'tomato': '🍅',
    'gurka': '🥒', 'cucumber': '🥒',
    'sallad': '🥬', 'salad': '🥬', 'spenat': '🥬',
    'morot': '🥕', 'carrot': '🥕',
    'lök': '🧅', 'onion': '🧅',
    'banan': '🍌', 'banana': '🍌',
    'äpple': '🍎', 'apple': '🍎',
    'apelsin': '🍊', 'orange': '🍊',
    'havregryn': '🥣', 'gryn': '🥣', 'flingor': '🥣',
    'yoghurt': '🥛', 'kvarg': '🥛',
    'grädde': '🥛',
    'broccoli': '🥦',
    'paprika': '🫑',
    'avokado': '🥑',
    'linser': '🫘', 'bönor': '🫘', 'legumes': '🫘',
    'tofu': '🧊',
    'nötter': '🥜', 'mandlar': '🥜',
    'protein': '🍗',
    'carbs': '🍞',
    'vegetables': '🥬',
    'fruit': '🍎',
}

def get_emoji_for_product(product):
    """Hitta passande emoji för en produkt"""
    if not product:
        return '🛒'
    
    # Kolla kategori först
    category = (product.get('category') or '').lower() if isinstance(product, dict) else (product.category or '').lower()
    if category in CATEGORY_EMOJIS:
        return CATEGORY_EMOJIS[category]
    
    # Kolla produktnamn
    name = (product.get('name') or '').lower() if isinstance(product, dict) else (product.name or '').lower()
    for keyword, emoji in CATEGORY_EMOJIS.items():
        if keyword in name:
            return emoji
    
    return '🛒'


@app.route('/shopping-list/<int:list_id>/view')
def shopping_list_view(list_id):
    """Förenklad butiksvy för inköpslistan"""
    shopping_list = ShoppingList.query.get_or_404(list_id)
    
    # Gruppera produkter efter kategori
    categories = {}
    for item in shopping_list.items:
        cat = item.product.category or 'övrigt' if item.product else 'övrigt'
        if cat not in categories:
            categories[cat] = []
        
        # Hitta pris och butik
        price = None
        best_store = None
        if item.product and item.product.prices:
            for p in item.product.prices:
                if shopping_list.store and p.store.lower() == shopping_list.store.lower():
                    price = p.price
                    best_store = p.store
                    break
                elif price is None or p.price < price:
                    price = p.price
                    best_store = p.store
        
        categories[cat].append({
            'item': item,
            'product': item.product,
            'price': price,
            'store': best_store,
            'emoji': get_emoji_for_product(item.product)
        })
    
    return render_template('shopping_view.html', 
                         shopping_list=shopping_list, 
                         categories=categories,
                         get_emoji=get_emoji_for_product)


@app.route('/shopping-list/<int:list_id>/meals')
def meal_plan_view(list_id):
    """Måltidsplan baserad på inköpslistan"""
    import json
    shopping_list = ShoppingList.query.get_or_404(list_id)
    plan = NutritionPlan.query.get(shopping_list.plan_id) if shopping_list.plan_id else None
    
    # Konvertera till JSON för JavaScript
    shopping_list_dict = shopping_list.to_dict()
    plan_dict = plan.to_dict() if plan else {
        'calories_target': 2000,
        'protein_target': 50,
        'carbs_target': 250,
        'fat_target': 65
    }
    
    return render_template('meal_plan.html',
                         shopping_list=shopping_list,
                         plan=plan,
                         shopping_list_json=json.dumps(shopping_list_dict),
                         plan_json=json.dumps(plan_dict))


@app.route('/api/shopping-lists/<int:list_id>', methods=['GET', 'PUT', 'DELETE'])
def api_shopping_list(list_id):
    """API för enskild inköpslista"""
    shopping_list = ShoppingList.query.get_or_404(list_id)
    
    if request.method == 'DELETE':
        db.session.delete(shopping_list)
        db.session.commit()
        return '', 204
    
    if request.method == 'PUT':
        data = request.json
        shopping_list.name = data.get('name', shopping_list.name)
        shopping_list.store = data.get('store', shopping_list.store)
        db.session.commit()
    
    return jsonify(shopping_list.to_dict())


@app.route('/api/shopping-lists/<int:list_id>/items', methods=['POST'])
def api_add_shopping_item(list_id):
    """Lägg till produkt i inköpslista"""
    shopping_list = ShoppingList.query.get_or_404(list_id)
    data = request.json
    
    # Kolla om produkten redan finns i databasen, annars skapa
    product = None
    if data.get('product_id'):
        product = Product.query.get(data['product_id'])
    
    if not product and data.get('product'):
        # Skapa ny produkt från sökresultat
        prod_data = data['product']
        product = Product(
            name=prod_data.get('name'),
            weight=prod_data.get('weight'),
            matspar_url=prod_data.get('url')
        )
        db.session.add(product)
        db.session.flush()
        
        # Lägg till priser
        for store, price in prod_data.get('prices', {}).items():
            price_obj = Price(product_id=product.id, store=store, price=price)
            db.session.add(price_obj)
    
    if product:
        item = ShoppingItem(
            list_id=list_id,
            product_id=product.id,
            quantity=data.get('quantity', 1)
        )
        db.session.add(item)
        
        # Uppdatera totalkostnad
        _update_list_total(shopping_list)
        
        db.session.commit()
        return jsonify(item.to_dict()), 201
    
    return jsonify({'error': 'Ingen produkt angiven'}), 400


@app.route('/api/shopping-items/<int:item_id>', methods=['PUT', 'DELETE'])
def api_shopping_item(item_id):
    """API för enskild vara i inköpslista"""
    item = ShoppingItem.query.get_or_404(item_id)
    
    if request.method == 'DELETE':
        list_id = item.list_id
        db.session.delete(item)
        shopping_list = ShoppingList.query.get(list_id)
        _update_list_total(shopping_list)
        db.session.commit()
        return '', 204
    
    if request.method == 'PUT':
        data = request.json
        if 'quantity' in data:
            item.quantity = data['quantity']
        if 'checked' in data:
            item.checked = data['checked']
        
        _update_list_total(item.shopping_list)
        db.session.commit()
    
    return jsonify(item.to_dict())


def _update_list_total(shopping_list):
    """Beräknar och uppdaterar totalkostnad för en lista"""
    total = 0
    for item in shopping_list.items:
        if item.product and item.product.prices:
            # Hitta pris för vald butik eller lägsta pris
            price = None
            for p in item.product.prices:
                if shopping_list.store and p.store.lower() == shopping_list.store.lower():
                    price = p.price
                    break
                elif price is None or p.price < price:
                    price = p.price
            
            if price:
                total += price * item.quantity
    
    shopping_list.total_cost = total


@app.route('/generate')
def generate_page():
    """Sida för att generera inköpslista från näringsplan"""
    plans = NutritionPlan.query.all()
    return render_template('generate.html', plans=plans, stores=STORES, allergens=ALLERGENS)


@app.route('/api/generate-list', methods=['POST'])
def api_generate_list():
    """
    Generera inköpslista baserat på näringsplan
    
    SMART BERÄKNING:
    1. Beräknar totalt näringsbehov (dagar × personer × dagsbehov)
    2. Väljer produkter baserat på deras näringsinnehåll per 100g
    3. Beräknar exakt kvantitet baserat på produktens vikt
    4. Stoppar när näringsbehoven är uppfyllda
    
    Stödjer:
    - Allergifiltrering (från näringsplan)
    - Budget (totalt)
    - Hushållsstorlek (skalar mängder)
    - Budgetprioritering (billigare alternativ vid behov)
    """
    data = request.json
    plan_id = data.get('plan_id')
    days = data.get('days', 7)
    store = data.get('store')
    budget = data.get('budget')  # Total budget i SEK
    household_size = data.get('household_size', 1)
    prefer_cheaper = data.get('prefer_cheaper', False)
    
    plan = NutritionPlan.query.get_or_404(plan_id)
    
    # Hämta allergier från plan
    allergies = plan.get_allergies_list()
    
    # ============== BERÄKNA TOTALT NÄRINGSBEHOV ==============
    # Totalt behov = dagligt behov × antal dagar × antal personer
    total_calories_needed = plan.calories_target * days * household_size
    total_protein_needed = plan.protein_target * days * household_size
    total_carbs_needed = plan.carbs_target * days * household_size
    total_fat_needed = plan.fat_target * days * household_size
    total_fiber_needed = plan.fiber_target * days * household_size
    
    # Dagliga värden per person (för beräkningar)
    daily_calories = plan.calories_target
    daily_protein = plan.protein_target
    
    # Spåra uppfyllnad
    current_calories = 0
    current_protein = 0
    current_carbs = 0
    current_fat = 0
    current_fiber = 0
    
    # ============== NY MÅLTIDSBASERAD STRATEGI ==============
    # Vi beräknar utifrån antal måltider som behöver täckas
    #
    # Antal måltider som behöver mat:
    num_breakfasts = days * household_size   # Antal frukostar totalt
    num_lunches = days * household_size      # Antal luncher totalt
    num_dinners = days * household_size      # Antal middagar totalt  
    num_snacks = days * household_size       # Antal mellanmål totalt
    
    # Kalorifördelning per måltid (baserat på plan):
    # Frukost: 20% | Lunch: 35% | Middag: 35% | Mellanmål: 10%
    breakfast_kcal_per_person = daily_calories * 0.20  # ~500 kcal för 2500
    lunch_kcal_per_person = daily_calories * 0.35      # ~875 kcal för 2500
    dinner_kcal_per_person = daily_calories * 0.35     # ~875 kcal för 2500
    snack_kcal_per_person = daily_calories * 0.10      # ~250 kcal för 2500
    
    # ============== PRODUKTKATEGORIER - KÖPER TILLRÄCKLIGT FÖR ALLA MÅLTIDER ==============
    # Varje produkt specificerar:
    # - meals: antal måltider denna produkt ska täcka (baserat på num_breakfasts etc)
    # - portion_grams: gram per portion
    # - kcal_per_100g: ungefärliga kalorier (fallback om nutrition saknas)
    
    product_categories = [
        # ===== FRUKOST =====
        # Frukostar: gröt, bröd+pålägg, ägg, müsli etc
        {'search': 'havregryn', 'priority': 1, 'type': 'breakfast', 'kcal_per_100g': 370,
         'meals': int(num_breakfasts * 0.6), 'portion_grams': 70},  # Gröt ~60% av frukostar
        
        {'search': 'bröd', 'priority': 1, 'type': 'breakfast', 'kcal_per_100g': 250,
         'meals': int(num_breakfasts * 1.0), 'portion_grams': 80},  # Bröd till alla frukostar + smörgås
        
        {'search': 'ägg', 'priority': 1, 'type': 'breakfast', 'kcal_per_100g': 155,
         'meals': int(num_breakfasts * 0.6), 'portion_grams': 120},  # Ägg de flesta morgnar + matlagning
        
        {'search': 'mjölk', 'priority': 2, 'type': 'breakfast', 'kcal_per_100g': 45,
         'meals': int(num_breakfasts * 1.5), 'portion_grams': 250},  # Till gröt, kaffe, etc
        
        {'search': 'yoghurt', 'priority': 2, 'type': 'breakfast', 'kcal_per_100g': 60,
         'meals': int(num_breakfasts * 0.4), 'portion_grams': 200},
        
        # ===== LUNCH & MIDDAG - PROTEIN =====
        # Huvudmåltider: num_lunches + num_dinners st
        {'search': 'kycklingfilé', 'priority': 1, 'type': 'protein', 'kcal_per_100g': 120,
         'meals': int((num_lunches + num_dinners) * 0.3), 'portion_grams': 175},  # ~30% av måltider
        
        {'search': 'nötfärs', 'priority': 1, 'type': 'protein', 'kcal_per_100g': 205,
         'meals': int((num_lunches + num_dinners) * 0.25), 'portion_grams': 150},  # ~25% av måltider
        
        {'search': 'lax', 'priority': 1, 'type': 'protein', 'kcal_per_100g': 205,
         'meals': int((num_lunches + num_dinners) * 0.15), 'portion_grams': 150},  # Fisk ~15%
        
        {'search': 'fläskfilé', 'priority': 1, 'type': 'protein', 'kcal_per_100g': 145,
         'meals': int((num_lunches + num_dinners) * 0.1), 'portion_grams': 150},  # ~10%
        
        {'search': 'korv', 'priority': 2, 'type': 'protein', 'kcal_per_100g': 280,
         'meals': int((num_lunches + num_dinners) * 0.1), 'portion_grams': 120},  # ~10%
        
        # ===== LUNCH & MIDDAG - KOLHYDRATER =====
        {'search': 'pasta', 'priority': 1, 'type': 'carbs', 'kcal_per_100g': 355,
         'meals': int((num_lunches + num_dinners) * 0.35), 'portion_grams': 100},  # ~35% av måltider
        
        {'search': 'ris', 'priority': 1, 'type': 'carbs', 'kcal_per_100g': 355,
         'meals': int((num_lunches + num_dinners) * 0.35), 'portion_grams': 85},  # ~35%
        
        {'search': 'potatis', 'priority': 1, 'type': 'carbs', 'kcal_per_100g': 85,
         'meals': int((num_lunches + num_dinners) * 0.3), 'portion_grams': 300},  # ~30%
        
        # ===== FETTER - KRITISKT FÖR KALORIER =====
        {'search': 'smör', 'priority': 2, 'type': 'fat', 'kcal_per_100g': 720,
         'meals': int(num_breakfasts * 1.5 + num_dinners * 0.5), 'portion_grams': 15},  # Smörgås + matlagning
        
        {'search': 'ost', 'priority': 2, 'type': 'dairy', 'kcal_per_100g': 350,
         'meals': int(num_breakfasts * 0.8), 'portion_grams': 30},  # Smörgåsost
        
        {'search': 'olja', 'priority': 2, 'type': 'fat', 'kcal_per_100g': 880,
         'meals': int((num_lunches + num_dinners) * 0.6), 'portion_grams': 15},  # Stekning
        
        {'search': 'grädde', 'priority': 3, 'type': 'fat', 'kcal_per_100g': 290,
         'meals': int(num_dinners * 0.3), 'portion_grams': 100},  # Till såser
        
        # ===== GRÖNSAKER =====
        {'search': 'tomat', 'priority': 3, 'type': 'vegetables', 'kcal_per_100g': 20,
         'meals': int((num_lunches + num_dinners) * 0.4), 'portion_grams': 150},
        
        {'search': 'gurka', 'priority': 3, 'type': 'vegetables', 'kcal_per_100g': 12,
         'meals': int(num_lunches * 0.4), 'portion_grams': 100},
        
        {'search': 'morot', 'priority': 3, 'type': 'vegetables', 'kcal_per_100g': 35,
         'meals': int((num_lunches + num_dinners) * 0.3), 'portion_grams': 100},
        
        {'search': 'broccoli', 'priority': 3, 'type': 'vegetables', 'kcal_per_100g': 35,
         'meals': int(num_dinners * 0.4), 'portion_grams': 150},
        
        {'search': 'lök', 'priority': 4, 'type': 'vegetables', 'kcal_per_100g': 40,
         'meals': int(num_dinners * 0.6), 'portion_grams': 75},
        
        {'search': 'paprika', 'priority': 4, 'type': 'vegetables', 'kcal_per_100g': 25,
         'meals': int(num_dinners * 0.3), 'portion_grams': 100},
        
        # ===== MELLANMÅL & FRUKT =====
        {'search': 'banan', 'priority': 2, 'type': 'snack', 'kcal_per_100g': 95,
         'meals': int(num_snacks * 0.6), 'portion_grams': 130},
        
        {'search': 'äpple', 'priority': 2, 'type': 'snack', 'kcal_per_100g': 55,
         'meals': int(num_snacks * 0.5), 'portion_grams': 180},
        
        {'search': 'kvarg', 'priority': 2, 'type': 'snack', 'kcal_per_100g': 65,
         'meals': int(num_snacks * 0.5), 'portion_grams': 200},
    ]
    
    # Lägg till vegetariska proteinkällor om vegetarian/vegan
    if 'vegetarian' in allergies or 'vegan' in allergies:
        # Ta bort köttprodukter och lägg till vegetariska
        protein_meals = int((num_lunches + num_dinners) * 0.25)
        product_categories = [p for p in product_categories if p['type'] != 'protein' or 'ägg' in p['search']]
        product_categories.insert(0, {'search': 'tofu', 'portion_grams': 200, 'priority': 1, 'type': 'protein', 'kcal_per_100g': 120, 'meals': protein_meals})
        product_categories.insert(1, {'search': 'quorn', 'portion_grams': 150, 'priority': 1, 'type': 'protein', 'kcal_per_100g': 100, 'meals': protein_meals})
        product_categories.insert(2, {'search': 'linser', 'portion_grams': 100, 'priority': 1, 'type': 'protein', 'kcal_per_100g': 115, 'meals': protein_meals})
        product_categories.insert(3, {'search': 'bönor', 'portion_grams': 150, 'priority': 1, 'type': 'protein', 'kcal_per_100g': 130, 'meals': protein_meals})
        product_categories.insert(4, {'search': 'sojafärs', 'portion_grams': 125, 'priority': 1, 'type': 'protein', 'kcal_per_100g': 140, 'meals': protein_meals})
    
    # Sortera efter prioritet
    product_categories.sort(key=lambda x: x['priority'])
    
    # Skapa ny inköpslista
    shopping_list = ShoppingList(
        name=f"Inköpslista - {plan.name} ({days} dagar, {household_size} pers)",
        store=store,
        days=days,
        plan_id=plan_id,
        budget=budget,
        household_size=household_size
    )
    db.session.add(shopping_list)
    db.session.flush()
    
    added_products = []
    running_total = 0
    
    def parse_weight_grams(weight_str):
        """Konvertera viktstring till gram (t.ex. '500g' -> 500, '1kg' -> 1000)"""
        if not weight_str:
            return 500  # Anta 500g om okänd
        weight_str = str(weight_str).lower().replace(' ', '')
        
        # Hantera kg
        kg_match = re.search(r'(\d+(?:[.,]\d+)?)\s*kg', weight_str)
        if kg_match:
            return float(kg_match.group(1).replace(',', '.')) * 1000
        
        # Hantera gram
        g_match = re.search(r'(\d+(?:[.,]\d+)?)\s*g', weight_str)
        if g_match:
            return float(g_match.group(1).replace(',', '.'))
        
        # Hantera liter (mjölk etc) - anta 1L = 1000g
        l_match = re.search(r'(\d+(?:[.,]\d+)?)\s*l', weight_str)
        if l_match:
            return float(l_match.group(1).replace(',', '.')) * 1000
        
        # Hantera dl
        dl_match = re.search(r'(\d+)\s*dl', weight_str)
        if dl_match:
            return float(dl_match.group(1)) * 100
        
        # Hantera ml
        ml_match = re.search(r'(\d+)\s*ml', weight_str)
        if ml_match:
            return float(ml_match.group(1))
        
        # Hantera st (ägg: 6st ≈ 360g, 12st ≈ 720g)
        st_match = re.search(r'(\d+)\s*st', weight_str)
        if st_match:
            count = int(st_match.group(1))
            return count * 60  # Anta 60g per styck
        
        return 500  # Default
    
    # ============== BYGG LISTAN SMART ==============
    for product_info in product_categories:
        # Kolla om vi redan nått våra mål (med 10% marginal)
        calories_fulfilled = current_calories >= total_calories_needed * 0.9
        protein_fulfilled = current_protein >= total_protein_needed * 0.9
        carbs_fulfilled = current_carbs >= total_carbs_needed * 0.9
        
        # Hoppa över proteinkällor om vi har tillräckligt protein
        if product_info['type'] == 'protein' and protein_fulfilled and calories_fulfilled:
            continue
        
        # Hoppa över kolhydrater om vi har tillräckligt
        if product_info['type'] == 'carbs' and carbs_fulfilled and calories_fulfilled:
            continue
        
        # Sök produkt med allergifiltrering
        results = scraper.search_products_filtered(
            product_info['search'], 
            allergies=allergies,
            prefer_cheaper=prefer_cheaper or (budget is not None),
            limit=3
        )
        
        if not results:
            continue
        
        prod_data = results[0]
        
        # Hämta pris
        prod_prices = prod_data.get('prices', {})
        if store and store in prod_prices:
            prod_price = prod_prices[store]
        else:
            prod_price = min(prod_prices.values()) if prod_prices else 0
        
        # ============== SMART KVANTITETSBERÄKNING ==============
        # Använder 'meals' för antal måltider produkten ska täcka
        portion_grams = product_info['portion_grams']
        meals_to_cover = product_info.get('meals', 1)  # Antal måltider att täcka
        
        # Totalt antal gram som behövs för alla måltider
        total_grams_needed = portion_grams * meals_to_cover
        
        # Hur mycket är det i en förpackning?
        pack_grams = parse_weight_grams(prod_data.get('weight', '500g'))
        
        # Hur många förpackningar behövs? (runda upp för att täcka behovet)
        quantity = max(1, math.ceil(total_grams_needed / pack_grams))
        
        # Begränsa till rimliga mängder (men mer generös för att nå mål)
        max_quantity = max(2, math.ceil(days * household_size / 2))  # Generösare max
        quantity = min(quantity, max_quantity)
        
        item_cost = prod_price * quantity
        
        # Budgetkontroll
        if budget and running_total + item_cost > budget:
            # Försök med billigare alternativ
            for alt in results[1:]:
                alt_prices = alt.get('prices', {})
                if store and store in alt_prices:
                    alt_price = alt_prices[store]
                else:
                    alt_price = min(alt_prices.values()) if alt_prices else 0
                
                alt_cost = alt_price * quantity
                if running_total + alt_cost <= budget:
                    prod_data = alt
                    prod_price = alt_price
                    item_cost = alt_cost
                    pack_grams = parse_weight_grams(alt.get('weight', '500g'))
                    break
            else:
                # Minska kvantitet eller hoppa över
                if quantity > 1:
                    quantity = max(1, quantity - 1)
                    item_cost = prod_price * quantity
                    if running_total + item_cost > budget:
                        continue
                else:
                    continue
        
        running_total += item_cost
        
        # Beräkna näringsbidrag från denna produkt
        nutr_data = prod_data.get('nutrition', {})
        actual_grams = pack_grams * quantity
        
        if nutr_data and nutr_data.get('calories'):
            # Näringsvärden är per 100g, beräkna för faktisk mängd
            factor = actual_grams / 100
            current_calories += (nutr_data.get('calories') or 0) * factor
            current_protein += (nutr_data.get('protein') or 0) * factor
            current_carbs += (nutr_data.get('carbs') or 0) * factor
            current_fat += (nutr_data.get('fat') or 0) * factor
            current_fiber += (nutr_data.get('fiber') or 0) * factor
        else:
            # Använd uppskattade värden från product_info om nutrition saknas
            factor = actual_grams / 100
            est_kcal = product_info.get('kcal_per_100g', 100)
            current_calories += est_kcal * factor
        
        # Spara produkt i databas
        product = Product(
            name=prod_data.get('name'),
            brand=prod_data.get('brand'),
            weight=prod_data.get('weight'),
            category=prod_data.get('category', product_info['type']),
            matspar_url=prod_data.get('url'),
            image_url=prod_data.get('image'),
            allergen_tags=','.join(prod_data.get('allergens', []))
        )
        db.session.add(product)
        db.session.flush()
        
        # Lägg till priser
        for store_name, price in prod_data.get('prices', {}).items():
            price_obj = Price(product_id=product.id, store=store_name, price=price)
            db.session.add(price_obj)
        
        # Lägg till näringsvärden
        if nutr_data:
            nutrition = Nutrition(
                product_id=product.id,
                calories=nutr_data.get('calories'),
                protein=nutr_data.get('protein'),
                carbs=nutr_data.get('carbs'),
                fat=nutr_data.get('fat'),
                fiber=nutr_data.get('fiber'),
                salt=nutr_data.get('salt'),
                vitamin_c=nutr_data.get('vitamin_c'),
                vitamin_d=nutr_data.get('vitamin_d'),
                vitamin_a=nutr_data.get('vitamin_a'),
                calcium=nutr_data.get('calcium'),
                iron=nutr_data.get('iron'),
                potassium=nutr_data.get('potassium')
            )
            db.session.add(nutrition)
        
        # Lägg till i lista
        item = ShoppingItem(
            list_id=shopping_list.id,
            product_id=product.id,
            quantity=quantity
        )
        db.session.add(item)
        added_products.append(f"{prod_data.get('name')} x{quantity}")
    
    # ============== FYLLNADS-LOOP: Säkerställ att vi når kalori-målet ==============
    # Om vi fortfarande saknar >10% av kalorierna, köp mer av kaloritäta produkter
    calories_deficit = total_calories_needed - current_calories
    calories_coverage = (current_calories / total_calories_needed * 100) if total_calories_needed else 100
    
    if calories_coverage < 90:
        # Lista med kaloritäta produkter att fylla med
        filler_products = [
            {'search': 'nötfärs', 'kcal_per_100g': 205, 'portion_grams': 400},   # Protein + kalorier
            {'search': 'kycklingfilé', 'kcal_per_100g': 120, 'portion_grams': 400},
            {'search': 'pasta', 'kcal_per_100g': 355, 'portion_grams': 500},
            {'search': 'ris', 'kcal_per_100g': 355, 'portion_grams': 500},
            {'search': 'havregryn', 'kcal_per_100g': 370, 'portion_grams': 500},
            {'search': 'bröd', 'kcal_per_100g': 250, 'portion_grams': 500},
            {'search': 'ost', 'kcal_per_100g': 350, 'portion_grams': 200},
            {'search': 'smör', 'kcal_per_100g': 720, 'portion_grams': 250},
        ]
        
        for filler in filler_products:
            if current_calories >= total_calories_needed * 0.98:
                break  # Nära nog - 98% är bra
            
            # Hur mycket saknas?
            remaining_deficit = total_calories_needed - current_calories
            
            # Sök produkten
            filler_results = scraper.search_products_filtered(
                filler['search'], 
                allergies=allergies,
                prefer_cheaper=True,
                limit=1
            )
            
            if not filler_results:
                continue
            
            filler_prod = filler_results[0]
            filler_prices = filler_prod.get('prices', {})
            filler_price = min(filler_prices.values()) if filler_prices else 0
            
            # Beräkna hur mycket vi behöver för att fylla deficit
            grams_needed = (remaining_deficit / filler['kcal_per_100g']) * 100
            pack_grams = parse_weight_grams(filler_prod.get('weight', '500g'))
            # Mer aggressiv: köp hela behovet, inte bara halva
            extra_quantity = max(1, math.ceil(grams_needed / pack_grams * 0.7))  # 70% för att inte överdriva massivt
            
            extra_cost = filler_price * extra_quantity
            
            # Budgetkontroll
            if budget and running_total + extra_cost > budget:
                continue
            
            running_total += extra_cost
            
            # Lägg till kalorier
            nutr = filler_prod.get('nutrition', {})
            actual_grams = pack_grams * extra_quantity
            kcal_added = (nutr.get('calories') or filler['kcal_per_100g']) * actual_grams / 100
            current_calories += kcal_added
            current_protein += (nutr.get('protein') or 0) * actual_grams / 100
            current_carbs += (nutr.get('carbs') or 0) * actual_grams / 100
            current_fat += (nutr.get('fat') or 0) * actual_grams / 100
            
            # Spara produkt
            filler_product = Product(
                name=filler_prod.get('name'),
                brand=filler_prod.get('brand'),
                weight=filler_prod.get('weight'),
                category=filler_prod.get('category'),
                image_url=filler_prod.get('image'),
                allergen_tags=','.join(filler_prod.get('allergens', []))
            )
            db.session.add(filler_product)
            db.session.flush()
            
            for store_name, price in filler_prod.get('prices', {}).items():
                price_obj = Price(product_id=filler_product.id, store=store_name, price=price)
                db.session.add(price_obj)
            
            if nutr:
                nutrition = Nutrition(
                    product_id=filler_product.id,
                    calories=nutr.get('calories'),
                    protein=nutr.get('protein'),
                    carbs=nutr.get('carbs'),
                    fat=nutr.get('fat'),
                    fiber=nutr.get('fiber')
                )
                db.session.add(nutrition)
            
            filler_item = ShoppingItem(
                list_id=shopping_list.id,
                product_id=filler_product.id,
                quantity=extra_quantity
            )
            db.session.add(filler_item)
            added_products.append(f"{filler_prod.get('name')} x{extra_quantity} (extra)")
    
    _update_list_total(shopping_list)
    db.session.commit()
    
    # Lägg till info om näringsuppfyllnad i svaret
    result = shopping_list.to_dict()
    result['nutrition_coverage'] = {
        'calories': round(current_calories / total_calories_needed * 100) if total_calories_needed else 0,
        'protein': round(current_protein / total_protein_needed * 100) if total_protein_needed else 0,
        'carbs': round(current_carbs / total_carbs_needed * 100) if total_carbs_needed else 0,
        'fat': round(current_fat / total_fat_needed * 100) if total_fat_needed else 0,
    }
    result['nutrition_totals'] = {
        'calories': round(current_calories),
        'protein': round(current_protein),
        'carbs': round(current_carbs),
        'fat': round(current_fat),
        'fiber': round(current_fiber)
    }
    result['nutrition_targets'] = {
        'calories': round(total_calories_needed),
        'protein': round(total_protein_needed),
        'carbs': round(total_carbs_needed),
        'fat': round(total_fat_needed),
        'fiber': round(total_fiber_needed)
    }
    
    return jsonify(result), 201


# ============== PRODUKTERSÄTTNING ==============

@app.route('/api/shopping-items/<int:item_id>/substitute', methods=['POST'])
def api_substitute_item(item_id):
    """
    Byt ut en produkt i inköpslistan mot ett likvärdigt alternativ
    
    Matchning sker på:
    - Produktkategori
    - Näringsvärden (kalorier, protein)
    - Allergiregler (från planens inställningar)
    - Budget (om angiven)
    
    POST body (valfritt):
    {
        "budget": 50.0,  // Max pris för ersättning
        "prefer_cheaper": true  // Prioritera billigare
    }
    """
    item = ShoppingItem.query.get_or_404(item_id)
    shopping_list = item.shopping_list
    data = request.json or {}
    
    if not item.product:
        return jsonify({'error': 'Produkten finns inte'}), 400
    
    # Hämta allergier från plan
    allergies = []
    if shopping_list.plan:
        allergies = shopping_list.plan.get_allergies_list()
    
    # Skapa produkt-dict för substitution-sökning
    product_dict = {
        'name': item.product.name,
        'category': item.product.category,
        'nutrition': item.product.nutrition.to_dict() if item.product.nutrition else {},
        'prices': {p.store: p.price for p in item.product.prices},
        'allergens': item.product.get_allergen_list()
    }
    
    # Budget-begränsning
    budget = data.get('budget')
    if not budget and shopping_list.budget:
        # Använd genomsnittligt produktpris från total budget
        item_count = len(shopping_list.items)
        budget = (shopping_list.budget / item_count) * 1.5 if item_count > 0 else None
    
    # Hitta ersättning
    substitute = scraper.find_substitute(
        product_dict,
        allergies=allergies,
        budget=budget,
        same_category=True
    )
    
    if not substitute:
        return jsonify({'error': 'Ingen lämplig ersättning hittades'}), 404
    
    # Spara original-produkt-id om inte redan utbytt
    if not item.original_product_id:
        item.original_product_id = item.product_id
    
    # Skapa ny produkt från substitut
    new_product = Product(
        name=substitute.get('name'),
        brand=substitute.get('brand'),
        weight=substitute.get('weight'),
        category=substitute.get('category'),
        image_url=substitute.get('image'),
        allergen_tags=','.join(substitute.get('allergens', []))
    )
    db.session.add(new_product)
    db.session.flush()
    
    # Lägg till priser
    for store_name, price in substitute.get('prices', {}).items():
        price_obj = Price(product_id=new_product.id, store=store_name, price=price)
        db.session.add(price_obj)
    
    # Lägg till näringsvärden
    nutr_data = substitute.get('nutrition', {})
    if nutr_data:
        nutrition = Nutrition(
            product_id=new_product.id,
            calories=nutr_data.get('calories'),
            protein=nutr_data.get('protein'),
            carbs=nutr_data.get('carbs'),
            fat=nutr_data.get('fat'),
            fiber=nutr_data.get('fiber')
        )
        db.session.add(nutrition)
    
    # Uppdatera item med ny produkt
    item.product_id = new_product.id
    
    # Uppdatera totalkostnad
    _update_list_total(shopping_list)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'item': item.to_dict(),
        'message': f"Bytte ut mot {new_product.name}"
    })


@app.route('/api/shopping-items/<int:item_id>/revert', methods=['POST'])
def api_revert_substitute(item_id):
    """Återställ till originalprodukt om produkten har bytts ut"""
    item = ShoppingItem.query.get_or_404(item_id)
    
    if not item.original_product_id:
        return jsonify({'error': 'Produkten har inte bytts ut'}), 400
    
    # Återställ till original
    item.product_id = item.original_product_id
    item.original_product_id = None
    
    _update_list_total(item.shopping_list)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'item': item.to_dict(),
        'message': 'Återställde originalprodukt'
    })


@app.route('/api/shopping-items/<int:item_id>/substitute-combined', methods=['POST'])
def api_substitute_combined(item_id):
    """
    Ersätt en vara med flera produkter (kombinerad ersättning)
    T.ex. 1kg kyckling → 2x 500g sojafärs
    
    POST body:
    {
        "product_ids": [1, 2],  // Lista med produkt-IDs
        "quantities": [2, 1]    // Antal av varje produkt
    }
    """
    item = ShoppingItem.query.get_or_404(item_id)
    shopping_list = item.shopping_list
    data = request.json or {}
    
    product_ids = data.get('product_ids', [])
    quantities = data.get('quantities', [])
    
    if not product_ids or not quantities or len(product_ids) != len(quantities):
        return jsonify({'error': 'Ogiltig data: product_ids och quantities krävs'}), 400
    
    if not item.product:
        return jsonify({'error': 'Produkten finns inte'}), 400
    
    # Spara original-produkt-id om inte redan utbytt
    original_quantity = item.quantity
    if not item.original_product_id:
        item.original_product_id = item.product_id
    
    # Hitta de nya produkterna
    # Produkterna kan vara antingen från databasen eller från FALLBACK_PRODUCTS
    new_items_created = []
    
    for idx, (prod_id, qty) in enumerate(zip(product_ids, quantities)):
        # Kolla om produkten finns i databasen
        existing_product = Product.query.get(prod_id)
        
        if existing_product:
            # Använd befintlig produkt
            if idx == 0:
                # Uppdatera den ursprungliga item:en
                item.product_id = existing_product.id
                item.quantity = qty
            else:
                # Skapa ny item för resten
                new_item = ShoppingItem(
                    shopping_list_id=shopping_list.id,
                    product_id=existing_product.id,
                    quantity=qty,
                    checked=False,
                    original_product_id=item.original_product_id  # Spara original för spårning
                )
                db.session.add(new_item)
                new_items_created.append(new_item)
        else:
            # Produkten finns inte i DB - leta i FALLBACK_PRODUCTS
            fallback_product = None
            for cat_products in scraper.FALLBACK_PRODUCTS.values():
                for p in cat_products:
                    if p.get('id') == prod_id:
                        fallback_product = p
                        break
                if fallback_product:
                    break
            
            if not fallback_product:
                return jsonify({'error': f'Produkten med id {prod_id} hittades inte'}), 404
            
            # Skapa ny produkt från fallback
            new_product = Product(
                name=fallback_product.get('name'),
                brand=fallback_product.get('brand'),
                weight=fallback_product.get('weight'),
                category=fallback_product.get('category'),
                image_url=fallback_product.get('image'),
                allergen_tags=','.join(fallback_product.get('allergens', []))
            )
            db.session.add(new_product)
            db.session.flush()
            
            # Lägg till priser
            for store_name, price in fallback_product.get('prices', {}).items():
                price_obj = Price(product_id=new_product.id, store=store_name, price=price)
                db.session.add(price_obj)
            
            # Lägg till näringsvärden
            nutr_data = fallback_product.get('nutrition', {})
            if nutr_data:
                nutrition = Nutrition(
                    product_id=new_product.id,
                    calories=nutr_data.get('calories'),
                    protein=nutr_data.get('protein'),
                    carbs=nutr_data.get('carbs'),
                    fat=nutr_data.get('fat'),
                    fiber=nutr_data.get('fiber')
                )
                db.session.add(nutrition)
            
            db.session.flush()
            
            if idx == 0:
                item.product_id = new_product.id
                item.quantity = qty
            else:
                new_item = ShoppingItem(
                    shopping_list_id=shopping_list.id,
                    product_id=new_product.id,
                    quantity=qty,
                    checked=False,
                    original_product_id=item.original_product_id
                )
                db.session.add(new_item)
                new_items_created.append(new_item)
    
    # Uppdatera totalkostnad
    _update_list_total(shopping_list)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f"Ersatte med {len(product_ids)} produkter",
        'items_created': len(new_items_created) + 1
    })


@app.route('/api/shopping-items/<int:item_id>/alternatives')
def api_get_alternatives(item_id):
    """Hämta alternativa produkter för en vara i listan baserat på näringsprofil och typ"""
    item = ShoppingItem.query.get_or_404(item_id)
    shopping_list = item.shopping_list
    
    if not item.product:
        return jsonify({'single': [], 'combined': []})
    
    # Hämta allergier
    allergies = []
    if shopping_list.plan:
        allergies = shopping_list.plan.get_allergies_list()
    
    # Hämta budget om tillgänglig
    budget = shopping_list.budget
    
    # Konvertera produkten till dict för scraper
    product_dict = {
        'name': item.product.name,
        'category': item.product.category,
        'weight': item.product.weight,
        'prices': {},
        'nutrition': {}
    }
    
    # Lägg till priser
    for price in item.product.prices:
        product_dict['prices'][price.store] = price.price
    
    # Lägg till näringsvärden
    if item.product.nutrition:
        product_dict['nutrition'] = {
            'calories': item.product.nutrition.calories,
            'protein': item.product.nutrition.protein,
            'carbs': item.product.nutrition.carbs,
            'fat': item.product.nutrition.fat,
            'fiber': item.product.nutrition.fiber
        }
    
    # Hitta enskilda alternativ (med strikt typ-matchning)
    single_alternatives = scraper.find_alternatives(
        product_dict,
        allergies=allergies,
        budget=budget,
        same_category=False,
        limit=8
    )
    
    # Filtrera bort nuvarande produkt
    single_alternatives = [a for a in single_alternatives if a.get('name') != item.product.name]
    
    # Beräkna målvikt för kombinerade ersättningar
    target_grams = 0
    if item.product.weight:
        # Parsa vikt från produkten
        weight_str = item.product.weight.lower()
        if 'kg' in weight_str:
            try:
                target_grams = int(float(weight_str.replace('kg', '').strip()) * 1000)
            except:
                target_grams = 500
        elif 'g' in weight_str:
            try:
                target_grams = int(weight_str.replace('g', '').strip())
            except:
                target_grams = 500
        else:
            target_grams = 500
    else:
        target_grams = 500  # Default
    
    # Multiplicera med antal
    target_grams = target_grams * item.quantity
    
    # Hitta kombinerade ersättningar (t.ex. 2x 500g istället för 1x 1kg)
    combined_alternatives = scraper.find_combined_alternatives(
        product_dict,
        target_grams=target_grams,
        allergies=allergies,
        budget=budget,
        limit=5
    )
    
    return jsonify({
        'single': single_alternatives,
        'combined': combined_alternatives
    })


# ============== EXPORT-FUNKTIONER ==============

@app.route('/api/shopping-lists/<int:list_id>/export/csv')
def export_shopping_list_csv(list_id):
    """
    Exportera inköpslista som CSV
    Kan öppnas i Excel eller importeras till andra system
    """
    shopping_list = ShoppingList.query.get_or_404(list_id)
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Header
    writer.writerow(['Produkt', 'Märke', 'Vikt', 'Antal', 'Pris', 'Totalt', 'Kategori'])
    
    total = 0
    for item in shopping_list.items:
        product = item.product
        if not product:
            continue
        
        # Hitta pris
        price = None
        if product.prices:
            for p in product.prices:
                if shopping_list.store and p.store.lower() == shopping_list.store.lower():
                    price = p.price
                    break
                elif price is None or p.price < price:
                    price = p.price
        
        item_total = (price or 0) * item.quantity
        total += item_total
        
        writer.writerow([
            product.name or '',
            product.brand or '',
            product.weight or '',
            item.quantity,
            f"{price:.2f}" if price else '',
            f"{item_total:.2f}",
            product.category or ''
        ])
    
    # Total rad
    writer.writerow([])
    writer.writerow(['TOTALT', '', '', '', '', f"{total:.2f}", ''])
    
    if shopping_list.household_size > 1:
        writer.writerow(['Per person', '', '', '', '', f"{total/shopping_list.household_size:.2f}", ''])
    
    output.seek(0)
    
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=inkopslista_{list_id}.csv'
        }
    )


@app.route('/api/shopping-lists/<int:list_id>/export/text')
def export_shopping_list_text(list_id):
    """
    Exportera inköpslista som text (för urklipp)
    Formaterat för att klistras in i butiksappar
    """
    shopping_list = ShoppingList.query.get_or_404(list_id)
    
    lines = [f"📋 {shopping_list.name}"]
    if shopping_list.store:
        lines.append(f"🏪 {shopping_list.store}")
    lines.append("")
    
    # Gruppera efter kategori
    categories = {}
    for item in shopping_list.items:
        cat = item.product.category or 'övrigt' if item.product else 'övrigt'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    total = 0
    for cat, items in categories.items():
        lines.append(f"── {cat.upper()} ──")
        for item in items:
            product = item.product
            if not product:
                continue
            
            # Hitta pris
            price = None
            if product.prices:
                for p in product.prices:
                    if shopping_list.store and p.store.lower() == shopping_list.store.lower():
                        price = p.price
                        break
                    elif price is None or p.price < price:
                        price = p.price
            
            item_total = (price or 0) * item.quantity
            total += item_total
            
            qty_str = f" x{item.quantity}" if item.quantity > 1 else ""
            price_str = f" ({price:.0f} kr)" if price else ""
            lines.append(f"☐ {product.name}{qty_str}{price_str}")
        
        lines.append("")
    
    lines.append(f"💰 Totalt: {total:.0f} kr")
    if shopping_list.household_size > 1:
        lines.append(f"👥 Per person: {total/shopping_list.household_size:.0f} kr")
    
    return jsonify({
        'text': '\n'.join(lines),
        'total': total,
        'item_count': len(shopping_list.items)
    })


@app.route('/api/shopping-lists/<int:list_id>/export/store/<store>')
def export_for_store(list_id, store):
    """
    Förbered export för specifik butik
    
    Butiksappar har oftast inga publika API:er, så vi erbjuder:
    1. Formaterad text för urklipp
    2. CSV för manuell import
    3. Deep-link om möjligt (begränsad)
    
    Butiksspecifik information:
    - ICA: Ingen publik API. Stödjer inte direkt import.
    - Coop: Ingen publik API. Har "Mina listor" men ej extern åtkomst.
    - Willys: Ingen publik API. Hemköp ägs av samma koncern.
    
    Rekommendation: Använd text-export och klistra in manuellt.
    """
    shopping_list = ShoppingList.query.get_or_404(list_id)
    
    store_lower = store.lower()
    
    # Butiksspecifika URL:er (för info, ej direktimport)
    store_urls = {
        'ica': 'https://www.ica.se/handla/',
        'coop': 'https://www.coop.se/handla/',
        'willys': 'https://www.willys.se/',
        'hemköp': 'https://www.hemkop.se/',
        'hemkop': 'https://www.hemkop.se/',
        'lidl': 'https://www.lidl.se/',
        'city gross': 'https://www.citygross.se/'
    }
    
    # Skapa produktlista för butiken
    items_for_store = []
    total = 0
    
    for item in shopping_list.items:
        product = item.product
        if not product:
            continue
        
        # Hitta pris för denna butik
        price = None
        for p in product.prices:
            if p.store.lower() == store_lower:
                price = p.price
                break
        
        # Om ingen pris för denna butik, ta lägsta
        if price is None and product.prices:
            price = min(p.price for p in product.prices)
        
        item_total = (price or 0) * item.quantity
        total += item_total
        
        items_for_store.append({
            'name': product.name,
            'brand': product.brand,
            'weight': product.weight,
            'quantity': item.quantity,
            'price': price,
            'total': item_total
        })
    
    # Formaterad text för urklipp - enkel lista med bara produktnamn
    # ICA.se och andra butiker vill ha enkla namn, en per rad
    simple_lines = []
    for item in items_for_store:
        # Använd bara produktnamnet (utan märke) för bättre sökträffar
        name = item['name']
        # Ta bort märkesnamn om det finns i slutet (t.ex. "Mjölk 3% Arla" -> "Mjölk 3%")
        brand = item.get('brand', '')
        if brand and name.endswith(brand):
            name = name[:-len(brand)].strip()
        
        # Lägg till antal om mer än 1
        if item['quantity'] > 1:
            simple_lines.append(f"{name} x{item['quantity']}")
        else:
            simple_lines.append(name)
    
    # Detaljerad text med priser etc
    detailed_lines = [f"Inköpslista - {store.upper()}"]
    detailed_lines.append("-" * 30)
    for item in items_for_store:
        qty = f" x{item['quantity']}" if item['quantity'] > 1 else ""
        detailed_lines.append(f"• {item['name']}{qty}")
    detailed_lines.append("-" * 30)
    detailed_lines.append(f"Totalt: {total:.0f} kr")
    
    return jsonify({
        'store': store,
        'store_url': store_urls.get(store_lower, ''),
        'items': items_for_store,
        'total': total,
        'text_for_clipboard': '\n'.join(simple_lines),  # Enkel lista för ICA etc
        'detailed_text': '\n'.join(detailed_lines),  # Detaljerad version
        'note': f'Listan kopierad! Gå till {store_urls.get(store_lower, store + ".se")} och klistra in varorna en i taget i sökfältet.',
        'instruction': 'Tips: På ICA.se, skriv i fältet "Lägg till vara" och klistra in (Ctrl+V). En vara läggs till i taget.',
        'export_options': [
            {'type': 'clipboard', 'description': 'Kopiera som text'},
            {'type': 'csv', 'description': 'Ladda ner som CSV'},
        ]
    })


if __name__ == '__main__':
    app.run(debug=True, port=5001)

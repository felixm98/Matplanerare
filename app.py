"""
Matplanerare - Flask App
En app för att planera mat baserat på näringsbehov och generera inköpslistor
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from database import db, init_db, Product, Price, Nutrition, NutritionPlan, ShoppingList, ShoppingItem
from scraper import MatsparScraper
import os
import math

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
    return render_template('plan.html', plans=plans)


@app.route('/api/plans', methods=['GET', 'POST'])
def api_plans():
    """API för näringsplaner"""
    if request.method == 'POST':
        data = request.json
        plan = NutritionPlan(
            name=data.get('name', 'Min plan'),
            calories_target=data.get('calories', 2000),
            protein_target=data.get('protein', 50),
            carbs_target=data.get('carbs', 250),
            fat_target=data.get('fat', 65),
            fiber_target=data.get('fiber', 30),
            vitamin_c_target=data.get('vitamin_c', 75),
            vitamin_d_target=data.get('vitamin_d', 10),
            calcium_target=data.get('calcium', 800),
            iron_target=data.get('iron', 15)
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
        plan.calories_target = data.get('calories', plan.calories_target)
        plan.protein_target = data.get('protein', plan.protein_target)
        plan.carbs_target = data.get('carbs', plan.carbs_target)
        plan.fat_target = data.get('fat', plan.fat_target)
        plan.fiber_target = data.get('fiber', plan.fiber_target)
        db.session.commit()
    
    return jsonify(plan.to_dict())


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
    return render_template('generate.html', plans=plans, stores=STORES)


@app.route('/api/generate-list', methods=['POST'])
def api_generate_list():
    """
    Generera inköpslista baserat på näringsplan
    Väljer produkter som matchar näringsbehoven
    Beräknar mängder baserat på 3 måltider per dag (frukost, lunch, middag)
    """
    data = request.json
    plan_id = data.get('plan_id')
    days = data.get('days', 7)
    store = data.get('store')
    
    plan = NutritionPlan.query.get_or_404(plan_id)
    
    # Antal måltider totalt (3 per dag: frukost, lunch, middag)
    total_meals = days * 3
    
    # Basvaror kategoriserade för bättre näringsbalans
    # quantity_factor anger hur många dagar en förpackning räcker
    base_products = {
        # Frukost-produkter (1 portion per dag)
        'frukost': [
            {'search': 'mjölk', 'days_per_pack': 5},      # 1.5L räcker ~5 dagar
            {'search': 'havregryn', 'days_per_pack': 14}, # 1.5kg räcker ~2 veckor
            {'search': 'yoghurt', 'days_per_pack': 4},    # 1kg räcker ~4 dagar
            {'search': 'bröd', 'days_per_pack': 5},       # 1 limpa räcker ~5 dagar
            {'search': 'smör', 'days_per_pack': 14},      # 500g räcker ~2 veckor
            {'search': 'ägg', 'days_per_pack': 6},        # 12-pack, 2 per dag = 6 dagar
        ],
        # Protein (lunch/middag - behövs för 2 måltider per dag)
        'protein': [
            {'search': 'kyckling', 'days_per_pack': 3},   # 900g räcker ~3 dagar
            {'search': 'lax', 'days_per_pack': 2},        # 400g räcker ~2 dagar
            {'search': 'nötfärs', 'days_per_pack': 3},    # 800g räcker ~3 dagar
            {'search': 'kvarg', 'days_per_pack': 4},      # 1kg räcker ~4 dagar (mellanmål/frukost)
        ],
        # Kolhydrater (bas till lunch/middag)
        'carbs': [
            {'search': 'ris', 'days_per_pack': 7},        # 1kg räcker ~7 dagar
            {'search': 'pasta', 'days_per_pack': 5},      # 500g räcker ~5 portioner
            {'search': 'potatis', 'days_per_pack': 5},    # 2kg räcker ~5 dagar
        ],
        # Grönsaker (till varje måltid)
        'vegetables': [
            {'search': 'tomat', 'days_per_pack': 3},      # 500g räcker ~3 dagar
            {'search': 'gurka', 'days_per_pack': 3},      # 1 st räcker ~3 dagar
            {'search': 'sallad', 'days_per_pack': 4},     # 1 st räcker ~4 dagar
            {'search': 'morot', 'days_per_pack': 5},      # 1kg räcker ~5 dagar
            {'search': 'lök', 'days_per_pack': 7},        # 1kg räcker ~1 vecka
            {'search': 'broccoli', 'days_per_pack': 3},   # 500g räcker ~3 dagar
            {'search': 'paprika', 'days_per_pack': 3},    # 2st räcker ~3 dagar
        ],
        # Frukt (mellanmål/frukost)
        'fruit': [
            {'search': 'banan', 'days_per_pack': 4},      # 1kg räcker ~4 dagar
            {'search': 'äpple', 'days_per_pack': 5},      # 1kg räcker ~5 dagar
            {'search': 'apelsin', 'days_per_pack': 5},    # 1kg räcker ~5 dagar
        ],
        # Mejeriprodukter (matlagning/tillbehör)
        'dairy': [
            {'search': 'ost', 'days_per_pack': 7},        # 500g räcker ~1 vecka
            {'search': 'grädde', 'days_per_pack': 7},     # 5dl räcker ~1 vecka
        ],
        # Baljväxter (vegetariskt protein/fiber)
        'legumes': [
            {'search': 'linser', 'days_per_pack': 5},     # 500g räcker ~5 portioner
            {'search': 'bönor', 'days_per_pack': 4},      # 410g räcker ~4 portioner
        ],
    }
    
    # Skapa ny inköpslista
    shopping_list = ShoppingList(
        name=f"Genererad lista - {plan.name} ({days} dag{'ar' if days > 1 else ''})",
        store=store,
        days=days,
        plan_id=plan_id
    )
    db.session.add(shopping_list)
    db.session.flush()
    
    added_products = []
    
    # Gå igenom varje kategori och lägg till produkter
    for category, products in base_products.items():
        for product_info in products:
            product_name = product_info['search']
            days_per_pack = product_info['days_per_pack']
            
            results = scraper.search_products(product_name, limit=1)
            if results:
                prod_data = results[0]
                
                # Skapa produkt med all data
                product = Product(
                    name=prod_data.get('name'),
                    brand=prod_data.get('brand'),
                    weight=prod_data.get('weight'),
                    category=prod_data.get('category', category),
                    matspar_url=prod_data.get('url'),
                    image_url=prod_data.get('image')
                )
                db.session.add(product)
                db.session.flush()
                
                # Lägg till priser
                for store_name, price in prod_data.get('prices', {}).items():
                    price_obj = Price(product_id=product.id, store=store_name, price=price)
                    db.session.add(price_obj)
                
                # Lägg till näringsvärden
                nutr_data = prod_data.get('nutrition', {})
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
                
                # Beräkna kvantitet baserat på antal dagar och hur länge förpackningen räcker
                # Avrunda uppåt för att säkerställa att det räcker
                quantity = max(1, math.ceil(days / days_per_pack))
                
                # Lägg till i lista
                item = ShoppingItem(
                    list_id=shopping_list.id,
                    product_id=product.id,
                    quantity=quantity
                )
                db.session.add(item)
                added_products.append(prod_data.get('name'))
    
    _update_list_total(shopping_list)
    db.session.commit()
    
    return jsonify(shopping_list.to_dict()), 201


if __name__ == '__main__':
    app.run(debug=True, port=5001)

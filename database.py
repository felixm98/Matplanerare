"""
Databas för matplaneraren
Lagrar produkter, priser och näringsvärden

SESSIONSBASERAD HANTERING:
- Varje användare får ett unikt session_id (UUID) som sparas i en cookie
- All data (planer, listor, recept) kopplas till session_id
- Användarinställningar (postnummer, butik) sparas per session

NÄRINGSMÅLSLOGIK:
- 'target': Standardmål att försöka uppnå (±20% tolerans anses bra)
- 'mode': 'exact' (försök matcha), 'min' (minst X), 'max' (högst X), 'ignore' (ingen preferens)
- Om mål inte kan uppfyllas exakt väljs närmaste möjliga värde
- 0-värden: Att sätta 0 som exakt mål är oftast omöjligt (livsmedel innehåller naturligt näringsämnen)
  Därför rekommenderas 'max'-läge med lågt värde eller 'ignore' istället

REKOMMENDERAT DAGLIGT INTAG (RDI) - Svenska rekommendationer:
Makronäringsämnen:
  - Kalorier: 2000 kcal (kvinnor), 2500 kcal (män) - varierar med aktivitetsnivå
  - Protein: 0.8-1.2 g/kg kroppsvikt, ca 50-75 g/dag
  - Kolhydrater: 250-350 g/dag (45-60% av energiintag)
  - Fett: 65-80 g/dag (25-35% av energiintag)
  - Fiber: 25-35 g/dag
  
Vitaminer:
  - Vitamin A: 700-900 µg/dag
  - Vitamin C: 75-90 mg/dag
  - Vitamin D: 10-20 µg/dag (speciellt viktigt i Norden)
  - Vitamin E: 8-10 mg/dag
  - Vitamin B12: 2-2.4 µg/dag
  
Mineraler:
  - Kalcium: 800-1000 mg/dag
  - Järn: 9 mg (män), 15 mg (kvinnor)
  - Magnesium: 280-350 mg/dag
  - Kalium: 3100-3500 mg/dag
  - Zink: 7-9 mg/dag

OBS: Dessa är generella riktlinjer för friska vuxna. Ej medicinska råd.
Individuella behov kan variera baserat på ålder, kön, graviditet, sjukdomar etc.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re

db = SQLAlchemy()

# Fördefinierade allergener/intoleranser
ALLERGENS = {
    'gluten': {
        'name': 'Gluten',
        'description': 'Vete, råg, korn, havre',
        'icon': '🌾'
    },
    'lactose': {
        'name': 'Laktos',
        'description': 'Mjölkprodukter',
        'icon': '🥛'
    },
    'nuts': {
        'name': 'Nötter',
        'description': 'Alla typer av nötter och mandlar',
        'icon': '🥜'
    },
    'eggs': {
        'name': 'Ägg',
        'description': 'Ägg och äggprodukter',
        'icon': '🥚'
    },
    'fish': {
        'name': 'Fisk & skaldjur',
        'description': 'Fisk, räkor, musslor etc.',
        'icon': '🐟'
    },
    'soy': {
        'name': 'Soja',
        'description': 'Sojabönor och sojaprodukter',
        'icon': '🫘'
    },
    'vegetarian': {
        'name': 'Vegetarisk',
        'description': 'Utesluter kött och fisk',
        'icon': '🥬'
    },
    'vegan': {
        'name': 'Vegansk',
        'description': 'Utesluter alla animaliska produkter',
        'icon': '🌱'
    }
}

# RDI (Recommended Daily Intake) - Svenska rekommendationer
RDI_VALUES = {
    'calories': {'value': 2000, 'unit': 'kcal', 'name': 'Kalorier', 'description': 'Dagligt energibehov för måttligt aktiv vuxen'},
    'protein': {'value': 60, 'unit': 'g', 'name': 'Protein', 'description': 'Ca 0.8-1.0 g per kg kroppsvikt'},
    'carbs': {'value': 280, 'unit': 'g', 'name': 'Kolhydrater', 'description': '45-60% av dagligt energiintag'},
    'fat': {'value': 70, 'unit': 'g', 'name': 'Fett', 'description': '25-35% av dagligt energiintag'},
    'fiber': {'value': 30, 'unit': 'g', 'name': 'Fiber', 'description': 'Viktigt för tarmhälsa'},
    'sugar': {'value': 50, 'unit': 'g', 'name': 'Socker', 'description': 'Max 10% av energiintag'},
    'salt': {'value': 6, 'unit': 'g', 'name': 'Salt', 'description': 'WHO rekommenderar max 5g'},
    'vitamin_a': {'value': 800, 'unit': 'µg', 'name': 'Vitamin A', 'description': 'Syn, immunförsvar, hud'},
    'vitamin_c': {'value': 80, 'unit': 'mg', 'name': 'Vitamin C', 'description': 'Antioxidant, immunförsvar'},
    'vitamin_d': {'value': 15, 'unit': 'µg', 'name': 'Vitamin D', 'description': 'Ben, immunförsvar - extra viktigt i Norden'},
    'vitamin_e': {'value': 10, 'unit': 'mg', 'name': 'Vitamin E', 'description': 'Antioxidant, cellskydd'},
    'vitamin_b12': {'value': 2.5, 'unit': 'µg', 'name': 'Vitamin B12', 'description': 'Nervsystem, blodbildning'},
    'calcium': {'value': 900, 'unit': 'mg', 'name': 'Kalcium', 'description': 'Ben och tänder'},
    'iron': {'value': 12, 'unit': 'mg', 'name': 'Järn', 'description': 'Blodbildning - högre behov för kvinnor'},
    'magnesium': {'value': 320, 'unit': 'mg', 'name': 'Magnesium', 'description': 'Muskler, nerver, energi'},
    'potassium': {'value': 3500, 'unit': 'mg', 'name': 'Kalium', 'description': 'Blodtryck, muskelfunktion'},
    'zinc': {'value': 8, 'unit': 'mg', 'name': 'Zink', 'description': 'Immunförsvar, sårläkning'}
}


class UserSession(db.Model):
    """Användarens sessionsinställningar"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), unique=True, nullable=False, index=True)  # UUID
    
    # Platsinställningar
    postal_code = db.Column(db.String(10))  # Postnummer för prisberäkning
    preferred_store = db.Column(db.String(50))  # Favoritbutik
    
    # Tidsstämplar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'session_id': self.session_id,
            'postal_code': self.postal_code,
            'preferred_store': self.preferred_store,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None
        }


class Product(db.Model):
    """Produkter från matbutiker"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100))
    weight = db.Column(db.String(50))  # t.ex. "500g", "1 l"
    category = db.Column(db.String(100))
    matspar_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))  # Produktbild från matspar CDN
    
    # Allergen-taggar (komma-separerad lista)
    # Möjliga: gluten, lactose, nuts, eggs, fish, soy, meat, animal
    allergen_tags = db.Column(db.String(500), default='')
    
    # Tidsstämplar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationer
    prices = db.relationship('Price', backref='product', lazy=True, cascade='all, delete-orphan')
    nutrition = db.relationship('Nutrition', backref='product', uselist=False, cascade='all, delete-orphan')
    
    def get_allergen_list(self):
        """Returnerar allergener som lista"""
        if not self.allergen_tags:
            return []
        return [tag.strip() for tag in self.allergen_tags.split(',') if tag.strip()]
    
    def has_allergen(self, allergen):
        """Kontrollerar om produkten innehåller ett visst allergen"""
        return allergen.lower() in [a.lower() for a in self.get_allergen_list()]
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'weight': self.weight,
            'category': self.category,
            'image_url': self.image_url,
            'allergen_tags': self.get_allergen_list(),
            'prices': [p.to_dict() for p in self.prices],
            'nutrition': self.nutrition.to_dict() if self.nutrition else None
        }


class Price(db.Model):
    """Priser per butik"""
    __tablename__ = 'prices'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    store = db.Column(db.String(50), nullable=False)  # ICA, Coop, Willys, etc.
    price = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float)  # Jämförpris per kg/l
    on_sale = db.Column(db.Boolean, default=False)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'store': self.store,
            'price': self.price,
            'unit_price': self.unit_price,
            'on_sale': self.on_sale,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Nutrition(db.Model):
    """Näringsvärden per 100g"""
    __tablename__ = 'nutrition'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    # Makronäringsämnen (per 100g)
    calories = db.Column(db.Float)  # kcal
    protein = db.Column(db.Float)   # g
    carbs = db.Column(db.Float)     # g
    sugar = db.Column(db.Float)     # g
    fat = db.Column(db.Float)       # g
    saturated_fat = db.Column(db.Float)  # g
    fiber = db.Column(db.Float)     # g
    salt = db.Column(db.Float)      # g
    
    # Vitaminer (om tillgängligt)
    vitamin_a = db.Column(db.Float)  # µg
    vitamin_c = db.Column(db.Float)  # mg
    vitamin_d = db.Column(db.Float)  # µg
    vitamin_e = db.Column(db.Float)  # mg
    vitamin_b12 = db.Column(db.Float)  # µg
    
    # Mineraler
    calcium = db.Column(db.Float)    # mg
    iron = db.Column(db.Float)       # mg
    magnesium = db.Column(db.Float)  # mg
    potassium = db.Column(db.Float)  # mg
    zinc = db.Column(db.Float)       # mg
    
    def to_dict(self):
        return {
            'calories': self.calories,
            'protein': self.protein,
            'carbs': self.carbs,
            'sugar': self.sugar,
            'fat': self.fat,
            'saturated_fat': self.saturated_fat,
            'fiber': self.fiber,
            'salt': self.salt,
            'vitamins': {
                'a': self.vitamin_a,
                'c': self.vitamin_c,
                'd': self.vitamin_d,
                'e': self.vitamin_e,
                'b12': self.vitamin_b12
            },
            'minerals': {
                'calcium': self.calcium,
                'iron': self.iron,
                'magnesium': self.magnesium,
                'potassium': self.potassium,
                'zinc': self.zinc
            }
        }


class NutritionPlan(db.Model):
    """
    Användarens näringsplan/mål
    
    Mållägen (mode) för varje näringsvärde:
    - 'target': Försök uppnå detta värde (standard)
    - 'min': Minst detta värde
    - 'max': Högst detta värde  
    - 'ignore': Ingen preferens (ignorera vid generering)
    
    Notera: Att sätta 0 som 'target' är problematiskt eftersom nästan alla
    livsmedel innehåller naturligt små mängder av näringsämnen.
    Rekommendation: Använd 'max' med lågt värde eller 'ignore'.
    """
    __tablename__ = 'nutrition_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), index=True)  # Kopplar till användarens session
    name = db.Column(db.String(100), nullable=False)
    
    # Allergier och intoleranser (komma-separerad lista)
    allergies = db.Column(db.String(500), default='')
    
    # Dagliga mål - target-värden
    calories_target = db.Column(db.Float, default=2000)
    protein_target = db.Column(db.Float, default=60)    # g
    carbs_target = db.Column(db.Float, default=280)     # g
    fat_target = db.Column(db.Float, default=70)        # g
    fiber_target = db.Column(db.Float, default=30)      # g
    sugar_target = db.Column(db.Float, default=50)      # g
    salt_target = db.Column(db.Float, default=6)        # g
    
    # Mode för makronäringsämnen: 'target', 'min', 'max', 'ignore'
    calories_mode = db.Column(db.String(10), default='target')
    protein_mode = db.Column(db.String(10), default='min')
    carbs_mode = db.Column(db.String(10), default='target')
    fat_mode = db.Column(db.String(10), default='max')
    fiber_mode = db.Column(db.String(10), default='min')
    sugar_mode = db.Column(db.String(10), default='max')
    salt_mode = db.Column(db.String(10), default='max')
    
    # Vitamin- och mineralmål
    vitamin_c_target = db.Column(db.Float, default=80)   # mg
    vitamin_d_target = db.Column(db.Float, default=15)   # µg
    vitamin_a_target = db.Column(db.Float, default=800)  # µg
    calcium_target = db.Column(db.Float, default=900)    # mg
    iron_target = db.Column(db.Float, default=12)        # mg
    potassium_target = db.Column(db.Float, default=3500) # mg
    
    # Mode för vitaminer/mineraler
    vitamin_c_mode = db.Column(db.String(10), default='min')
    vitamin_d_mode = db.Column(db.String(10), default='min')
    vitamin_a_mode = db.Column(db.String(10), default='min')
    calcium_mode = db.Column(db.String(10), default='min')
    iron_mode = db.Column(db.String(10), default='min')
    potassium_mode = db.Column(db.String(10), default='ignore')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_allergies_list(self):
        """Returnerar allergier som lista"""
        if not self.allergies:
            return []
        return [a.strip() for a in self.allergies.split(',') if a.strip()]
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'allergies': self.get_allergies_list(),
            'daily_targets': {
                'calories': {'value': self.calories_target, 'mode': self.calories_mode},
                'protein': {'value': self.protein_target, 'mode': self.protein_mode},
                'carbs': {'value': self.carbs_target, 'mode': self.carbs_mode},
                'fat': {'value': self.fat_target, 'mode': self.fat_mode},
                'fiber': {'value': self.fiber_target, 'mode': self.fiber_mode},
                'sugar': {'value': self.sugar_target, 'mode': self.sugar_mode},
                'salt': {'value': self.salt_target, 'mode': self.salt_mode},
                'vitamin_c': {'value': self.vitamin_c_target, 'mode': self.vitamin_c_mode},
                'vitamin_d': {'value': self.vitamin_d_target, 'mode': self.vitamin_d_mode},
                'vitamin_a': {'value': self.vitamin_a_target, 'mode': self.vitamin_a_mode},
                'calcium': {'value': self.calcium_target, 'mode': self.calcium_mode},
                'iron': {'value': self.iron_target, 'mode': self.iron_mode},
                'potassium': {'value': self.potassium_target, 'mode': self.potassium_mode}
            },
            # Bakåtkompatibilitet
            'calories': self.calories_target,
            'protein': self.protein_target,
            'carbs': self.carbs_target,
            'fat': self.fat_target,
            'fiber': self.fiber_target
        }


class ShoppingList(db.Model):
    """Inköpslistor"""
    __tablename__ = 'shopping_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), index=True)  # Kopplar till användarens session
    name = db.Column(db.String(100))
    store = db.Column(db.String(50))  # Vald butik
    days = db.Column(db.Integer, default=7)  # Antal dagar
    plan_id = db.Column(db.Integer, db.ForeignKey('nutrition_plans.id'))
    
    # Budget och hushållsstorlek
    budget = db.Column(db.Float)  # Budget i SEK (None = ingen budget)
    household_size = db.Column(db.Integer, default=1)  # Antal personer
    
    total_cost = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationer
    plan = db.relationship('NutritionPlan', backref='shopping_lists')
    items = db.relationship('ShoppingItem', backref='shopping_list', lazy=True, cascade='all, delete-orphan')
    
    def get_cost_per_person(self):
        """Beräknar kostnad per person"""
        if not self.total_cost or not self.household_size:
            return 0
        return self.total_cost / self.household_size
    
    def calculate_nutrition_summary(self):
        """Beräknar total näringssummering för listan"""
        summary = {
            'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0,
            'fiber': 0, 'vitamin_c': 0, 'vitamin_d': 0, 'calcium': 0, 'iron': 0
        }
        
        for item in self.items:
            if item.product and item.product.nutrition:
                nutr = item.product.nutrition
                grams = item.estimate_grams()
                factor = (grams / 100) * item.quantity
                
                if nutr.calories:
                    summary['calories'] += nutr.calories * factor
                if nutr.protein:
                    summary['protein'] += nutr.protein * factor
                if nutr.carbs:
                    summary['carbs'] += nutr.carbs * factor
                if nutr.fat:
                    summary['fat'] += nutr.fat * factor
                if nutr.fiber:
                    summary['fiber'] += nutr.fiber * factor
                if nutr.vitamin_c:
                    summary['vitamin_c'] += nutr.vitamin_c * factor
                if nutr.vitamin_d:
                    summary['vitamin_d'] += nutr.vitamin_d * factor
                if nutr.calcium:
                    summary['calcium'] += nutr.calcium * factor
                if nutr.iron:
                    summary['iron'] += nutr.iron * factor
        
        return summary
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'store': self.store,
            'days': self.days,
            'budget': self.budget,
            'household_size': self.household_size,
            'total_cost': self.total_cost,
            'cost_per_person': self.get_cost_per_person(),
            'items': [item.to_dict() for item in self.items],
            'nutrition_summary': self.calculate_nutrition_summary(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ShoppingItem(db.Model):
    """Produkter i en inköpslista"""
    __tablename__ = 'shopping_items'
    
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey('shopping_lists.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    checked = db.Column(db.Boolean, default=False)
    
    # För produktersättning - sparar original-produkt-id om utbytt
    original_product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    
    # Relation
    product = db.relationship('Product', foreign_keys=[product_id])
    original_product = db.relationship('Product', foreign_keys=[original_product_id])
    
    def estimate_grams(self):
        """Uppskattar gram från viktfält"""
        if not self.product or not self.product.weight:
            return 500  # Default
        
        weight = self.product.weight.lower()
        
        # Försök extrahera nummer och enhet
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l|cl|dl)', weight)
        if match:
            value = float(match.group(1).replace(',', '.'))
            unit = match.group(2)
            
            if unit == 'kg':
                return value * 1000
            elif unit == 'g':
                return value
            elif unit == 'l':
                return value * 1000
            elif unit == 'dl':
                return value * 100
            elif unit == 'cl':
                return value * 10
            elif unit == 'ml':
                return value
        
        return 500
    
    def to_dict(self):
        return {
            'id': self.id,
            'product': self.product.to_dict() if self.product else None,
            'quantity': self.quantity,
            'checked': self.checked,
            'original_product': self.original_product.to_dict() if self.original_product else None,
            'was_substituted': self.original_product_id is not None
        }


class Recipe(db.Model):
    """AI-genererade recept"""
    __tablename__ = 'recipes'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), index=True)  # Kopplar till användarens session
    shopping_list_id = db.Column(db.Integer, db.ForeignKey('shopping_lists.id'))
    
    day = db.Column(db.Integer, default=1)  # Dag 1-7
    meal_type = db.Column(db.String(50))  # frukost, lunch, middag, mellanmål
    
    name = db.Column(db.String(200))
    portions = db.Column(db.Integer, default=2)
    calories_per_portion = db.Column(db.Integer)
    prep_time_minutes = db.Column(db.Integer)
    
    ingredients_json = db.Column(db.Text)  # JSON-lista med ingredienser
    instructions_json = db.Column(db.Text)  # JSON-lista med instruktioner
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation
    shopping_list = db.relationship('ShoppingList', backref=db.backref('recipes', lazy=True, cascade='all, delete-orphan'))
    
    def get_ingredients(self):
        """Hämta ingredienser som lista"""
        import json
        if self.ingredients_json:
            try:
                return json.loads(self.ingredients_json)
            except:
                return []
        return []
    
    def set_ingredients(self, ingredients):
        """Spara ingredienser"""
        import json
        self.ingredients_json = json.dumps(ingredients, ensure_ascii=False)
    
    def get_instructions(self):
        """Hämta instruktioner som lista"""
        import json
        if self.instructions_json:
            try:
                return json.loads(self.instructions_json)
            except:
                return []
        return []
    
    def set_instructions(self, instructions):
        """Spara instruktioner"""
        import json
        self.instructions_json = json.dumps(instructions, ensure_ascii=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'day': self.day,
            'meal_type': self.meal_type,
            'name': self.name,
            'portions': self.portions,
            'calories_per_portion': self.calories_per_portion,
            'prep_time_minutes': self.prep_time_minutes,
            'ingredients': self.get_ingredients(),
            'instructions': self.get_instructions()
        }


def init_db(app):
    """Initierar databasen"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

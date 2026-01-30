"""
Databas för matplaneraren
Lagrar produkter, priser och näringsvärden
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


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
    
    # Tidsstämplar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationer
    prices = db.relationship('Price', backref='product', lazy=True, cascade='all, delete-orphan')
    nutrition = db.relationship('Nutrition', backref='product', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'weight': self.weight,
            'category': self.category,
            'image_url': self.image_url,
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
    """Användarens näringsplan/mål"""
    __tablename__ = 'nutrition_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Dagliga mål
    calories_target = db.Column(db.Float, default=2000)
    protein_target = db.Column(db.Float, default=50)    # g
    carbs_target = db.Column(db.Float, default=250)     # g
    fat_target = db.Column(db.Float, default=65)        # g
    fiber_target = db.Column(db.Float, default=30)      # g
    
    # Vitamin- och mineralmål (baserat på RDI)
    vitamin_c_target = db.Column(db.Float, default=75)   # mg
    vitamin_d_target = db.Column(db.Float, default=10)   # µg
    calcium_target = db.Column(db.Float, default=800)    # mg
    iron_target = db.Column(db.Float, default=15)        # mg
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'daily_targets': {
                'calories': self.calories_target,
                'protein': self.protein_target,
                'carbs': self.carbs_target,
                'fat': self.fat_target,
                'fiber': self.fiber_target,
                'vitamin_c': self.vitamin_c_target,
                'vitamin_d': self.vitamin_d_target,
                'calcium': self.calcium_target,
                'iron': self.iron_target
            }
        }


class ShoppingList(db.Model):
    """Inköpslistor"""
    __tablename__ = 'shopping_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    store = db.Column(db.String(50))  # Vald butik
    days = db.Column(db.Integer, default=7)  # Antal dagar
    plan_id = db.Column(db.Integer, db.ForeignKey('nutrition_plans.id'))
    
    total_cost = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationer
    plan = db.relationship('NutritionPlan', backref='shopping_lists')
    items = db.relationship('ShoppingItem', backref='shopping_list', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'store': self.store,
            'days': self.days,
            'total_cost': self.total_cost,
            'items': [item.to_dict() for item in self.items],
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
    
    # Relation
    product = db.relationship('Product')
    
    def to_dict(self):
        return {
            'id': self.id,
            'product': self.product.to_dict() if self.product else None,
            'quantity': self.quantity,
            'checked': self.checked
        }


def init_db(app):
    """Initierar databasen"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

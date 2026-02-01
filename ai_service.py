"""
AI Service för receptgenerering med Groq API
Groq har generösa kvoter och snabb inferens
"""
import os
import json
import re
import time
import requests

# Ladda .env-fil om den finns
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class AIRecipeService:
    """Service för AI-baserad receptgenerering via Groq API"""
    
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('GROQ_API_KEY')
        self._last_request_time = 0
        self._min_request_interval = 2  # Groq har bättre kvoter
    
    def is_available(self):
        """Kolla om AI-tjänsten är tillgänglig"""
        return bool(self.api_key)
    
    def _wait_for_rate_limit(self):
        """Vänta om vi gör anrop för snabbt"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            wait_time = self._min_request_interval - elapsed
            print(f"Rate limiting: väntar {wait_time:.1f}s...")
            time.sleep(wait_time)
        self._last_request_time = time.time()
    
    def generate_recipes(self, params):
        """
        Generera recept baserat på parametrar via Groq
        """
        if not self.is_available():
            return None, "AI-tjänsten är inte tillgänglig. Kontrollera GROQ_API_KEY."
        
        # Bygg prompt
        prompt = self._build_recipe_prompt(params)
        
        # Rate limiting
        self._wait_for_rate_limit()
        
        print("Skickar förfrågan till Groq API...")
        
        try:
            response = requests.post(
                self.GROQ_API_URL,
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "Du är en svensk matplanerare. Svara alltid med giltig JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 8000
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=120
            )
            
            if response.status_code == 429:
                return None, "API-kvoten är tillfälligt slut. Vänta en stund och försök igen."
            
            if response.status_code != 200:
                error_msg = response.json().get('error', {}).get('message', response.text)
                return None, f"API-fel ({response.status_code}): {error_msg}"
            
            # Parsa svar
            result = response.json()
            text = result['choices'][0]['message']['content']
            
            print("Svar mottaget, parsear recept...")
            recipes_data = self._parse_recipe_response(text)
            return recipes_data, None
            
        except requests.exceptions.Timeout:
            return None, "Timeout - API:t svarade inte inom 120 sekunder."
        except Exception as e:
            return None, f"Fel vid generering: {str(e)}"
    
    def _build_recipe_prompt(self, params):
        """Bygg prompt för receptgenerering"""
        
        days = params.get('days', 7)
        calories = params.get('calories_per_day', 2000)
        persons = params.get('household_size', 1)
        allergies = params.get('allergies', [])
        
        include_breakfast = params.get('include_breakfast', True)
        include_lunch = params.get('include_lunch', True)
        include_dinner = params.get('include_dinner', True)
        include_snacks = params.get('include_snacks', False)
        
        # Beräkna måltidsfördelning
        meals_info = []
        total_fraction = 0
        
        if include_breakfast:
            meals_info.append(('frukost', 0.20))
            total_fraction += 0.20
        if include_lunch:
            meals_info.append(('lunch', 0.35))
            total_fraction += 0.35
        if include_dinner:
            meals_info.append(('middag', 0.35))
            total_fraction += 0.35
        if include_snacks:
            meals_info.append(('mellanmål', 0.10))
            total_fraction += 0.10
        
        # Justera om inte alla måltider valts
        if total_fraction > 0:
            meals_info = [(name, frac/total_fraction) for name, frac in meals_info]
        
        meals_text = ", ".join([f"{name}" for name, frac in meals_info])
        
        allergy_text = ""
        if allergies:
            allergy_text = f"\n- VIKTIGT: Undvik dessa allergener: {', '.join(allergies)}"
        
        # Begränsa till max 3 dagar för att undvika ofullständig JSON
        actual_days = min(days, 3)
        
        prompt = f"""Skapa en matplan för {actual_days} dagar.

KRAV:
- {persons} person(er), {calories} kcal/dag
- Måltider: {meals_text}{allergy_text}
- Svenska rätter, korta instruktioner

Returnera ENDAST JSON (ingen markdown, inga kommentarer):
{{"recipes":[{{"day":1,"meal_type":"middag","name":"Köttfärssås","portions":{persons},"calories_per_portion":600,"prep_time_minutes":25,"ingredients":[{{"name":"nötfärs","amount":400,"unit":"g"}},{{"name":"pasta","amount":300,"unit":"g"}}],"instructions":["Bryn färsen.","Koka pasta.","Blanda och servera."]}}]}}

Skapa {actual_days} dagars recept med {meals_text}. Kort och koncist!"""
        return prompt
    
    def _parse_recipe_response(self, response_text):
        """Parsa AI-svaret till strukturerad data"""
        
        # Försök hitta JSON i svaret
        try:
            # Ta bort eventuell markdown-formatering
            text = response_text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            text = text.strip()
            
            # Hitta JSON-objektet
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                
                # Försök parsa direkt
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Försök fixa vanliga problem
                    # Ta bort trailing komma före ]
                    json_str = re.sub(r',\s*]', ']', json_str)
                    # Ta bort trailing komma före }
                    json_str = re.sub(r',\s*}', '}', json_str)
                    
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # Försök hitta sista kompletta receptet
                        # Hitta sista "]" innan "recipes" slutar
                        recipes_end = json_str.rfind(']}')
                        if recipes_end > 0:
                            json_str = json_str[:recipes_end+2] + '}'
                            try:
                                return json.loads(json_str)
                            except:
                                pass
                        
        except Exception as e:
            print(f"Parse error: {e}")
        
        print(f"Kunde inte parsa JSON från AI-svar")
        print(f"Response text (första 1000 tecken): {response_text[:1000]}")
        return None
    
    def extract_ingredients_for_search(self, recipes_data):
        """
        Extrahera sökbara ingredienser från recept
        Returnerar lista med (sökterm, kategori, mängd)
        """
        if not recipes_data or 'recipes' not in recipes_data:
            return []
        
        # Samla alla ingredienser
        ingredient_totals = {}
        
        for recipe in recipes_data['recipes']:
            # Hantera om recipe är en sträng istället för dict
            if isinstance(recipe, str):
                print(f"Varning: recipe är sträng, inte dict: {recipe[:100]}")
                continue
            
            ingredients_list = recipe.get('ingredients', [])
            
            for ing in ingredients_list:
                # Hantera olika format
                if isinstance(ing, str):
                    # Ingrediensen är bara en sträng, t.ex. "400g nötfärs"
                    name = ing.lower()
                    amount = 1
                    unit = 'st'
                elif isinstance(ing, dict):
                    name = ing.get('name', '').lower()
                    amount = ing.get('amount', 1)
                    unit = ing.get('unit', 'st')
                else:
                    print(f"Varning: okänt ingrediensformat: {type(ing)}")
                    continue
                
                if not name:
                    continue
                
                # Normalisera och summera
                key = self._normalize_ingredient(name)
                if key not in ingredient_totals:
                    ingredient_totals[key] = {
                        'search_term': self._get_search_term(name),
                        'category': self._categorize_ingredient(name),
                        'amounts': []
                    }
                ingredient_totals[key]['amounts'].append((amount, unit))
        
        # Konvertera till lista
        result = []
        for key, data in ingredient_totals.items():
            total = self._sum_amounts(data['amounts'])
            result.append({
                'search_term': data['search_term'],
                'category': data['category'],
                'total_amount': total,
                'original_name': key
            })
        
        return result
    
    def _normalize_ingredient(self, name):
        """Normalisera ingrediensnamn för gruppering"""
        name = name.lower().strip()
        
        # Mappningar för vanliga varianter
        mappings = {
            'kycklingfilé': 'kyckling',
            'kycklingbröst': 'kyckling',
            'nötfärs 12%': 'nötfärs',
            'nötfärs 10%': 'nötfärs',
            'grädde': 'vispgrädde',
            'matlagningsgrädde': 'vispgrädde',
        }
        
        return mappings.get(name, name)
    
    def _get_search_term(self, name):
        """Få bästa sökterm för Matspar"""
        name = name.lower()
        
        # Specifika söktermer för bättre matchning
        search_terms = {
            'krossade tomater': 'krossade tomater',
            'passerade tomater': 'passerade tomater',
            'nötfärs': 'nötfärs',
            'kycklingfilé': 'kycklingfilé',
            'lök': 'gul lök',
            'vitlök': 'vitlök',
            'ris': 'ris',
            'pasta': 'spaghetti',  # Vanligaste pastan
            'olivolja': 'olivolja',
            'smör': 'smör',
            'mjölk': 'mjölk',
            'grädde': 'vispgrädde',
            'ägg': 'ägg',
            'ost': 'ost',
        }
        
        for key, term in search_terms.items():
            if key in name:
                return term
        
        return name
    
    def _categorize_ingredient(self, name):
        """Kategorisera ingrediens"""
        name = name.lower()
        
        proteins = ['kyckling', 'fläsk', 'nöt', 'färs', 'fisk', 'lax', 'torsk', 'räkor', 'ägg', 'tofu', 'bönor', 'linser']
        carbs = ['pasta', 'ris', 'potatis', 'bröd', 'nudlar', 'couscous', 'bulgur']
        dairy = ['mjölk', 'grädde', 'ost', 'smör', 'yoghurt', 'kvarg', 'crème']
        vegetables = ['lök', 'tomat', 'gurka', 'paprika', 'morot', 'broccoli', 'sallad', 'spenat', 'zucchini', 'aubergine', 'svamp', 'vitlök']
        
        for p in proteins:
            if p in name:
                return 'protein'
        for c in carbs:
            if c in name:
                return 'carbs'
        for d in dairy:
            if d in name:
                return 'dairy'
        for v in vegetables:
            if v in name:
                return 'vegetables'
        
        return 'other'
    
    def _sum_amounts(self, amounts):
        """Summera mängder (förenklad version)"""
        # Gruppera per enhet
        by_unit = {}
        for amount, unit in amounts:
            unit = unit.lower()
            if unit not in by_unit:
                by_unit[unit] = 0
            by_unit[unit] += amount
        
        # Returnera som sträng
        parts = []
        for unit, total in by_unit.items():
            if unit in ['g', 'kg', 'ml', 'l', 'dl']:
                parts.append(f"{total}{unit}")
            else:
                parts.append(f"{total} {unit}")
        
        return ', '.join(parts) if parts else '1 st'


# Singleton-instans
_ai_service = None

def get_ai_service(api_key=None):
    """Hämta AI-service instans"""
    global _ai_service
    if _ai_service is None or api_key:
        _ai_service = AIRecipeService(api_key)
    return _ai_service

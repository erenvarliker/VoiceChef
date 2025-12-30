"""Recipe planning service using LLM (Groq or OpenAI)."""

import json
import re
from app.config import get_settings
from app.schemas import Recipe, RecipeStep

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class RecipePlanner:
    """Creates recipes from dish names using LLM."""
    
    def __init__(self):
        settings = get_settings()
        # Prefer Groq, fall back to OpenAI config if needed
        api_key = settings.groq_api_key or settings.openai_api_key
        model = settings.groq_model or settings.openai_model

        if not api_key:
            # No key configured – all calls will fall back to simple recipes
            print("[RecipePlanner] WARNING: No Groq/OpenAI API key configured. Using fallback recipes.")
            self.client = None
        else:
            # Try Groq first, then OpenAI
            if GROQ_AVAILABLE and settings.groq_api_key:
                self.client = Groq(api_key=settings.groq_api_key)
                self.model = settings.groq_model
            elif OPENAI_AVAILABLE and settings.openai_api_key:
                self.client = OpenAI(api_key=settings.openai_api_key)
                self.model = settings.openai_model
            else:
                self.client = None
                self.model = model
    
    def extract_dish_name(self, user_message: str) -> str:
        """
        Extract dish name from user's natural language message.
        
        Args:
            user_message: e.g., "I want to cook pasta carbonara"
        
        Returns:
            str: Extracted dish name
        """
        system_prompt = """Extract the dish name from the user's message.
Return only the dish name, nothing else."""
        
        try:
            if not self.client:
                raise RuntimeError("LLM client not configured")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception:
            # Fallback: simple extraction
            words_to_remove = ["i", "want", "to", "cook", "make", "prepare", "recipe", "for"]
            words = user_message.lower().split()
            dish_words = [w for w in words if w not in words_to_remove]
            return " ".join(dish_words) if dish_words else "unknown dish"
    
    def create_recipe(self, dish_name: str) -> Recipe:
        """
        Generate a recipe for the given dish with safety detection.
        
        Args:
            dish_name: Name of the dish to create recipe for
        
        Returns:
            Recipe: Complete recipe with steps, ingredients, and safety flags
        """
        system_prompt = """You are a professional chef assistant creating recipes for a voice-controlled AR cooking system.

Create detailed, easy-to-follow recipes. Respond ONLY with valid JSON using:
- dish_name: string
- ingredients: array of strings (with quantities)
- steps: array of objects with:
  - step_number: int
  - title: string (VERY SHORT summary, e.g. "Chop Onions", "Boil Water")
  - instruction: string (full detailed instruction)
  - estimated_time: string (e.g., "5 minutes", "10 seconds")
  - requires_heat: boolean (true if using stove, oven, or any heat source)
  - requires_knife: boolean (true if cutting, chopping, or slicing)

Keep instructions clear and concise. Each step should be a single, actionable instruction.
Mark safety-critical steps accurately."""
        
        user_prompt = f"Create a recipe for: {dish_name}"
        
        try:
            if not self.client:
                raise RuntimeError("LLM client not configured")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            try:
                recipe_data = json.loads(content)
            except Exception as parse_err:
                print("[RecipePlanner] JSON parse error from LLM:", parse_err)
                print("[RecipePlanner] Raw content was:", content)
                raise
            
            # Parse steps with safety detection
            steps = []
            for idx, step in enumerate(recipe_data["steps"]):
                # Detect safety requirements if not provided
                requires_heat = step.get("requires_heat", False)
                requires_knife = step.get("requires_knife", False)
                
                # Fallback detection if LLM didn't provide flags
                if not requires_heat:
                    requires_heat = self._detect_heat_requirement(step["instruction"])
                if not requires_knife:
                    requires_knife = self._detect_knife_requirement(step["instruction"])
                
                # Generate safety confirmation message
                safety_msg = None
                if requires_heat or requires_knife:
                    safety_msg = self._generate_safety_confirmation(requires_heat, requires_knife)
                
                steps.append(RecipeStep(
                    step_number=step.get("step_number", idx + 1),
                    title=step.get("title", f"Step {idx+1}"), # Map the title
                    instruction=step["instruction"],
                    estimated_time=step.get("estimated_time"),
                    requires_heat=requires_heat,
                    requires_knife=requires_knife,
                    safety_confirmation=safety_msg
                ))
            
            return Recipe(
                dish_name=recipe_data["dish_name"],
                total_steps=len(steps),
                ingredients=recipe_data["ingredients"],
                steps=steps
            )
        
        except Exception as e:
            # Log and fallback to a simple recipe if LLM fails
            print("[RecipePlanner] Error in create_recipe, using fallback:", repr(e))
            return self._create_fallback_recipe(dish_name)
    
    def _detect_heat_requirement(self, instruction: str) -> bool:
        """Detect if step requires heat using keyword matching."""
        heat_keywords = [
            "boil", "fry", "cook", "bake", "roast", "grill", "simmer",
            "sauté", "stir-fry", "heat", "warm", "stove", "oven", "pan"
        ]
        instruction_lower = instruction.lower()
        return any(keyword in instruction_lower for keyword in heat_keywords)
    
    def _detect_knife_requirement(self, instruction: str) -> bool:
        """Detect if step requires knife using keyword matching."""
        knife_keywords = [
            "cut", "chop", "slice", "dice", "mince", "julienne",
            "knife", "peel", "trim", "carve"
        ]
        instruction_lower = instruction.lower()
        return any(keyword in instruction_lower for keyword in knife_keywords)
    
    def _generate_safety_confirmation(self, requires_heat: bool, requires_knife: bool) -> str:
        """Generate appropriate safety confirmation message."""
        if requires_heat and requires_knife:
            return "This step involves heat and sharp objects. Please confirm you're ready."
        elif requires_heat:
            return "This step involves heat. Please confirm you're ready to use the stove/oven."
        elif requires_knife:
            return "This step involves sharp objects. Please confirm you're ready."
        return None
    
    def _create_fallback_recipe(self, dish_name: str) -> Recipe:
        """Create a simple fallback recipe with actual ingredients."""
        dish_lower = dish_name.lower()
        
        # Provide basic ingredients based on common dishes
        if "pasta" in dish_lower or "carbonara" in dish_lower:
            ingredients = [
                "200g pasta (spaghetti or fettuccine)",
                "100g pancetta or bacon, diced",
                "2 large eggs",
                "50g parmesan cheese, grated",
                "2 cloves garlic, minced",
                "Black pepper to taste",
                "Salt for pasta water"
            ]
            steps = [
                RecipeStep(step_number=1, instruction="Bring a large pot of salted water to a boil", estimated_time="5 minutes", requires_heat=True),
                RecipeStep(step_number=2, instruction="Cook the pasta according to package directions until al dente", estimated_time="10 minutes", requires_heat=True),
                RecipeStep(step_number=3, instruction="While pasta cooks, heat a large pan and cook the pancetta until crispy", estimated_time="5 minutes", requires_heat=True),
                RecipeStep(step_number=4, instruction="In a bowl, whisk together eggs, parmesan, and black pepper", estimated_time="2 minutes"),
                RecipeStep(step_number=5, instruction="Drain pasta, reserving some pasta water, then add to the pan with pancetta", estimated_time="2 minutes", requires_heat=True),
                RecipeStep(step_number=6, instruction="Remove from heat and quickly mix in the egg mixture, adding pasta water if needed", estimated_time="1 minute"),
                RecipeStep(step_number=7, instruction="Serve immediately with extra parmesan and pepper", estimated_time="1 minute")
            ]
        elif "omelette" in dish_lower or "omelet" in dish_lower:
            ingredients = [
                "3 large eggs",
                "2 tablespoons butter",
                "Salt and pepper to taste",
                "Optional: 30g cheese (cheddar, feta, or your choice)",
                "Optional: 2 tablespoons chopped herbs (chives, parsley)"
            ]
            steps = [
                RecipeStep(step_number=1, instruction="Crack eggs into a bowl and whisk with salt and pepper until frothy", estimated_time="2 minutes"),
                RecipeStep(step_number=2, instruction="Heat butter in a non-stick pan over medium heat until melted", estimated_time="2 minutes", requires_heat=True),
                RecipeStep(step_number=3, instruction="Pour eggs into the pan and let cook for 30 seconds without stirring", estimated_time="30 seconds", requires_heat=True),
                RecipeStep(step_number=4, instruction="Gently lift edges and tilt pan to let uncooked egg flow underneath", estimated_time="1 minute", requires_heat=True),
                RecipeStep(step_number=5, instruction="Add cheese or fillings if using, then fold in half", estimated_time="1 minute", requires_heat=True),
                RecipeStep(step_number=6, instruction="Cook for another 30 seconds until golden, then slide onto plate", estimated_time="1 minute", requires_heat=True)
            ]
        else:
            # Generic recipe
            ingredients = [
                "Main ingredients for " + dish_name,
                "Seasoning (salt, pepper)",
                "Cooking oil or butter",
                "Fresh herbs (optional)"
            ]
            steps = [
                RecipeStep(step_number=1, instruction=f"Prepare and gather all ingredients for {dish_name}", estimated_time="5 minutes"),
                RecipeStep(step_number=2, instruction=f"Follow traditional cooking method for {dish_name}", estimated_time="15 minutes", requires_heat=True),
                RecipeStep(step_number=3, instruction="Season to taste and serve hot", estimated_time="2 minutes")
            ]
        
        return Recipe(
            dish_name=dish_name,
            total_steps=len(steps),
            ingredients=ingredients,
            steps=steps
        )


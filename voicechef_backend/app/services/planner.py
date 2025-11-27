"""Recipe planning service using LLM (Groq or OpenAI)."""

import json
import re
from groq import Groq
from app.config import get_settings
from app.schemas import Recipe, RecipeStep


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
            self.client = Groq(api_key=api_key)
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
  - instruction: string (clear, single action per step)
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
        """Create a simple fallback recipe."""
        return Recipe(
            dish_name=dish_name,
            total_steps=3,
            ingredients=["Ingredients will be provided"],
            steps=[
                RecipeStep(
                    step_number=1,
                    instruction="Prepare your ingredients",
                    estimated_time="5 minutes"
                ),
                RecipeStep(
                    step_number=2,
                    instruction="Cook according to traditional methods",
                    estimated_time="20 minutes"
                ),
                RecipeStep(
                    step_number=3,
                    instruction="Serve and enjoy",
                    estimated_time="2 minutes"
                )
            ]
        )


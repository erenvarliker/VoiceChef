using System;
using System.Collections.Generic;
using UnityEngine;

namespace VoiceChef
{
    /// <summary>
    /// Data models matching the FastAPI backend schemas.
    /// These match the JSON structure returned by the backend.
    /// </summary>

    [Serializable]
    public class StartRecipeRequest
    {
        public string user_message;
        public string session_id;
    }

    [Serializable]
    public class InterpretRequest
    {
        public string session_id;
        public string user_message;
    }

    [Serializable]
    public class TranscribeResponse
    {
        public string text;
        public string language;
    }

    [Serializable]
    public class RecipeStep
    {
        public int step_number;
        public string instruction;
        public string estimated_time;
        public bool requires_heat;
        public bool requires_knife;
        public string safety_confirmation;
    }

    [Serializable]
    public class Recipe
    {
        public string dish_name;
        public int total_steps;
        public string[] ingredients;
        public RecipeStep[] steps;
    }

    [Serializable]
    public class StepData
    {
        public int step_number;
        public string instruction;
        public string estimated_time;
        public bool requires_heat;
        public bool requires_knife;
        public string safety_confirmation;
    }

    [Serializable]
    public class TimerData
    {
        public string timer_id;
        public int duration_seconds;
        public string started_at;
    }

    [Serializable]
    public class StartRecipeResponse
    {
        public string session_id;
        public string action;
        public Recipe recipe;
        public string tts_message;
    }

    [Serializable]
    public class InterpretResponse
    {
        public string session_id;
        public string action;
        public int current_step;
        public int total_steps;
        public StepData step_data;
        public string tts_message;
        public TimerData timer_data;
        public Dictionary<string, object> actions; // For complex actions
        public bool recipe_complete;
    }
}


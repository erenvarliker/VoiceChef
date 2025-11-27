# Unity Integration Guide

This document provides JSON examples and integration guidance for connecting Unity/HoloLens to the Python backend.

## API Base URL

```csharp
private const string API_BASE_URL = "http://localhost:8000";  // Development
// private const string API_BASE_URL = "https://your-server.com";  // Production
```

## 1. Starting a Recipe

### Unity C# HTTP Request

```csharp
using UnityEngine.Networking;
using System.Collections;

IEnumerator StartRecipe(string userMessage)
{
    string url = API_BASE_URL + "/start_recipe";
    
    // Create JSON request
    var requestData = new {
        user_message = userMessage,
        session_id = (string)null  // Backend will generate
    };
    
    string jsonData = JsonUtility.ToJson(requestData);
    
    // Send POST request
    using (UnityWebRequest request = UnityWebRequest.Post(url, "POST"))
    {
        byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(jsonData);
        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");
        
        yield return request.SendWebRequest();
        
        if (request.result == UnityWebRequest.Result.Success)
        {
            string responseJson = request.downloadHandler.text;
            RecipeResponse response = JsonUtility.FromJson<RecipeResponse>(responseJson);
            
            // Save session ID for future calls
            sessionId = response.session_id;
            
            // Speak the TTS message
            SpeakText(response.tts_message);
            
            // Display recipe UI
            DisplayRecipe(response.recipe);
        }
        else
        {
            Debug.LogError("Error: " + request.error);
        }
    }
}
```

### Example Response

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "recipe_created",
  "recipe": {
    "dish_name": "Simple Omelette",
    "total_steps": 5,
    "ingredients": [
      "3 large eggs",
      "2 tablespoons butter",
      "Salt and pepper to taste",
      "Optional: cheese, vegetables"
    ],
    "steps": [
      {
        "step_number": 1,
        "instruction": "Crack eggs into a bowl and whisk until well combined",
        "estimated_time": "1 minute",
        "requires_heat": false,
        "requires_knife": false,
        "safety_confirmation": null
      },
      {
        "step_number": 2,
        "instruction": "Heat butter in a non-stick pan over medium heat",
        "estimated_time": "2 minutes",
        "requires_heat": true,
        "requires_knife": false,
        "safety_confirmation": "This step involves heat. Please confirm you're ready to use the stove/oven."
      }
    ]
  },
  "tts_message": "Great! I've prepared a recipe for Simple Omelette. You'll need 3 large eggs, 2 tablespoons butter, Salt and pepper to taste, and 1 more. There are 5 steps in total. Say 'next' when you're ready to start!"
}
```

## 2. Interpreting Commands

### Unity C# HTTP Request

```csharp
IEnumerator InterpretCommand(string sessionId, string userMessage)
{
    string url = API_BASE_URL + "/interpret";
    
    var requestData = new {
        session_id = sessionId,
        user_message = userMessage
    };
    
    string jsonData = JsonUtility.ToJson(requestData);
    
    using (UnityWebRequest request = UnityWebRequest.Post(url, "POST"))
    {
        byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(jsonData);
        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");
        
        yield return request.SendWebRequest();
        
        if (request.result == UnityWebRequest.Result.Success)
        {
            string responseJson = request.downloadHandler.text;
            InterpretResponse response = JsonUtility.FromFrom<InterpretResponse>(responseJson);
            
            // Handle based on action type
            HandleAction(response);
        }
    }
}

void HandleAction(InterpretResponse response)
{
    // Always speak the TTS message
    SpeakText(response.tts_message);
    
    switch (response.action)
    {
        case "next_step":
            DisplayStep(response.step_data);
            UpdateProgress(response.current_step, response.total_steps);
            
            // Show safety confirmation if needed
            if (response.step_data.safety_confirmation != null)
            {
                ShowSafetyConfirmation(response.step_data.safety_confirmation);
            }
            break;
            
        case "repeat_step":
            DisplayStep(response.step_data);
            break;
            
        case "answer_question":
            DisplayAnswer(response.tts_message);
            break;
            
        case "timer_set":
            StartTimer(response.timer_data);
            break;
            
        case "recipe_complete":
            ShowCompletionUI();
            CelebrateCompletion();
            break;
            
        case "error":
            ShowErrorMessage(response.tts_message);
            break;
    }
}
```

## 3. Command Response Examples

### Next Step

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "next_step",
  "current_step": 1,
  "total_steps": 5,
  "step_data": {
    "step_number": 1,
    "instruction": "Crack eggs into a bowl and whisk until well combined",
    "estimated_time": "1 minute",
    "requires_heat": false,
    "requires_knife": false,
    "safety_confirmation": null
  },
  "tts_message": "Step 1: Crack eggs into a bowl and whisk until well combined. This should take about 1 minute.",
  "timer_data": null,
  "recipe_complete": false
}
```

### Timer Set

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "timer_set",
  "current_step": 3,
  "total_steps": 5,
  "timer_data": {
    "timer_id": "timer-123-abc",
    "duration_seconds": 180,
    "started_at": "2025-11-16T10:35:22.123456"
  },
  "tts_message": "Timer set for 3 minutes. I'll let you know when it's done!",
  "recipe_complete": false
}
```

### Answer Question

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "answer_question",
  "current_step": 2,
  "total_steps": 5,
  "step_data": null,
  "tts_message": "Yes, you can use olive oil instead of butter. It will give the omelette a slightly different flavor but works great!",
  "timer_data": null,
  "recipe_complete": false
}
```

### Recipe Complete

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "recipe_complete",
  "current_step": 5,
  "total_steps": 5,
  "step_data": null,
  "tts_message": "Congratulations! You've completed the Simple Omelette. Enjoy your meal!",
  "timer_data": null,
  "recipe_complete": true
}
```

### Error / Unclear

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "error",
  "current_step": 2,
  "total_steps": 5,
  "step_data": null,
  "tts_message": "I'm not sure what you want me to do. You can say: 'next' to move to the next step, 'repeat' to hear the current step again, 'set timer for X minutes' to start a timer, or ask me a question about the recipe.",
  "timer_data": null,
  "recipe_complete": false
}
```

## 4. C# Data Models

```csharp
[System.Serializable]
public class RecipeResponse
{
    public string session_id;
    public string action;
    public Recipe recipe;
    public string tts_message;
}

[System.Serializable]
public class Recipe
{
    public string dish_name;
    public int total_steps;
    public string[] ingredients;
    public RecipeStep[] steps;
}

[System.Serializable]
public class RecipeStep
{
    public int step_number;
    public string instruction;
    public string estimated_time;
    public bool requires_heat;
    public bool requires_knife;
    public string safety_confirmation;
}

[System.Serializable]
public class InterpretResponse
{
    public string session_id;
    public string action;
    public int current_step;
    public int total_steps;
    public StepData step_data;
    public string tts_message;
    public TimerData timer_data;
    public bool recipe_complete;
}

[System.Serializable]
public class StepData
{
    public int step_number;
    public string instruction;
    public string estimated_time;
    public bool requires_heat;
    public bool requires_knife;
    public string safety_confirmation;
}

[System.Serializable]
public class TimerData
{
    public string timer_id;
    public int duration_seconds;
    public string started_at;
}
```

## 5. UI Recommendations

### Safety Confirmation Display

When `step_data.requires_heat` or `step_data.requires_knife` is true:

1. Display safety icon (fire 🔥 or knife 🔪)
2. Show `safety_confirmation` message
3. Require user confirmation before proceeding
4. Speak the safety message via TTS

### Timer Display

When `timer_data` is received:

1. Parse `started_at` timestamp
2. Calculate remaining time from `duration_seconds`
3. Display countdown overlay
4. Play alert sound when complete
5. Optionally vibrate HoloLens

### Progress Indicator

Use `current_step` and `total_steps`:

```
Progress: Step 3 of 8 [████████░░░░░░░] 37%
```

### Step Display

```
┌─────────────────────────────────────┐
│ Step 2 of 5                    🔥   │
├─────────────────────────────────────┤
│ Heat butter in a non-stick pan      │
│ over medium heat                    │
│                                     │
│ ⏱ Estimated time: 2 minutes         │
│                                     │
│ ⚠️ This step involves heat.          │
│    Please confirm you're ready.     │
└─────────────────────────────────────┘
```

## 6. Error Handling

```csharp
void HandleHTTPError(UnityWebRequest request)
{
    if (request.responseCode == 404)
    {
        // Session not found - restart recipe
        Debug.LogError("Session expired. Please start a new recipe.");
        SpeakText("Your session has expired. Let's start a new recipe!");
    }
    else if (request.responseCode == 500)
    {
        // Server error
        Debug.LogError("Server error: " + request.error);
        SpeakText("I'm having trouble connecting. Please try again.");
    }
    else
    {
        // Other errors
        Debug.LogError("Network error: " + request.error);
        SpeakText("There was a connection problem. Please check your network.");
    }
}
```

## 7. Testing Without HoloLens

You can test the API using Unity Editor:

1. Start the Python backend: `uvicorn app.main:app --reload`
2. Use Unity's Play mode
3. Simulate voice commands with text input
4. View responses in Unity Console

Or use curl/Postman:

```bash
# Start recipe
curl -X POST http://localhost:8000/start_recipe \
  -H "Content-Type: application/json" \
  -d '{"user_message": "I want to cook an omelette", "session_id": null}'

# Interpret command
curl -X POST http://localhost:8000/interpret \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR_SESSION_ID", "user_message": "next"}'
```

## 8. Complete Workflow Example

```
1. User says: "I want to cook pasta"
   Unity → STT → "I want to cook pasta"
   Unity → POST /start_recipe
   Backend → Recipe JSON
   Unity → Display recipe + TTS

2. User says: "next"
   Unity → STT → "next"
   Unity → POST /interpret
   Backend → next_step action
   Unity → Display step 1 + TTS

3. User says: "set timer for 5 minutes"
   Unity → STT → "set timer for 5 minutes"
   Unity → POST /interpret
   Backend → timer_set action with timer_data
   Unity → Start countdown + TTS confirmation

4. User says: "can I use olive oil?"
   Unity → STT → "can I use olive oil?"
   Unity → POST /interpret
   Backend → answer_question action
   Unity → Display answer + TTS

5. Repeat until recipe_complete = true
```

## Notes

- Always save `session_id` after `/start_recipe`
- All subsequent calls to `/interpret` require the `session_id`
- The backend does NOT handle audio - Unity is responsible for STT/TTS
- Use Azure Speech SDK in Unity for voice input/output
- Test thoroughly with various commands and error scenarios





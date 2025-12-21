using System;
using System.Collections;
using UnityEngine;
using TMPro;

namespace VoiceChef
{
    /// <summary>
    /// Main controller for VoiceChef HoloGuide.
    /// Orchestrates audio recording, transcription, and backend communication.
    /// </summary>
    public class VoiceChefManager : MonoBehaviour
    {
        [Header("Components")]
        [Tooltip("Audio recorder component")]
        public AudioRecorder audioRecorder;

        [Tooltip("API client component")]
        public VoiceChefAPIClient apiClient;

        [Header("UI References")]
        [Tooltip("Text display for chef's messages")]
        public TextMeshPro chefMessageText;

        [Tooltip("Text display for current step")]
        public TextMeshPro stepText;

        [Tooltip("Text display for ingredients")]
        public TextMeshPro ingredientsText;

        [Header("Settings")]
        [Tooltip("Auto-play TTS audio")]
        public bool autoPlayTTS = true;

        // Current session state
        private string currentSessionId = null;
        private Recipe currentRecipe = null;
        private bool isWaitingForResponse = false;

        private void Start()
        {
            // Validate components
            if (audioRecorder == null)
            {
                audioRecorder = GetComponent<AudioRecorder>();
                if (audioRecorder == null)
                {
                    Debug.LogError("AudioRecorder component not found!");
                }
            }

            if (apiClient == null)
            {
                apiClient = GetComponent<VoiceChefAPIClient>();
                if (apiClient == null)
                {
                    Debug.LogError("VoiceChefAPIClient component not found!");
                }
            }

            // Subscribe to events
            if (audioRecorder != null)
            {
                audioRecorder.OnRecordingComplete += HandleRecordingComplete;
                audioRecorder.OnError += HandleError;
            }

            if (apiClient != null)
            {
                apiClient.OnTranscriptionComplete += HandleTranscription;
                apiClient.OnRecipeStarted += HandleRecipeStarted;
                apiClient.OnCommandInterpreted += HandleCommandInterpreted;
                apiClient.OnError += HandleError;
            }

            // Check backend health
            StartCoroutine(CheckBackendHealth());
        }

        /// <summary>
        /// Check if backend is available.
        /// </summary>
        private IEnumerator CheckBackendHealth()
        {
            if (apiClient == null) yield break;

            bool isHealthy = false;
            yield return StartCoroutine(apiClient.CheckHealth((healthy) => { isHealthy = healthy; }));

            if (isHealthy)
            {
                Debug.Log("✅ Backend is available");
                UpdateChefMessage("VoiceChef is ready! Say 'I want to cook...' to start.");
            }
            else
            {
                Debug.LogError("❌ Backend is not available");
                UpdateChefMessage("Error: Cannot connect to backend. Check if server is running.");
            }
        }

        /// <summary>
        /// Start recording audio (called by voice command or button).
        /// </summary>
        public void StartRecording()
        {
            if (isWaitingForResponse)
            {
                Debug.LogWarning("Waiting for backend response. Please wait...");
                return;
            }

            if (audioRecorder == null)
            {
                Debug.LogError("AudioRecorder not available!");
                return;
            }

            audioRecorder.StartRecording();
            UpdateChefMessage("🎤 Listening...");
        }

        /// <summary>
        /// Stop recording and process audio (called by voice command or button).
        /// </summary>
        public void StopRecording()
        {
            if (audioRecorder == null || !audioRecorder.IsRecording())
            {
                return;
            }

            audioRecorder.StopRecording();
            UpdateChefMessage("⏳ Processing...");
        }

        /// <summary>
        /// Handle completed audio recording.
        /// </summary>
        private void HandleRecordingComplete(AudioClip clip)
        {
            if (clip == null || clip.length < 0.1f)
            {
                HandleError("Recording too short or empty");
                return;
            }

            Debug.Log($"Recording complete: {clip.length}s");
            isWaitingForResponse = true;

            // Transcribe audio
            StartCoroutine(apiClient.TranscribeAudio(clip, (response) =>
            {
                if (response != null && !string.IsNullOrEmpty(response.text))
                {
                    HandleTranscription(response.text);
                }
                else
                {
                    HandleError("Transcription failed or returned empty text");
                    isWaitingForResponse = false;
                }
            }));
        }

        /// <summary>
        /// Handle transcription result.
        /// </summary>
        private void HandleTranscription(string text)
        {
            Debug.Log($"Transcribed: '{text}'");

            if (string.IsNullOrEmpty(currentSessionId))
            {
                // No active session - start a new recipe
                StartCoroutine(apiClient.StartRecipe(text, null, (response) =>
                {
                    if (response != null)
                    {
                        HandleRecipeStarted(response);
                    }
                    else
                    {
                        HandleError("Failed to start recipe");
                        isWaitingForResponse = false;
                    }
                }));
            }
            else
            {
                // Active session - interpret command
                StartCoroutine(apiClient.InterpretCommand(currentSessionId, text, (response) =>
                {
                    if (response != null)
                    {
                        HandleCommandInterpreted(response);
                    }
                    else
                    {
                        HandleError("Failed to interpret command");
                        isWaitingForResponse = false;
                    }
                }));
            }
        }

        /// <summary>
        /// Handle recipe started response.
        /// </summary>
        private void HandleRecipeStarted(StartRecipeResponse response)
        {
            currentSessionId = response.session_id;
            currentRecipe = response.recipe;
            isWaitingForResponse = false;

            Debug.Log($"Recipe started: {response.recipe.dish_name}");

            // Update UI
            UpdateChefMessage(response.tts_message);
            UpdateIngredients(response.recipe.ingredients);
            UpdateStepText($"Ready to start! Say 'next' to begin step 1 of {response.recipe.total_steps}");

            // Play TTS if enabled
            if (autoPlayTTS)
            {
                PlayTTS(response.tts_message);
            }
        }

        /// <summary>
        /// Handle command interpretation response.
        /// </summary>
        private void HandleCommandInterpreted(InterpretResponse response)
        {
            isWaitingForResponse = false;

            Debug.Log($"Command interpreted: {response.action}");

            // Update UI based on action
            UpdateChefMessage(response.tts_message);

            if (response.step_data != null)
            {
                UpdateStepText($"Step {response.current_step}/{response.total_steps}: {response.step_data.instruction}");
            }

            if (response.recipe_complete)
            {
                UpdateStepText("🎉 Recipe complete! Great job!");
            }

            // Handle timer if set
            if (response.timer_data != null)
            {
                StartTimer(response.timer_data);
            }

            // Play TTS if enabled
            if (autoPlayTTS)
            {
                PlayTTS(response.tts_message);
            }
        }

        /// <summary>
        /// Update chef message display.
        /// </summary>
        private void UpdateChefMessage(string message)
        {
            if (chefMessageText != null)
            {
                chefMessageText.text = message;
            }
            Debug.Log($"Chef: {message}");
        }

        /// <summary>
        /// Update step text display.
        /// </summary>
        private void UpdateStepText(string text)
        {
            if (stepText != null)
            {
                stepText.text = text;
            }
        }

        /// <summary>
        /// Update ingredients display.
        /// </summary>
        private void UpdateIngredients(string[] ingredients)
        {
            if (ingredientsText != null && ingredients != null)
            {
                ingredientsText.text = "Ingredients:\n" + string.Join("\n", ingredients);
            }
        }

        /// <summary>
        /// Play TTS audio (using Unity's built-in TTS or external service).
        /// </summary>
        private void PlayTTS(string text)
        {
            // TODO: Implement Unity TTS or use Windows Speech API for HoloLens
            // For now, just log
            Debug.Log($"TTS: {text}");
        }

        /// <summary>
        /// Start a timer from timer data.
        /// </summary>
        private void StartTimer(TimerData timerData)
        {
            // TODO: Implement timer UI and countdown
            Debug.Log($"Timer started: {timerData.duration_seconds}s");
        }

        /// <summary>
        /// Handle errors.
        /// </summary>
        private void HandleError(string error)
        {
            Debug.LogError($"VoiceChef Error: {error}");
            UpdateChefMessage($"Error: {error}");
            isWaitingForResponse = false;
        }

        private void OnDestroy()
        {
            // Unsubscribe from events
            if (audioRecorder != null)
            {
                audioRecorder.OnRecordingComplete -= HandleRecordingComplete;
                audioRecorder.OnError -= HandleError;
            }

            if (apiClient != null)
            {
                apiClient.OnTranscriptionComplete -= HandleTranscription;
                apiClient.OnRecipeStarted -= HandleRecipeStarted;
                apiClient.OnCommandInterpreted -= HandleCommandInterpreted;
                apiClient.OnError -= HandleError;
            }
        }
    }
}


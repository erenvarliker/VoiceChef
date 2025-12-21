using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using System.IO;

namespace VoiceChef
{
    /// <summary>
    /// HTTP client for VoiceChef backend API.
    /// Handles all communication with the FastAPI backend.
    /// </summary>
    public class VoiceChefAPIClient : MonoBehaviour
    {
        [Header("Backend Configuration")]
        [Tooltip("Backend API URL (e.g., http://localhost:8000)")]
        public string backendUrl = "http://localhost:8000";

        [Tooltip("Request timeout in seconds")]
        public int timeoutSeconds = 30;

        // Events for Unity components to subscribe to
        public event Action<string> OnTranscriptionComplete;
        public event Action<StartRecipeResponse> OnRecipeStarted;
        public event Action<InterpretResponse> OnCommandInterpreted;
        public event Action<string> OnError;

        /// <summary>
        /// Check if backend is available.
        /// </summary>
        public IEnumerator CheckHealth(Action<bool> callback)
        {
            string url = $"{backendUrl}/";
            using (UnityWebRequest request = UnityWebRequest.Get(url))
            {
                request.timeout = timeoutSeconds;
                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    callback?.Invoke(true);
                }
                else
                {
                    Debug.LogError($"Backend health check failed: {request.error}");
                    callback?.Invoke(false);
                }
            }
        }

        /// <summary>
        /// Transcribe audio file to text using Whisper.
        /// </summary>
        /// <param name="audioClip">Audio clip to transcribe</param>
        public IEnumerator TranscribeAudio(AudioClip audioClip, Action<TranscribeResponse> callback)
        {
            // Convert AudioClip to WAV bytes
            byte[] audioData = EncodeToWAV(audioClip);
            
            string url = $"{backendUrl}/transcribe";
            
            // Create multipart form data
            List<IMultipartFormSection> formData = new List<IMultipartFormSection>();
            formData.Add(new MultipartFormFileSection("audio_file", audioData, "audio.wav", "audio/wav"));

            using (UnityWebRequest request = UnityWebRequest.Post(url, formData))
            {
                request.timeout = timeoutSeconds;
                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    try
                    {
                        TranscribeResponse response = JsonUtility.FromJson<TranscribeResponse>(request.downloadHandler.text);
                        OnTranscriptionComplete?.Invoke(response.text);
                        callback?.Invoke(response);
                    }
                    catch (Exception e)
                    {
                        Debug.LogError($"Failed to parse transcription response: {e}");
                        OnError?.Invoke($"Parse error: {e.Message}");
                        callback?.Invoke(null);
                    }
                }
                else
                {
                    Debug.LogError($"Transcription failed: {request.error}");
                    OnError?.Invoke($"Transcription error: {request.error}");
                    callback?.Invoke(null);
                }
            }
        }

        /// <summary>
        /// Start a new recipe from natural language input.
        /// </summary>
        public IEnumerator StartRecipe(string userMessage, string sessionId = null, Action<StartRecipeResponse> callback = null)
        {
            string url = $"{backendUrl}/start_recipe";
            
            StartRecipeRequest requestData = new StartRecipeRequest
            {
                user_message = userMessage,
                session_id = sessionId
            };

            string jsonData = JsonUtility.ToJson(requestData);
            byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonData);

            using (UnityWebRequest request = new UnityWebRequest(url, "POST"))
            {
                request.uploadHandler = new UploadHandlerRaw(bodyRaw);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");
                request.timeout = timeoutSeconds;

                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    try
                    {
                        StartRecipeResponse response = JsonUtility.FromJson<StartRecipeResponse>(request.downloadHandler.text);
                        OnRecipeStarted?.Invoke(response);
                        callback?.Invoke(response);
                    }
                    catch (Exception e)
                    {
                        Debug.LogError($"Failed to parse start recipe response: {e}");
                        OnError?.Invoke($"Parse error: {e.Message}");
                        callback?.Invoke(null);
                    }
                }
                else
                {
                    Debug.LogError($"Start recipe failed: {request.error}");
                    OnError?.Invoke($"Start recipe error: {request.error}");
                    callback?.Invoke(null);
                }
            }
        }

        /// <summary>
        /// Interpret user command during cooking.
        /// </summary>
        public IEnumerator InterpretCommand(string sessionId, string userMessage, Action<InterpretResponse> callback = null)
        {
            string url = $"{backendUrl}/interpret";
            
            InterpretRequest requestData = new InterpretRequest
            {
                session_id = sessionId,
                user_message = userMessage
            };

            string jsonData = JsonUtility.ToJson(requestData);
            byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonData);

            using (UnityWebRequest request = new UnityWebRequest(url, "POST"))
            {
                request.uploadHandler = new UploadHandlerRaw(bodyRaw);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");
                request.timeout = timeoutSeconds;

                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    try
                    {
                        InterpretResponse response = JsonUtility.FromJson<InterpretResponse>(request.downloadHandler.text);
                        OnCommandInterpreted?.Invoke(response);
                        callback?.Invoke(response);
                    }
                    catch (Exception e)
                    {
                        Debug.LogError($"Failed to parse interpret response: {e}");
                        OnError?.Invoke($"Parse error: {e.Message}");
                        callback?.Invoke(null);
                    }
                }
                else
                {
                    Debug.LogError($"Interpret command failed: {request.error}");
                    OnError?.Invoke($"Interpret error: {request.error}");
                    callback?.Invoke(null);
                }
            }
        }

        /// <summary>
        /// Convert AudioClip to WAV byte array.
        /// </summary>
        private byte[] EncodeToWAV(AudioClip clip)
        {
            float[] samples = new float[clip.samples * clip.channels];
            clip.GetData(samples, 0);

            // Convert float samples to 16-bit PCM
            short[] intData = new short[samples.Length];
            for (int i = 0; i < samples.Length; i++)
            {
                intData[i] = (short)(samples[i] * 32767f);
            }

            // Create WAV header
            int hz = clip.frequency;
            int channels = clip.channels;
            int samples_count = intData.Length;
            int sample_rate = hz;
            int num_of_channels = channels;
            int bits_per_sample = 16;
            int header_size = 44;
            int file_size = header_size + (samples_count * num_of_channels * bits_per_sample / 8);

            using (MemoryStream stream = new MemoryStream())
            {
                using (BinaryWriter writer = new BinaryWriter(stream))
                {
                    // WAV header
                    writer.Write("RIFF".ToCharArray());
                    writer.Write(file_size - 8);
                    writer.Write("WAVE".ToCharArray());
                    writer.Write("fmt ".ToCharArray());
                    writer.Write(16); // fmt chunk size
                    writer.Write((ushort)1); // audio format (1 = PCM)
                    writer.Write((ushort)num_of_channels);
                    writer.Write(sample_rate);
                    writer.Write(sample_rate * num_of_channels * bits_per_sample / 8); // byte rate
                    writer.Write((ushort)(num_of_channels * bits_per_sample / 8)); // block align
                    writer.Write((ushort)bits_per_sample);
                    writer.Write("data".ToCharArray());
                    writer.Write(samples_count * num_of_channels * bits_per_sample / 8);

                    // Write audio data
                    foreach (short sample in intData)
                    {
                        writer.Write(sample);
                    }
                }
                return stream.ToArray();
            }
        }
    }
}


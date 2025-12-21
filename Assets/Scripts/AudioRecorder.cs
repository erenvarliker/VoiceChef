using System;
using System.Collections;
using UnityEngine;

namespace VoiceChef
{
    /// <summary>
    /// Records audio from microphone for HoloLens.
    /// Handles microphone permissions and audio capture.
    /// </summary>
    public class AudioRecorder : MonoBehaviour
    {
        [Header("Recording Settings")]
        [Tooltip("Maximum recording duration in seconds")]
        public int maxRecordingTime = 10;

        [Tooltip("Sample rate for recording (16000 Hz recommended for Whisper)")]
        public int sampleRate = 16000;

        private AudioClip recording;
        private bool isRecording = false;
        private string microphoneDevice = null;

        // Events
        public event Action<AudioClip> OnRecordingComplete;
        public event Action<string> OnError;

        private void Start()
        {
            // Get default microphone device
            if (Microphone.devices.Length > 0)
            {
                microphoneDevice = Microphone.devices[0];
                Debug.Log($"Using microphone: {microphoneDevice}");
            }
            else
            {
                Debug.LogWarning("No microphone devices found!");
            }
        }

        /// <summary>
        /// Start recording audio from microphone.
        /// </summary>
        public void StartRecording()
        {
            if (isRecording)
            {
                Debug.LogWarning("Already recording!");
                return;
            }

            if (string.IsNullOrEmpty(microphoneDevice))
            {
                OnError?.Invoke("No microphone available");
                return;
            }

            // Stop any existing recording
            if (recording != null)
            {
                Destroy(recording);
            }

            try
            {
                recording = Microphone.Start(microphoneDevice, false, maxRecordingTime, sampleRate);
                isRecording = true;
                Debug.Log("Recording started...");
            }
            catch (Exception e)
            {
                Debug.LogError($"Failed to start recording: {e}");
                OnError?.Invoke($"Recording error: {e.Message}");
            }
        }

        /// <summary>
        /// Stop recording and return the AudioClip.
        /// </summary>
        public void StopRecording()
        {
            if (!isRecording)
            {
                Debug.LogWarning("Not currently recording!");
                return;
            }

            if (recording == null)
            {
                OnError?.Invoke("No recording available");
                return;
            }

            // Get the actual length of the recording
            int position = Microphone.GetPosition(microphoneDevice);
            int recordingLength = position;

            // Create a new clip with the actual recorded length
            AudioClip trimmedClip = AudioClip.Create(
                "Recording",
                recordingLength,
                recording.channels,
                recording.frequency,
                false
            );

            float[] data = new float[recordingLength * recording.channels];
            recording.GetData(data, 0);
            trimmedClip.SetData(data, 0);

            // Stop microphone
            Microphone.End(microphoneDevice);
            isRecording = false;

            // Clean up old recording
            Destroy(recording);
            recording = trimmedClip;

            Debug.Log($"Recording stopped. Length: {trimmedClip.length}s");
            OnRecordingComplete?.Invoke(trimmedClip);
        }

        /// <summary>
        /// Check if currently recording.
        /// </summary>
        public bool IsRecording()
        {
            return isRecording;
        }

        /// <summary>
        /// Get current recording duration.
        /// </summary>
        public float GetRecordingDuration()
        {
            if (!isRecording || recording == null)
                return 0f;

            int position = Microphone.GetPosition(microphoneDevice);
            return position / (float)recording.frequency;
        }

        private void OnDestroy()
        {
            if (isRecording)
            {
                Microphone.End(microphoneDevice);
            }

            if (recording != null)
            {
                Destroy(recording);
            }
        }
    }
}


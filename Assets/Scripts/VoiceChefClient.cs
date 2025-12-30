using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using UI;

public class VoiceChefClient : MonoBehaviour
{
    [Header("Backend Config")]
    public string backendUrl = "http://localhost:8000";
    public string sessionId = "holo-test";
    public float pollInterval = 1.0f;

    [Header("UI Groups")]
    public GameObject introGroup;
    public GameObject cookingGroup; // The new group you created for Step/Timer/Warning

    [Header("UI Components")]
    public IntroCardUI introCard;
    public IngredientListUI ingredientList;
    public StepCardUI stepCard;
    public SmartTimerUIController timerUI;
    public WarningWindowController warningUI;

    private bool _isPolling = false;
    private string _lastLoadedDish = "";

    void Start()
    {
        // 1. FIX: Hide Warning Window immediately on start
        if (warningUI != null) warningUI.gameObject.SetActive(false);

        // 2. FIX: Hide Timer immediately on start
        if (timerUI != null) timerUI.HideTimerUI();

        StartCoroutine(PollRoutine());
    }

    IEnumerator PollRoutine()
    {
        _isPolling = true;
        while (_isPolling)
        {
            string url = $"{backendUrl}/session/{sessionId}/status";
            using (UnityWebRequest request = UnityWebRequest.Get(url))
            {
                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    string json = request.downloadHandler.text;
                    SessionStatus status = JsonUtility.FromJson<SessionStatus>(json);
                    UpdateUI(status);
                }
            }
            yield return new WaitForSeconds(pollInterval);
        }
    }

    void UpdateUI(SessionStatus status)
    {
        // --- PHASE 1: INTRO ---
        if (status.current_step_index == -1)
        {
            if (!introGroup.activeSelf) introGroup.SetActive(true);
            if (cookingGroup.activeSelf) cookingGroup.SetActive(false);

            if (introCard != null) introCard.SetText(status.dish_name);

            if (ingredientList != null && status.dish_name != _lastLoadedDish && status.ingredients != null)
            {
                _lastLoadedDish = status.dish_name;
                // Unity requires a List<string>, not string[]
                List<string> ingList = new List<string>(status.ingredients);
                ingredientList.LoadIngredients(ingList);
            }
        }
        // --- PHASE 2: COOKING ---
        else
        {
            if (introGroup.activeSelf) introGroup.SetActive(false);
            if (!cookingGroup.activeSelf) cookingGroup.SetActive(true);

            // 3. FIX: Use the new "Title" from backend if available
            if (status.current_step != null)
            {
                // If backend provides a title (e.g., "Chop Onions"), use it. 
                // Otherwise fall back to "Step X".
                string stepTitle = string.IsNullOrEmpty(status.current_step.title)
                    ? $"Step {status.current_step.step_number}"
                    : $"Step {status.current_step.step_number}: {status.current_step.title}";

                stepCard.SetStep(stepTitle, status.current_step.instruction, status.current_step.step_number % 6);
            }
            else
            {
                stepCard.SetStep("Recipe Complete", "Enjoy your meal!", 0);
            }

            // --- TIMER LOGIC ---
            if (timerUI != null)
            {
                if (status.timers != null && status.timers.Length > 0)
                {
                    // Show timer if hidden
                    if (!timerUI.timerUI.activeSelf) timerUI.ShowTimerUI();

                    // Update time
                    timerUI.StartTimer(status.timers[0].remaining_seconds);
                }
                else
                {
                    // Hide timer if no active timers
                    if (timerUI.timerUI.activeSelf) timerUI.HideTimerUI();
                }
            }

            // --- WARNING LOGIC ---
            // Inside UpdateUI method...

            // --- WARNING LOGIC ---
            if (warningUI != null)
            {
                // If backend sends a warning string (fire/cut), show the UI
                if (!string.IsNullOrEmpty(status.active_warning))
                {
                    if (!warningUI.gameObject.activeSelf) warningUI.gameObject.SetActive(true);

                    // Call specific methods on your controller based on type
                    if (status.active_warning.Contains("fire"))
                        warningUI.ShowFireWarning();
                    else if (status.active_warning.Contains("cut"))
                        warningUI.ShowDeepCutWarning();
                    else
                        warningUI.ShowMinimalCutWarning(); // Default fallback
                }
                else
                {
                    // No warning active, hide the window
                    if (warningUI.gameObject.activeSelf) warningUI.gameObject.SetActive(false);
                }
            }
        }
    }
}
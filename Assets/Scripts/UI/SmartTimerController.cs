using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System.Text.RegularExpressions;

public class SmartTimerUIController : MonoBehaviour
{
    [Header("UI Elements")]
    public GameObject timerUI;    
    public Image fillRing;        
    public TMP_Text timerText;    

    private float totalTime;
    private float remainingTime;
    private bool isRunning = false;
    private bool timerStarted = false;   // NEW: ensures timer starts only once

    void Start()
    {
        timerUI.SetActive(false); 
    }

    void Update()
    {
        // ============================
        // PRESS S = SHOW + START TIMER
        // ============================
        if (Input.GetKeyDown(KeyCode.S))
        {
            ToggleTimerUI();

            // Start the timer only the FIRST time S is pressed
            if (!timerStarted)
            {
                StartTimerFromText("00:30");  // starting test time
                timerStarted = true;
            }
        }

        // ============================
        // TIMER COUNTDOWN
        // ============================
        if (!isRunning) return;

        remainingTime -= Time.deltaTime;

        if (remainingTime <= 0)
        {
            remainingTime = 0;
            isRunning = false;
        }

        UpdateUI();
    }

    // SHOW / HIDE UI --------------------------------------------
    public void ShowTimerUI() => timerUI.SetActive(true);
    public void HideTimerUI() => timerUI.SetActive(false);

    public void ToggleTimerUI()
    {
        timerUI.SetActive(!timerUI.activeSelf);
    }

    // Parse MM:SS ------------------------------------------------
    public void StartTimerFromText(string timeString)
    {
        Match match = Regex.Match(timeString, @"^(\d{1,2}):(\d{2})$");

        if (!match.Success)
        {
            Debug.LogWarning("Invalid time format. Use MM:SS only.");
            return;
        }

        int minutes = int.Parse(match.Groups[1].Value);
        int seconds = int.Parse(match.Groups[2].Value);

        float totalSeconds = minutes * 60 + seconds;
        StartTimer(totalSeconds);
    }

    // Start timer ------------------------------------------------
    public void StartTimer(float seconds)
    {
        if (seconds <= 0) return;

        totalTime = seconds;
        remainingTime = seconds;
        isRunning = true;

        UpdateUI();
    }

    // Update ring + text ----------------------------------------
    private void UpdateUI()
    {
        if (totalTime > 0)
            fillRing.fillAmount = remainingTime / totalTime;

        int m = Mathf.FloorToInt(remainingTime / 60f);
        int s = Mathf.FloorToInt(remainingTime % 60f);

        timerText.text = $"{m:00}:{s:00}";
    }
}

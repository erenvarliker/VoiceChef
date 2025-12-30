using UnityEngine;
using TMPro;
using UnityEngine.InputSystem; // IMPORTANT for MRTK / New Input System

public class WarningWindowController : MonoBehaviour
{
    [Header("UI Reference")]
    [SerializeField] private TMP_Text warningText;

    [Header("Font Settings")]
    [SerializeField] private float warningFontSize = 36f;

    [Header("Warning Messages")]
    [TextArea(2, 4)]
    public string fireMessage =
        "🔥 Fire Detected!\n\nPlease move away from the area and call 911.";

    [TextArea(2, 4)]
    public string minimalCutMessage =
        "✂️ Minimal Cut Detected!\n\nPlease remove the device and use first-aid.";

    [TextArea(2, 4)]
    public string deepCutMessage =
        "🩸 Deep Cut Detected!\n\nPlease remove the device and call 911.";

    private void Awake()
    {
        if (warningText == null)
        {
            warningText = GetComponentInChildren<TMP_Text>();
        }
    }

    private void Start()
    {
        ApplyText(
            "Press 1, 2, or 3 to trigger a warning."
        );
    }

    private void Update()
    {
        if (Keyboard.current == null)
            return;

        if (Keyboard.current.digit1Key.wasPressedThisFrame)
        {
            ShowFireWarning();
        }
        else if (Keyboard.current.digit2Key.wasPressedThisFrame)
        {
            ShowMinimalCutWarning();
        }
        else if (Keyboard.current.digit3Key.wasPressedThisFrame)
        {
            ShowDeepCutWarning();
        }
    }

    // =============================
    // WARNING METHODS
    // =============================

    public void ShowFireWarning()
    {
        ApplyText(fireMessage);
    }

    public void ShowMinimalCutWarning()
    {
        ApplyText(minimalCutMessage);
    }

    public void ShowDeepCutWarning()
    {
        ApplyText(deepCutMessage);
    }

    // =============================
    // HELPER
    // =============================

    private void ApplyText(string message)
    {
        warningText.fontSize = warningFontSize; // ✅ always 36
        warningText.text = message;
    }
}

using UnityEngine;
using TMPro;

public class IngredientPanelAutoHeight : MonoBehaviour
{
    [Header("References")]
    public RectTransform panelRect;   // The panel you want to resize (purple card)
    public TMP_Text listText;         // The TMP that contains the ingredients list

    [Header("Padding (pixels in Canvas space)")]
    public float topPadding = 90f;    // space for title area
    public float bottomPadding = 20f; // space below list

    [Header("Clamp Height")]
    public float minHeight = 140f;
    public float maxHeight = 600f;

    void Reset()
    {
        panelRect = GetComponent<RectTransform>();
    }

    void OnEnable()
    {
        TMPro_EventManager.TEXT_CHANGED_EVENT.Add(OnTextChanged);
        Rebuild();
    }

    void OnDisable()
    {
        TMPro_EventManager.TEXT_CHANGED_EVENT.Remove(OnTextChanged);
    }

    void OnTextChanged(Object changedObj)
    {
        if (changedObj == listText) Rebuild();
    }

    public void Rebuild()
    {
        if (panelRect == null || listText == null) return;

        // Make sure TMP has up-to-date layout values
        Canvas.ForceUpdateCanvases();

        float listPreferred = listText.preferredHeight;
        float target = listPreferred + topPadding + bottomPadding;
        target = Mathf.Clamp(target, minHeight, maxHeight);

        // Resize height only (keep width)
        panelRect.sizeDelta = new Vector2(panelRect.sizeDelta.x, target);
    }

    // Optional helper: call this when backend sets ingredients
    public void SetIngredients(string ingredientsMultiline)
    {
        if (listText == null) return;
        listText.text = ingredientsMultiline;
        Rebuild();
    }
}

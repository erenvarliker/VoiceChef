using UnityEngine;
using TMPro;

public class StepCardUI : MonoBehaviour
{
    public TextMeshProUGUI stepTitle;
    public TextMeshProUGUI stepDescription;

    public void SetStep(string title, string desc)
    {
        stepTitle.text = title;
        stepDescription.text = desc;
    }
}

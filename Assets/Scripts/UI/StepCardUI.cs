using UnityEngine;
using UnityEngine.UI;
using TMPro;

namespace UI
{
    public class StepCardUI : MonoBehaviour
    {
        [Header("UI Refs")]
        public Image bgImage;      // drag BG (Image) here
        public TMP_Text titleText; // drag TMP title here (can reuse your Label)
        public TMP_Text descText;  // optional second TMP for description

        [Header("Background States (ordered)")]
        public Sprite[] stepSprites; // StepCard1..StepCard6 (or however many)

        // Called by CardManager.ShowStepCard(...)
        public void SetStep(string title = null, string desc = null, int spriteIndex = -1)
        {
            if (titleText && title != null) titleText.text = title;
            if (descText && desc != null) descText.text = desc;

            if (spriteIndex >= 0)
                SetBackground(spriteIndex);
        }

        public void SetBackground(int idx)
        {
            if (!bgImage || stepSprites == null || stepSprites.Length == 0) return;

            idx = Mathf.Clamp(idx, 0, stepSprites.Length - 1);
            bgImage.sprite = stepSprites[idx];
        }
    }
}

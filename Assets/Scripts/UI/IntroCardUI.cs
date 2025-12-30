using UnityEngine;
using TMPro;

namespace UI
{
    public class IntroCardUI : MonoBehaviour
    {
        public TextMeshProUGUI titleText;

        public void SetText(string value)
        {
            titleText.text = value;
        }
    }
}

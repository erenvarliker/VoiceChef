using UnityEngine;
using TMPro;

namespace UI
{
    public class IngredientCardUI : MonoBehaviour
    {
        // A big TMP text box that lists ingredients
        public TextMeshProUGUI ingredientList;

        // Called by CardManager to update ingredients dynamically
        public void SetIngredients(string list)
        {
            ingredientList.text = list;
        }
    }
}

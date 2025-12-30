using UnityEngine;
using UI;



namespace Managers
{
    public class CardManager : MonoBehaviour
    {
        [Header("Intro Card")]
        public GameObject introCard;
        public IntroCardUI introUI;

        [Header("Ingredient Card")]
        public GameObject ingredientCard;
        public IngredientCardUI ingredientUI;

        [Header("Step Cards")]
        public GameObject[] stepCards;
        public StepCardUI[] stepUIs;

        private int currentStep = 0;

        void DisableAll()
        {
            if (introCard) introCard.SetActive(false);
            if (ingredientCard) ingredientCard.SetActive(false);

            foreach (var s in stepCards)
                if (s) s.SetActive(false);
        }

        public void ShowIntroCard(string text = null)
        {
            DisableAll();
            introCard.SetActive(true);
            if (text != null)
                introUI.SetText(text);
        }

        public void ShowIngredientCard(string ingredients = null)
        {
            DisableAll();
            ingredientCard.SetActive(true);
            if (ingredients != null)
                ingredientUI.SetIngredients(ingredients);
        }

        public void ShowStepCard(int index, string title = null, string desc = null)
        {
            DisableAll();
            currentStep = index;
            stepCards[index].SetActive(true);

            if (title != null || desc != null)
                stepUIs[index].SetStep(title, desc);
        }

        public void NextStep()
        {
            if (currentStep < stepCards.Length - 1)
            {
                currentStep++;
                ShowStepCard(currentStep);
            }
        }

        public void PreviousStep()
        {
            if (currentStep > 0)
            {
                currentStep--;
                ShowStepCard(currentStep);
            }
        }

        public void RepeatStep()
        {
            ShowStepCard(currentStep);
        }
    }
}

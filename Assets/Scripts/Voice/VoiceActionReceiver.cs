using UnityEngine;
using SimpleJSON;
using Managers;

public class VoiceActionReceiver : MonoBehaviour
{
    public CardManager cardManager;

    public void OnReceive(string json)
    {
        var data = JSON.Parse(json);

        string type = data["type"].Value;
        Debug.Log("Voice Action Received: " + type);

        switch (type)
        {
            case "show_intro_card":
                cardManager.ShowIntroCard();
                break;

            case "show_ingredient_card":
                cardManager.ShowIngredientCard();
                break;

            case "show_step_card":
                int stepIndex = data["parameters"]["step_index"].AsInt;
                cardManager.ShowStepCard(stepIndex);
                break;

            case "next_step":
                cardManager.NextStep();
                break;

            case "previous_step":
                cardManager.PreviousStep();
                break;

            case "repeat_step":
                cardManager.RepeatStep();
                break;

            case "set_timer":
                Debug.Log("Timer action received — connect SmartTimer later");
                break;

            default:
                Debug.LogWarning("Unknown action: " + type);
                break;
        }
    }
}

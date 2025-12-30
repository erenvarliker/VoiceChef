using UnityEngine;
using UI;

public class StepCardTester : MonoBehaviour
{
    public StepCardUI card;          // drag your StepCard here
    public int spriteIndex = 0;

    void Update()
    {
        if (card == null) return;

        // 1..6 sets different background sprites
        if (Input.GetKeyDown(KeyCode.Alpha1)) Set(0);
        if (Input.GetKeyDown(KeyCode.Alpha2)) Set(1);
        if (Input.GetKeyDown(KeyCode.Alpha3)) Set(2);
        if (Input.GetKeyDown(KeyCode.Alpha4)) Set(3);
        if (Input.GetKeyDown(KeyCode.Alpha5)) Set(4);
        if (Input.GetKeyDown(KeyCode.Alpha6)) Set(5);

        // N / P to move next/prev
        if (Input.GetKeyDown(KeyCode.N)) Set(spriteIndex + 1);
        if (Input.GetKeyDown(KeyCode.P)) Set(spriteIndex - 1);
    }

    void Set(int idx)
    {
        spriteIndex = Mathf.Clamp(idx, 0, 5);
        card.SetStep($"Step {spriteIndex + 1}: Test Title", "Test desc", spriteIndex);
    }
}

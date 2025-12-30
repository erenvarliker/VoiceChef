using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TMPro;
using UnityEngine.UI;

public class IngredientListUI : MonoBehaviour
{
    [Header("UI References")]
    public TMP_Text ingredientTextPrefab;
    public Transform contentParent;

    [Header("Paging Settings")]
    public int itemsPerPage = 4;
    public float pageDuration = 4f;

    [Header("Animation")]
    public float fadeDuration = 0.25f;

    private List<string> ingredients = new();
    private List<TMP_Text> activeTexts = new();
    private int currentPage = 0;

    // =============================
    // PUBLIC ENTRY
    // =============================

    public void LoadIngredients(List<string> newIngredients)
    {
        StopAllCoroutines();
        ClearTexts();

        ingredients = newIngredients;
        currentPage = 0;

        ShowPage();
        StartCoroutine(PageRoutine());
    }

    // =============================
    // TEST
    // =============================

    [ContextMenu("TEST Paging")]
    void TestLoad()
    {
        LoadIngredients(new List<string>
        {
            "elma",
            "armut",
            "mandalina",
            "kiraz",
            "un",
            "yoğurt",
            "su",
            "pekmez"
        });
    }

    // =============================
    // PAGE LOGIC (FIXED)
    // =============================

    IEnumerator PageRoutine()
    {
        while (true)
        {
            yield return new WaitForSeconds(pageDuration);

            yield return StartCoroutine(FadeOutCurrent());

            currentPage++;

            int start = currentPage * itemsPerPage;
            if (start >= ingredients.Count)
                yield break; // NOW it stops correctly

            ShowPage();
        }
    }

    void ShowPage()
    {
        ClearTexts();

        int start = currentPage * itemsPerPage;
        int end = Mathf.Min(start + itemsPerPage, ingredients.Count);

        for (int i = start; i < end; i++)
        {
            TMP_Text txt = Instantiate(ingredientTextPrefab, contentParent);
            txt.text = "• " + ingredients[i];

            if (!txt.TryGetComponent(out CanvasGroup cg))
                cg = txt.gameObject.AddComponent<CanvasGroup>();

            cg.alpha = 0f;
            activeTexts.Add(txt);
            StartCoroutine(FadeIn(cg));
        }

        LayoutRebuilder.ForceRebuildLayoutImmediate(
            contentParent.GetComponent<RectTransform>()
        );
    }

    // =============================
    // CLEANUP
    // =============================

    void ClearTexts()
    {
        foreach (var t in activeTexts)
            if (t != null) Destroy(t.gameObject);

        activeTexts.Clear();
    }

    // =============================
    // ANIMATIONS
    // =============================

    IEnumerator FadeIn(CanvasGroup cg)
    {
        float t = 0f;
        while (t < fadeDuration)
        {
            t += Time.deltaTime;
            cg.alpha = t / fadeDuration;
            yield return null;
        }
        cg.alpha = 1f;
    }

    IEnumerator FadeOutCurrent()
    {
        foreach (var txt in activeTexts)
            if (txt.TryGetComponent(out CanvasGroup cg))
                StartCoroutine(FadeOut(cg));

        yield return new WaitForSeconds(fadeDuration);
        ClearTexts();
    }

    IEnumerator FadeOut(CanvasGroup cg)
    {
        float t = 0f;
        while (t < fadeDuration)
        {
            t += Time.deltaTime;
            cg.alpha = 1f - (t / fadeDuration);
            yield return null;
        }
        cg.alpha = 0f;
    }
}

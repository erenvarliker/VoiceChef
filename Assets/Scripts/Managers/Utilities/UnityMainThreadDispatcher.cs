using System;
using System.Collections.Generic;
using UnityEngine;

public class UnityMainThreadDispatcher : MonoBehaviour
{
    private static UnityMainThreadDispatcher _instance;
    private static readonly Queue<Action> _executionQueue = new Queue<Action>();

    public static UnityMainThreadDispatcher Instance
    {
        get
        {
            if (_instance == null)
            {
                // Try to find an existing dispatcher
                _instance = FindObjectOfType<UnityMainThreadDispatcher>();

                // If none exists, create a new GameObject
                if (_instance == null)
                {
                    GameObject obj = new GameObject("UnityMainThreadDispatcher");
                    _instance = obj.AddComponent<UnityMainThreadDispatcher>();
                    DontDestroyOnLoad(obj);
                }
            }
            return _instance;
        }
    }

    public void Enqueue(Action action)
    {
        lock (_executionQueue)
        {
            _executionQueue.Enqueue(action);
        }
    }

    private void Update()
    {
        lock (_executionQueue)
        {
            while (_executionQueue.Count > 0)
            {
                Action action = _executionQueue.Dequeue();
                action.Invoke();
            }
        }
    }
}

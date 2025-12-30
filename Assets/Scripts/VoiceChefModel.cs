using System;
using System.Collections.Generic;

[Serializable]
public class SessionStatus
{
    public string session_id;
    public string dish_name;
    public int current_step_index;
    public int total_steps;
    public bool is_paused;
    public string active_warning;
    public StepInfo current_step;

    // New fields for your Prefabs
    public string[] ingredients;
    public TimerInfo[] timers;
}

[Serializable]
public class StepInfo
{
    public int step_number;
    public string title;
    public string instruction;
    public string estimated_time;
}

[Serializable]
public class TimerInfo
{
    public string timer_id;
    public float remaining_seconds;
    public float total_seconds;
}
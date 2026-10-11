using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using UnityEngine;

namespace AnalogSewing
{
    [BepInPlugin(Guid, Name, Version)]
    public class Plugin : BaseUnityPlugin
    {
        public const string Guid = "xamspanda.dressmaker.analogsewing";
        public const string Name = "Analog Sewing";
        public const string Version = "1.0.0";

        internal static ManualLogSource Log;

        internal static ConfigEntry<string> SewKey;
        internal static ConfigEntry<float> StartDepthMm;
        internal static ConfigEntry<float> FullSpeedDepthMm;
        internal static ConfigEntry<int> MinSpeedPercent;
        internal static ConfigEntry<int> MaxSpeedPercent;
        internal static ConfigEntry<float> Curve;
        internal static ConfigEntry<float> KeyTravelMm;
        internal static ConfigEntry<bool> MoveSpeedSlider;

        private void Awake()
        {
            Log = Logger;
            BindConfig();

            if (!HidKeys.TryParse(SewKey.Value, out _))
                Log.LogWarning($"Unknown SewKey '{SewKey.Value}', using Space. Use a key name like Space, F, LeftShift, or a HID code like 0x2C.");

            AnalogInput.Start();
            Patches.Apply(new Harmony(Guid));
            Log.LogInfo($"{Name} {Version} loaded (game version {Application.version})");
        }

        private void OnApplicationQuit() => AnalogInput.Stop();

        private void BindConfig()
        {
            SewKey = Config.Bind("Input", "SewKey", "Space",
                "Analog key that drives the sewing machine: a key name (Space, F, LeftShift, ...) or a HID usage code (0x2C).");

            StartDepthMm = Config.Bind("Sewing", "StartDepthMm", 0.4f,
                new ConfigDescription("How far (mm) the key must be pressed before the machine starts sewing, at minimum speed. " +
                    "This replaces the keyboard's own actuation point and Rapid Trigger for the sew key.",
                    new AcceptableValueRange<float>(0.1f, 3.9f)));
            FullSpeedDepthMm = Config.Bind("Sewing", "FullSpeedDepthMm", 3.6f,
                new ConfigDescription("How far (mm) the key must be pressed to reach maximum speed.",
                    new AcceptableValueRange<float>(0.2f, 4.0f)));
            MinSpeedPercent = Config.Bind("Sewing", "MinSpeedPercent", 5,
                new ConfigDescription("Machine speed (% of the game's maximum) at the start depth.",
                    new AcceptableValueRange<int>(0, 100)));
            MaxSpeedPercent = Config.Bind("Sewing", "MaxSpeedPercent", 100,
                new ConfigDescription("Machine speed (% of the game's maximum) at the full-speed depth.",
                    new AcceptableValueRange<int>(1, 100)));
            Curve = Config.Bind("Sewing", "Curve", 1.5f,
                new ConfigDescription("Response curve between the two depths. 1 = linear, higher = finer control at low speed, " +
                    "lower = reaches high speed sooner.",
                    new AcceptableValueRange<float>(0.25f, 4f)));
            KeyTravelMm = Config.Bind("Advanced", "KeyTravelMm", 4.0f,
                new ConfigDescription("Total travel of your switches; the SDK reports depth as a fraction of this. " +
                    "4.0 for Lekker and most Wooting switches.",
                    new AcceptableValueRange<float>(1f, 6f)));
            MoveSpeedSlider = Config.Bind("Display", "MoveSpeedSlider", true,
                "Move the sewing machine's speed slider to show the current speed while sewing with the analog key.");
        }
    }
}

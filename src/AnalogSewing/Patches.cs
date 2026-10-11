using System;
using System.Reflection;
using HarmonyLib;
using UnityEngine;

namespace AnalogSewing
{
    // Two hooks into the game's sewing code:
    //   InputReader.SewButton               - "is the sew key held?" (vanilla: Space or right mouse)
    //   SewingController.ComputeFeedSpeed() - feed speed while sewing (vanilla: max speed * speed slider)
    internal static class Patches
    {
        private const float ReleaseHysteresisMm = 0.15f;

        private static Func<bool> _acceptInput;
        private static bool _holding;
        private static int _frame = -1;

        public static void Apply(Harmony harmony)
        {
            var acceptInput = AccessTools.PropertyGetter(typeof(InputReader), "AcceptInput");
            if (acceptInput != null) _acceptInput = (Func<bool>)Delegate.CreateDelegate(typeof(Func<bool>), acceptInput);

            if (_acceptInput != null)
                Patch(harmony, AccessTools.PropertyGetter(typeof(InputReader), nameof(InputReader.SewButton)), postfix: nameof(SewButtonPostfix));
            else
                Plugin.Log.LogWarning("InputReader.AcceptInput not found; the keyboard's own actuation will decide when sewing starts");

            Patch(harmony, AccessTools.Method(typeof(SewingController), "ComputeFeedSpeed"), prefix: nameof(ComputeFeedSpeedPrefix));
        }

        private static void Patch(Harmony harmony, MethodBase target, string prefix = null, string postfix = null)
        {
            var name = prefix ?? postfix;
            if (target == null)
            {
                Plugin.Log.LogError($"Hook for {name} not found; a game update may have changed it. This part of the mod is disabled.");
                return;
            }
            try
            {
                harmony.Patch(target,
                    prefix: prefix == null ? null : new HarmonyMethod(typeof(Patches), prefix),
                    postfix: postfix == null ? null : new HarmonyMethod(typeof(Patches), postfix));
            }
            catch (Exception e)
            {
                Plugin.Log.LogError($"Failed to hook {target.DeclaringType?.Name}.{target.Name}: {e}");
            }
        }

        /// <summary>Whether the analog key is pressed past the start depth (with hysteresis), updated once per frame.</summary>
        private static bool Holding(out float depthMm)
        {
            var live = AnalogInput.TryGetDepthMm(out depthMm);
            if (_frame != Time.frameCount)
            {
                _frame = Time.frameCount;
                var start = Plugin.StartDepthMm.Value;
                // The SDK sees the keyboard even when another window has focus (e.g. typing in Discord
                // after alt-tab), unlike the game's own input, so ignore the key while unfocused.
                if (!live || !Application.isFocused) _holding = false;
                else if (!_holding && depthMm >= start) _holding = true;
                else if (_holding && depthMm < Mathf.Max(0.05f, start - ReleaseHysteresisMm)) _holding = false;
            }
            return _holding;
        }

        private static float SpeedFraction(float depthMm)
        {
            var start = Plugin.StartDepthMm.Value;
            var full = Plugin.FullSpeedDepthMm.Value;
            var t = full > start ? Mathf.InverseLerp(start, full, depthMm) : 1f;
            t = Mathf.Pow(t, Plugin.Curve.Value);
            return Mathf.Lerp(Plugin.MinSpeedPercent.Value, Plugin.MaxSpeedPercent.Value, t) / 100f;
        }

        private static void SewButtonPostfix(ref bool __result)
        {
            if (!AnalogInput.TryGetDepthMm(out _)) return;
            var holding = Holding(out _);
            HidKeys.TryParse(Plugin.SewKey.Value, out var code);

            if (code == HidKeys.Space)
                // The analog depth replaces Space's digital press, so the keyboard's actuation point
                // and Rapid Trigger no longer matter. Right mouse still sews as normal.
                __result = _acceptInput() && (holding || Input.GetMouseButton(1));
            else
                __result |= _acceptInput() && holding;
        }

        private static bool ComputeFeedSpeedPrefix(SewingController __instance, SewingSpeedControl ___speedControl, ref float __result)
        {
            if (!Holding(out var depthMm) || !InputReader.SewButton) return true;

            var speed = SpeedFraction(depthMm);
            if (Plugin.MoveSpeedSlider.Value && ___speedControl != null) ___speedControl.SpeedSetting = speed;
            __result = __instance.fabricSpeedMax * speed;
            return false;
        }
    }
}

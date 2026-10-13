using System;
using System.Reflection;
using BepInEx;
using BepInEx.Bootstrap;
using BepInEx.Configuration;
using UnityEngine;

namespace AnalogSewing
{
    // Optional integration with Yuuma's Dressmaker ModLoader: author and credits in its Mod Manager, an
    // "Analog Sewing" tab in its Mod Settings window, the analog key following its Sew keybind, and no sewing
    // while it holds the keyboard (typing in a text field, capturing a keybind, or the debug console open).
    // Uses its public API by reflection so the mod builds and runs without it. The Mod Manager icon
    // (ModManagerIcon) is the one part that relies on its private code.
    internal static class ModLoader
    {
        public const string Guid = "yuu.dressmaker.mods";

        private static Func<bool> _inputSuppressed;
        private static Func<bool> _consoleOpen;

        /// <summary>Whether the mod loader has taken the keyboard away from the game.</summary>
        public static bool BlocksInput => (_inputSuppressed?.Invoke() ?? false) || (_consoleOpen?.Invoke() ?? false);

        public static void Init(BaseUnityPlugin plugin)
        {
            if (!Chainloader.PluginInfos.TryGetValue(Guid, out var info) || info.Instance == null) return;
            var asm = info.Instance.GetType().Assembly;

            if (info.Instance.Config.TryGetEntry<KeyCode>("Keybinds", "SewPrimary", out var primary) &&
                info.Instance.Config.TryGetEntry<KeyCode>("Keybinds", "SewAlternate", out var alternate))
                SewKeys.FollowModLoader(primary, alternate);
            else
                Plugin.Log.LogWarning("Mod Loader's Sew keybind not found; using the SewKey setting");

            try
            {
                RegisterMod(asm, plugin);
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning($"Couldn't register with Mod Loader {info.Metadata.Version}: {e.GetBaseException().Message}");
            }

            try
            {
                ModManagerIcon.Apply(asm);
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning($"Couldn't add the icon to Mod Loader {info.Metadata.Version}'s Mod Manager: {e.GetBaseException().Message}");
            }

            try
            {
                _inputSuppressed = StaticGetter(asm, "DressmakerMods.ModKeybindApi", "InputSuppressed");
                _consoleOpen = StaticGetter(asm, "DressmakerMods.DebugConsoleApi", "IsOpen");
                if (_inputSuppressed == null || _consoleOpen == null)
                    Plugin.Log.LogWarning("Mod Loader input API not found; sewing won't pause while typing in its text fields");

                RegisterSettings(asm);
                Plugin.Log.LogInfo($"Added settings to Mod Loader {info.Metadata.Version}");
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning($"Couldn't add settings to Mod Loader {info.Metadata.Version}; " +
                    $"edit the config file or use ConfigurationManager instead. {e.GetBaseException().Message}");
            }
        }

        // Fills in the author, description and credits shown in the Mod Manager.
        private static void RegisterMod(Assembly asm, BaseUnityPlugin plugin)
        {
            var infoType = asm.GetType("DressmakerMods.ModInfo", throwOnError: true);
            var modInfo = Activator.CreateInstance(infoType);
            infoType.GetProperty("Author").SetValue(modInfo, "xamspanda", null);
            infoType.GetProperty("Description").SetValue(modInfo,
                "Use a Wooting analog keyboard like a sewing machine foot pedal: press the sew key lightly to sew slowly, harder to sew faster.", null);
            infoType.GetProperty("Credits").SetValue(modInfo, "Wooting Analog SDK (MPL-2.0)", null);
            asm.GetType("DressmakerMods.ModLoaderApi", throwOnError: true)
                .GetMethod("Register", BindingFlags.Public | BindingFlags.Static)
                .Invoke(null, new[] { plugin, modInfo });
        }

        private static void RegisterSettings(Assembly asm)
        {
            Type Find(string name) => asm.GetType("DressmakerMods." + name, throwOnError: true);
            var slider = Find("ModSliderSetting");
            var toggle = Find("ModToggleSetting");
            var action = Find("ModActionSetting");

            object Slider(ConfigEntry<float> entry, string title, string description, string suffix, bool wholeNumbers = false)
            {
                var range = (AcceptableValueRange<float>)entry.Description.AcceptableValues;
                return Activator.CreateInstance(slider, title, description, entry, range.MinValue, range.MaxValue, wholeNumbers, suffix);
            }

            var items = new[]
            {
                Slider(Plugin.StartDepthMm, "Start depth", "How far to press before the machine starts, at minimum speed.", " mm"),
                Slider(Plugin.FullSpeedDepthMm, "Full-speed depth", "How far to press for maximum speed.", " mm"),
                Slider(Plugin.MinSpeedPercent, "Minimum speed", "Speed at the start depth, as % of the game's maximum.", "%", wholeNumbers: true),
                Slider(Plugin.MaxSpeedPercent, "Maximum speed", "Speed at the full-speed depth.", "%", wholeNumbers: true),
                Slider(Plugin.Curve, "Response curve", "1 is linear; higher gives finer control at low speed.", ""),
                Slider(Plugin.KeyTravelMm, "Key travel", "Your switches' total travel (4 mm for most Wooting switches).", " mm"),
                Activator.CreateInstance(toggle, "Move speed slider", "Show the current speed on the sewing machine's slider.", Plugin.MoveSpeedSlider),
                Activator.CreateInstance(action, "Reset to defaults", "Restore every Analog Sewing setting above.", (Func<string>)ResetToDefaults),
            };
            var settings = Array.CreateInstance(Find("ModSetting"), items.Length);
            Array.Copy(items, settings, items.Length);

            Find("ModSettingsApi").GetMethod("Register", BindingFlags.Public | BindingFlags.Static)
                .Invoke(null, new object[] { "xamspanda.analog-sewing", Plugin.Name, settings });
        }

        private static string ResetToDefaults()
        {
            foreach (var entry in new ConfigEntryBase[]
                { Plugin.StartDepthMm, Plugin.FullSpeedDepthMm, Plugin.MinSpeedPercent, Plugin.MaxSpeedPercent,
                  Plugin.Curve, Plugin.KeyTravelMm, Plugin.MoveSpeedSlider })
                entry.BoxedValue = entry.DefaultValue;
            return "Analog Sewing settings reset";
        }

        private static Func<bool> StaticGetter(Assembly asm, string type, string property)
        {
            var getter = asm.GetType(type)?.GetProperty(property, BindingFlags.Public | BindingFlags.Static)?.GetGetMethod();
            return getter == null ? null : (Func<bool>)Delegate.CreateDelegate(typeof(Func<bool>), getter);
        }
    }
}

using System.Collections.Generic;
using System.Linq;
using BepInEx.Configuration;
using UnityEngine;

namespace AnalogSewing
{
    // Which keys sew with analog depth. With Yuuma's Dressmaker ModLoader these are the keyboard keys bound to
    // its Sew keybind, so rebinding there moves the analog key too; otherwise it's the Input.SewKey setting.
    internal static class SewKeys
    {
        private static ConfigEntry<KeyCode> _loaderPrimary;
        private static ConfigEntry<KeyCode> _loaderAlternate;

        private static bool _resolved;
        private static (KeyCode, KeyCode, string) _source;
        private static ushort[] _analog = new ushort[0];
        private static KeyCode[] _gameKeys = new KeyCode[0];

        /// <summary>HID codes of the keys whose depth drives the machine (deepest one wins).</summary>
        public static ushort[] Analog { get { Refresh(); return _analog; } }

        /// <summary>Analog keys the game also treats as digital sew keys; their digital press is replaced by the depth.</summary>
        public static KeyCode[] GameKeys { get { Refresh(); return _gameKeys; } }

        public static void FollowModLoader(ConfigEntry<KeyCode> primary, ConfigEntry<KeyCode> alternate)
        {
            _loaderPrimary = primary;
            _loaderAlternate = alternate;
            _resolved = false;
        }

        // Re-resolved only when a binding changes, so rebinding in-game takes effect immediately.
        private static void Refresh()
        {
            var source = (_loaderPrimary?.Value ?? KeyCode.None, _loaderAlternate?.Value ?? KeyCode.None, Plugin.SewKey.Value);
            if (_resolved && source.Equals(_source)) return;
            _resolved = true;
            _source = source;

            if (_loaderPrimary != null)
            {
                var keys = new[] { source.Item1, source.Item2 }.Where(k => HidKeys.TryFromKeyCode(k, out _)).Distinct().ToArray();
                _gameKeys = keys;
                _analog = keys.Select(k => { HidKeys.TryFromKeyCode(k, out var code); return code; }).ToArray();
                Plugin.Log.LogInfo(keys.Length > 0
                    ? $"Analog sew key follows Mod Loader's Sew keybind: {string.Join(", ", keys.Select(k => k.ToString()).ToArray())}"
                    : "Mod Loader's Sew keybind has no keyboard keys; analog sewing is off");
            }
            else
            {
                HidKeys.TryParse(source.Item3, out var code);
                _analog = new[] { code };
                // The vanilla game only sews with Space (and right mouse).
                _gameKeys = code == HidKeys.Space ? new[] { KeyCode.Space } : new KeyCode[0];
            }
        }
    }
}

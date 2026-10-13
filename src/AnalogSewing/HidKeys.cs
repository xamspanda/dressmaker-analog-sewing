using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

namespace AnalogSewing
{
    // Key names -> USB HID keyboard usage codes, which is what the Wooting SDK reads by default.
    internal static class HidKeys
    {
        public const ushort Space = 0x2C;

        private static readonly Dictionary<string, ushort> Named = new Dictionary<string, ushort>(StringComparer.OrdinalIgnoreCase)
        {
            ["Space"] = 0x2C, ["Enter"] = 0x28, ["Return"] = 0x28, ["Escape"] = 0x29, ["Backspace"] = 0x2A,
            ["Tab"] = 0x2B, ["CapsLock"] = 0x39, ["Minus"] = 0x2D, ["Equals"] = 0x2E, ["LeftBracket"] = 0x2F,
            ["RightBracket"] = 0x30, ["Backslash"] = 0x31, ["Semicolon"] = 0x33, ["Quote"] = 0x34,
            ["Backquote"] = 0x35, ["Comma"] = 0x36, ["Period"] = 0x37, ["Slash"] = 0x38,
            ["Right"] = 0x4F, ["Left"] = 0x50, ["Down"] = 0x51, ["Up"] = 0x52,
            ["LeftControl"] = 0xE0, ["LeftShift"] = 0xE1, ["LeftAlt"] = 0xE2, ["LeftWindows"] = 0xE3,
            ["RightControl"] = 0xE4, ["RightShift"] = 0xE5, ["RightAlt"] = 0xE6, ["RightWindows"] = 0xE7,
        };

        public static bool TryParse(string name, out ushort code)
        {
            name = (name ?? "").Trim();
            if (Named.TryGetValue(name, out code)) return true;
            if (name.Length == 1 && char.IsLetter(name[0]))
            {
                code = (ushort)(0x04 + char.ToUpperInvariant(name[0]) - 'A');
                return true;
            }
            if (name.Length == 1 && char.IsDigit(name[0]))
            {
                code = (ushort)(name[0] == '0' ? 0x27 : 0x1E + name[0] - '1');
                return true;
            }
            if (name.Length >= 2 && (name[0] == 'F' || name[0] == 'f') && int.TryParse(name.Substring(1), out var f) && f >= 1 && f <= 12)
            {
                code = (ushort)(0x3A + f - 1);
                return true;
            }
            if (name.StartsWith("0x", StringComparison.OrdinalIgnoreCase) &&
                ushort.TryParse(name.Substring(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out code))
                return true;
            code = Space;
            return false;
        }

        /// <summary>Maps a Unity key (e.g. from Mod Loader keybinds) to its HID code; false for mouse buttons and unmapped keys.</summary>
        public static bool TryFromKeyCode(KeyCode key, out ushort code)
        {
            var name = key.ToString();
            if (name.StartsWith("Alpha")) name = name.Substring(5);                  // Alpha1 -> 1
            else if (name.EndsWith("Arrow")) name = name.Substring(0, name.Length - 5); // UpArrow -> Up
            if (key != KeyCode.None && TryParse(name, out code)) return true;
            code = 0;
            return false;
        }
    }
}

using System;
using System.IO;
using System.Runtime.InteropServices;
using UnityEngine;

namespace AnalogSewing
{
    // Current depth of the sew key, read from the bundled Wooting Analog SDK.
    internal static class AnalogInput
    {
        private const string Dll = "wooting_analog_sdk_dist";

        [DllImport("kernel32", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr LoadLibraryW(string path);

        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)]
        private static extern int wooting_analog_initialise();

        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)]
        private static extern int wooting_analog_uninitialise();

        [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)]
        private static extern float wooting_analog_read_analog(ushort code);

        private static bool _ready;
        private static int _frame = -1;
        private static float _depth01;
        private static bool _live;
        private static bool? _loggedLive;

        public static void Start()
        {
            try
            {
                // Load the bundled DLL by full path so P/Invoke finds it next to this plugin.
                var path = Path.Combine(Path.GetDirectoryName(typeof(Plugin).Assembly.Location), Dll + ".dll");
                if (LoadLibraryW(path) == IntPtr.Zero)
                {
                    Plugin.Log.LogWarning($"Could not load {path} (error {Marshal.GetLastWin32Error()}); analog sewing disabled");
                    return;
                }
                var result = wooting_analog_initialise();
                _ready = result >= 0;
                if (_ready) Plugin.Log.LogInfo($"Wooting Analog SDK initialised, {result} device(s) connected");
                else Plugin.Log.LogWarning($"Wooting Analog SDK failed to initialise (code {result})");
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning($"Wooting Analog SDK unavailable: {e.Message}");
            }
        }

        public static void Stop()
        {
            if (!_ready) return;
            _ready = false;
            try { wooting_analog_uninitialise(); } catch { }
        }

        /// <summary>Key depth in millimetres, or false when no keyboard is available (falls back to vanilla controls).</summary>
        public static bool TryGetDepthMm(out float mm)
        {
            if (_frame != Time.frameCount)
            {
                _frame = Time.frameCount;
                Poll();
            }
            mm = _depth01 * Plugin.KeyTravelMm.Value;
            return _live;
        }

        // The SDK reads devices on its own threads and rescans for new ones every few seconds,
        // so this is a cheap lookup; negative values are error codes such as NoDevices.
        private static void Poll()
        {
            _live = false;
            _depth01 = 0f;
            if (_ready)
            {
                HidKeys.TryParse(Plugin.SewKey.Value, out var code);
                var v = wooting_analog_read_analog(code);
                if (v >= 0f)
                {
                    _live = true;
                    _depth01 = Mathf.Clamp01(v);
                }
            }

            if (_live != _loggedLive)
            {
                _loggedLive = _live;
                Plugin.Log.LogInfo(_live
                    ? "Reading key depth from the Wooting Analog SDK"
                    : "No analog keyboard found; using the game's normal controls");
            }
        }
    }
}

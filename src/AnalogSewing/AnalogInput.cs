using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using UnityEngine;

namespace AnalogSewing
{
    public enum InputSource { Auto, WootingSdk, LinuxBridge }

    // Current depth of the sew key, from whichever source is delivering data this frame.
    internal static class AnalogInput
    {
        private enum Live { None, Sdk, Bridge }

        private static int _frame = -1;
        private static float _depth01;
        private static Live _live = Live.None;
        private static Live _loggedLive = Live.None;

        public static void Start()
        {
            if (Plugin.Source.Value != InputSource.LinuxBridge) WootingSdk.Init();
            if (Plugin.Source.Value != InputSource.WootingSdk) Bridge.Listen(Plugin.BridgePort.Value);
        }

        public static void Stop()
        {
            WootingSdk.Shutdown();
            Bridge.Close();
        }

        /// <summary>Key depth in millimetres, or false when no source has data (falls back to vanilla controls).</summary>
        public static bool TryGetDepthMm(out float mm)
        {
            if (_frame != Time.frameCount)
            {
                _frame = Time.frameCount;
                Poll();
            }
            mm = _depth01 * Plugin.KeyTravelMm.Value;
            return _live != Live.None;
        }

        private static void Poll()
        {
            HidKeys.TryParse(Plugin.SewKey.Value, out var code);
            if (WootingSdk.TryRead(code, out _depth01)) _live = Live.Sdk;
            else if (Bridge.TryRead(out _depth01)) _live = Live.Bridge;
            else { _live = Live.None; _depth01 = 0f; }

            if (_live != _loggedLive)
            {
                _loggedLive = _live;
                Plugin.Log.LogInfo(_live switch
                {
                    Live.Sdk => "Reading key depth from the Wooting Analog SDK",
                    Live.Bridge => "Reading key depth from the Linux bridge",
                    _ => "No analog keyboard found; using the game's normal controls",
                });
            }
        }

        private static class WootingSdk
        {
            private const string Dll = "wooting_analog_sdk_dist";
            private const float NoDevices = -1999f;

            [DllImport("kernel32", CharSet = CharSet.Unicode, SetLastError = true)]
            private static extern IntPtr LoadLibraryW(string path);

            [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)]
            private static extern int wooting_analog_initialise();

            [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)]
            private static extern int wooting_analog_uninitialise();

            [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)]
            private static extern float wooting_analog_read_analog(ushort code);

            private static bool _ready;

            public static void Init()
            {
                try
                {
                    // Load the bundled DLL by full path so P/Invoke finds it next to this plugin.
                    var path = Path.Combine(Path.GetDirectoryName(typeof(Plugin).Assembly.Location), Dll + ".dll");
                    if (LoadLibraryW(path) == IntPtr.Zero)
                    {
                        Plugin.Log.LogWarning($"Could not load {path} (error {Marshal.GetLastWin32Error()}); Wooting SDK disabled");
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

            // The SDK reads devices on its own threads and rescans for new ones every few seconds,
            // so this is a cheap lookup; negative values are error codes such as NoDevices.
            public static bool TryRead(ushort code, out float depth01)
            {
                depth01 = 0f;
                if (!_ready) return false;
                var v = wooting_analog_read_analog(code);
                if (v < 0f) return false;
                depth01 = Mathf.Clamp01(v);
                return true;
            }

            public static void Shutdown()
            {
                if (!_ready) return;
                _ready = false;
                try { wooting_analog_uninitialise(); } catch { }
            }
        }

        private static class Bridge
        {
            private const double TimeoutSeconds = 0.5;

            private static readonly Stopwatch Clock = Stopwatch.StartNew();
            private static UdpClient _udp;
            private static float _depth;
            private static long _lastTicks = long.MinValue / 2;

            public static void Listen(int port)
            {
                try
                {
                    _udp = new UdpClient(new IPEndPoint(IPAddress.Loopback, port));
                    new Thread(Receive) { IsBackground = true, Name = "AnalogSewing bridge" }.Start();
                }
                catch (Exception e)
                {
                    Plugin.Log.LogWarning($"Could not listen for the Linux bridge on UDP {port}: {e.Message}");
                }
            }

            public static void Close() => _udp?.Close();

            public static bool TryRead(out float depth01)
            {
                depth01 = Volatile.Read(ref _depth);
                var age = (Clock.ElapsedTicks - Interlocked.Read(ref _lastTicks)) / (double)Stopwatch.Frequency;
                return age <= TimeoutSeconds;
            }

            private static void Receive()
            {
                var from = new IPEndPoint(IPAddress.Any, 0);
                while (true)
                {
                    try
                    {
                        var text = Encoding.ASCII.GetString(_udp.Receive(ref from)).Trim();
                        if (float.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
                        {
                            Volatile.Write(ref _depth, Mathf.Clamp01(d));
                            Interlocked.Exchange(ref _lastTicks, Clock.ElapsedTicks);
                        }
                    }
                    catch (ObjectDisposedException) { return; }
                    catch (SocketException) when (_udp.Client == null) { return; }
                    catch (Exception e) { Plugin.Log.LogWarning($"Bridge receive failed: {e.Message}"); Thread.Sleep(500); }
                }
            }
        }
    }
}

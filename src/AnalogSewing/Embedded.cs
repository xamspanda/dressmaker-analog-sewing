using System;
using System.IO;
using System.Security.Cryptography;
using BepInEx;

namespace AnalogSewing
{
    // Files embedded in AnalogSewing.dll so the plugin is a single file (Yuuma's Dressmaker ModLoader installs
    // plugins as one DLL), unpacked under BepInEx/cache when needed.
    internal static class Embedded
    {
        /// <summary>Unpacks the named resource and returns its path. Each version gets its own folder, so an update
        /// never has to overwrite a copy that's in use, and the file keeps its name (P/Invoke finds DLLs by name).</summary>
        public static string Unpack(string name)
        {
            byte[] bytes;
            using (var resource = typeof(Plugin).Assembly.GetManifestResourceStream(name))
            using (var buffer = new MemoryStream())
            {
                if (resource == null) throw new FileNotFoundException($"{name} is missing from AnalogSewing.dll");
                resource.CopyTo(buffer);
                bytes = buffer.ToArray();
            }

            string hash;
            using (var sha = SHA256.Create())
                hash = BitConverter.ToString(sha.ComputeHash(bytes), 0, 6).Replace("-", "").ToLowerInvariant();
            var dir = Path.Combine(Path.Combine(Paths.CachePath, "AnalogSewing"), hash);
            var path = Path.Combine(dir, name);
            if (!File.Exists(path) || new FileInfo(path).Length != bytes.Length)
            {
                Directory.CreateDirectory(dir);
                var temp = path + ".tmp";
                File.WriteAllBytes(temp, bytes);
                if (File.Exists(path)) File.Delete(path);
                File.Move(temp, path);
            }
            return path;
        }
    }
}

using System;
using System.IO;
using System.Reflection;
using HarmonyLib;

namespace AnalogSewing
{
    // Yuuma's Dressmaker ModLoader's Mod Manager draws a "DLL MOD" placeholder for every DLL mod, with no API for an
    // icon yet. Until there is one, draw our icon over the placeholder with its own pack-icon code (MakePackArt),
    // from a postfix on its private InGameModManager.DrawPackRow. If that code changes, this logs a warning and the
    // placeholder stays; nothing else depends on it.
    internal static class ModManagerIcon
    {
        private static Type _packType;
        private static FieldInfo _packId, _packFolder, _packIcon;
        private static MethodInfo _makePackArt;
        private static string _iconPath;

        public static void Apply(Assembly loader)
        {
            var manager = loader.GetType("DressmakerMods.InGameModManager", throwOnError: true);
            _packType = loader.GetType("DressmakerMods.ModPackInfo", throwOnError: true);
            _packId = AccessTools.Field(_packType, "Id");
            _packFolder = AccessTools.Field(_packType, "Folder");
            _packIcon = AccessTools.Field(_packType, "Icon");
            _makePackArt = AccessTools.Method(manager, "MakePackArt",
                new[] { _packType, typeof(float), typeof(float), typeof(float), typeof(float) });
            var drawPackRow = AccessTools.Method(manager, "DrawPackRow", new[] { _packType, _packType, typeof(int) });
            if (_packId == null || _packFolder == null || _packIcon == null || _makePackArt == null || drawPackRow == null)
                throw new MissingMemberException("Mod Manager's card drawing has changed");

            _iconPath = Embedded.Unpack("icon.png");
            new Harmony(Plugin.Guid).Patch(drawPackRow, postfix: new HarmonyMethod(typeof(ModManagerIcon), nameof(DrawPackRowPostfix)));
        }

        // DrawPackRow draws the placeholder at (9, y + 10), 94 x 94; drawing after it puts the icon on top.
        private static void DrawPackRowPostfix(object __instance, object pack, int y)
        {
            if (_iconPath == null || (string)_packId.GetValue(pack) != "plugin:" + Plugin.Guid) return;
            try
            {
                var art = Activator.CreateInstance(_packType);
                _packFolder.SetValue(art, Path.GetDirectoryName(_iconPath));
                _packIcon.SetValue(art, Path.GetFileName(_iconPath));
                _makePackArt.Invoke(__instance, new[] { art, 9f, y + 10f, 94f, 94f });
            }
            catch (Exception e)
            {
                _iconPath = null; // don't retry every frame the list redraws
                Plugin.Log.LogWarning($"Couldn't draw the icon in Mod Manager: {e.GetBaseException().Message}");
            }
        }
    }
}

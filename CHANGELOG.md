# Changelog

## 1.1.0

- Works with Yuuma's Dressmaker ModLoader:
  - Install and update it through the loader's Mod Manager.
  - The analog key follows its Sew keybind, and other sew bindings (like right mouse) keep working.
  - Settings can be changed in its Mod Settings window (Analog Sewing tab).
  - Its Mod Manager shows the mod's icon, author, description and credits.
  - The analog key doesn't sew while typing in a text field, setting a keybind or using its
    debug console.
- The mod is now a single file, `BepInEx/plugins/AnalogSewing.dll`, with the Wooting Analog SDK
  built in. When updating from 1.0.0, delete `AnalogSewing.dll` and `wooting_analog_sdk_dist.dll`
  from `BepInEx/plugins/AnalogSewing/`; the log reminds you if they're still there.
- MinSpeedPercent and MaxSpeedPercent accept decimals (existing config files still load).

## 1.0.0

- First release: sewing machine speed follows how far the sew key is pressed.
- Built-in Wooting Analog SDK (v0.9.1) on Windows and Linux/Proton.
- Configurable start depth, full-speed depth, speed range, response curve and sew key.
- The sew key is ignored while the game window isn't focused, so typing in other apps doesn't sew.

<div align=center>

# Configuration

</div>

> [!CAUTION]
> Avoid editing anything in `default_config.toml`, only edit `config.toml`.

All configurations are done through the `config.toml` file. First create the `config.toml` file in the `fabric-shell` directory, and add the following lines:
```
[app_settings]

[css_settings]

```
The `app_settings` header is used to configure the shell itself(i.e. icons, commands, etc.), while the `css_settings` is used to configure the style of the app(i.e. border-radius, padding, etc.). Most of the configurations will be under the `app_settings` header.

## Changing Applets
Fabric-shell currently has three applets: Dashboard(default), Powermenu, Wallpaper selector.
To change the currently open Applet, run `fabric-cli execute fabric-shell 'pill_window.change_applet("APPLET")'`. `APPLET` could be any one of `dashboard`, `powermenu`, `wallpaper`. To return to the default Applet(Dashboard) just press the `escape` key.

You can also toggle the Dashboard expand, or change back to the Dashboard from any other Applet using `fabric-cli execute fabric-shell 'pill_window.toggle_dashboard_expand()'`.

You can bind any of these commands to a keybind in your Hyprland config, ex:
```
bind = SUPER, W, exec, fabric-cli execute fabric-shell 'pill_window.change_applet("wallpaper")'
bind = SUPER SHIFT, L, exec, fabric-cli execute fabric-shell 'pill_window.change_applet("powermenu")'
bind = SUPER SHIFT, D, exec, fabric-cli execute fabric-shell 'pill_window.toggle_dashboard_expand()'
```

### Setup the Wallpaper selector Applet:

The Wallpaper selector Applet requires some configuration to work correctly. First, you'll need to define the `wallpapers_dir` and `wallpapers_thumbnails_cache_dir` variables under the `app_settings` in your `config.toml`. Refer to [Path Parsing](#path-parsing) for further information on how to define paths.

Next, you'll need to define how you want to set the selected wallpaper through the `change_wallpaper_command` variable. The variable can accept two arguments: `path` for the absolute path of the wallpaper, and `scheme` for the selected matugen scheme. An example of a script that'll set the wallpaper and update the matugen theme:

`change_wallpaper.sh`:
```sh
swww img "$1"
matugen -m dark image "$1" -t "$2"
```
Usage: 
```
change_wallpaper_command = "user_config_dir-change_wallpaper.sh '{path}' '{scheme}'"
```

> [!TIP]
> If you want to update the fabric-shell colors, add the `matugen-template.scss` file to your matugen config:
> ```
> [templates.fabric_shell]
> input_path = '~/.config/matugen/Templates/fabric-shell.scss'
> output_path = '~/.config/fabric-shell/styles/_colors.scss'
> ```

The `wallpaper` widget in the left bar displays a small thumbnail of the wallpaper in the bar. It uses the `wallpaper_file` **under the `css_settings` header** to show the wallpaper, meaning that it uses a static path. if the path isn't configured properly it'll show a blank space in the bar. The above `change_wallpaper.sh` snippet could be updated to copy the wallpaper to a static path to update the wallpaper widget:

```sh
static_path="~/.current-wallpaper"
cp -f "$1" "$static_path"

swww img "$static_path"
matugen -m dark image "$static_path" -t "$2"
```

and then you could update the `wallpaper_file` variable with the following path: `user_config_dir-../.current-wallpaper`.

### Configure the Powermenu Applet:

The Powermenu applet should work out of the box with most systems. There's currently four configurable actions, each has its own variable in the configuration file:
- `lock`: `power_menu_lock_commands`
- `suspend`: `power_menu_suspend_commands`
- `reboot`: `power_menu_reboot_commands`
- `shutdown`: `power_menu_shutdown_commands`

All of the above variables are actually arrays holding multiple commands. when executing the action, each command gets executed in order one after the other, the default `power_menu_suspend_commands` for example:
```
power_menu_suspend_commands = ["playerctl pause", "loginctl lock-session", "systemctl suspend"]
```

### Configure the Media Player Widget:

The media player widget actively monitors `playerctl` for new players, and if the player is in the `media_player_allowed_players` variable, it'll be added to the manged media players. The `media_player_allowed_players` variable is a key-value pair, the key is the name of the player, and the value is the icon that'll be used for this palyer in the tabs. The default value is: `media_player_allowed_players = { "spotify" = "󰓇" }`.

> [!TIP]
> To add new players to the `media_player_allowed_players`, monitor the output log for messages like: `Player {name} is available but won't be managed`, you can then use `name` in the `media_player_allowed_players` variable.

## Path parsing

Paths could be expressed in the config file in two different ways: either explicitly by using the absolute path, or by using `platformdirs` as a shortcut. The syntax is: `PLATFORMDIRS_FOLDER-PATH`. So for example, if i wanted to reference the `~/.config/some_file.ext` in the config, it should be written as `user_config_dir-some_file.ext`, which when parsed will give the absolute path of `some_file.ext`. Having hyphens `-` in the `PATH` is not an issue, i.e. `user_config_dir-file-name-with-hyphens.ext` will be parsed to `/home/USERNAME/.config/file-name-with-hyphens.ext`.

All `platformdirs` functions are supported, including but not limited to:
- `user_config_dir`
- `user_cache_dir`
- `user_log_dir`
- `user_documents_dir`
- `user_downloads_dir`
- `user_pictures_dir`
- `user_videos_dir`
- `user_music_dir`
- `user_desktop_dir`

> [!TIP]
> Relative paths and double dots are fully supported by the parser, so if you wanted to reference the user's home dir, you could use `user_config_dir-..`.

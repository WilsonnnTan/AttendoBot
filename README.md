# Discord Attendance Bot

A Discord bot that automates attendance tracking using Google Forms. The bot allows server administrators to configure attendance windows, manage Google Form URLs, and lets users mark their attendance with a simple command.

## Features

- 📝 Automated attendance tracking via Google Forms
- ⏰ Configurable attendance time windows
- 🌐 Timezone support
- 🔒 Admin-only configuration commands
- 📊 Easy attendance marking for users

## Commands

### Admin Commands

- `/add_gform_url <link>` — Set/update the Google Form URL for attendance
- `/delete_gform_url` — Remove the configured Google Form URL
- `/list_gform_url` — Show current Google Form URL
- `/set_attendance_time <day>/<HH:MM>-<HH:MM>` — Set attendance window
- `/show_attendance_time` — Display current attendance window
- `/delete_attendance_time` — Remove attendance window
- `/set_timezone <offset>` — Set server timezone (UTC-12 to UTC+14)
- `/show_timezone` — Display current timezone setting
- `/help` — Show all available commands

### User Commands

- `/hadir` — Mark attendance (only works during configured time window)

---

For setup, deployment, and technical documentation, see [DOCUMENTATION.md](Techinal-Documentation/README.md).

## License

This project is licensed under the terms specified in the LICENSE file.

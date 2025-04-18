# Discord Attendance Bot

A Discord bot that automates attendance tracking using Google Forms. The bot allows server administrators to configure attendance windows, manage Google Form URLs, and lets users mark their attendance with a simple command.

## Features

- 📝 Automated attendance tracking via Google Forms
- ⏰ Configurable attendance time windows
- 🌐 Timezone support
- 🔒 Admin-only configuration commands
- 📊 Easy attendance marking for users

## Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- PostgreSQL database

## Installation

### Local Development Setup

1. Clone the repository and navigate to the project directory:
```bash
git clone https://github.com/WilsonnnTan/Discord-Attendance-Bot.git
cd Discord-Attendance-Bot
```

2. Create and activate a virtual environment (recommended):
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/MacOS
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Windows
copy .env.example .env

# Linux/MacOS
cp .env.example .env
```

Then edit the `.env` file with your configuration:
```env
# Discord Bot Token (Required)
DISCORD_TOKEN=your_discord_bot_token

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

5. Initialize the database:
```bash
alembic upgrade head
```

### Docker Setup (Recommended for Production)

A Docker setup is available for easy deployment.

#### 1. Build the Docker image
```bash
docker build -t discord-attendance-bot .
```

#### 2. Configure environment variables
Copy `.env.example` to `.env` and edit it with your credentials, or set variables in your deployment environment.

#### 3. Run the bot container
```bash
docker run --env-file .env --name discord-attendance-bot discord-attendance-bot
```

#### 4. (Optional) Run as a background service
```bash
docker run -d --env-file .env --name discord-attendance-bot discord-attendance-bot
```

#### 5. Database Migrations
If you need to run Alembic migrations inside the container:
```bash
docker run --rm --env-file .env discord-attendance-bot alembic upgrade head
```

## Usage

1. Start the bot:
```bash
python app.py
```

2. Invite the bot to your server using the OAuth2 URL generator in the Discord Developer Portal.

3. Configure your server's attendance settings using the admin commands.

## Commands

### Admin Commands

- `!add_gform_url <link>` - Set/update the Google Form URL for attendance
- `!delete_gform_url` - Remove the configured Google Form URL
- `!list_gform_url` - Show current Google Form URL
- `!set_attendance_time <day>/<HH:MM>-<HH:MM>` - Set attendance window
- `!show_attendance_time` - Display current attendance window
- `!delete_attendance_time` - Remove attendance window
- `!set_timezone <offset>` - Set server timezone (UTC-12 to UTC+14)
- `!show_timezone` - Display current timezone setting
- `!help` - Show all available commands

### User Commands

- `!hadir` - Mark attendance (only works during configured time window)

## Setting Up Google Form

1. Create a Google Form with at least one text field for the name
2. Get the form URL (either full URL or shortened forms.gle link)
3. Use `!add_gform_url` command with the form URL
4. The bot will automatically handle form submissions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms specified in the LICENSE file.

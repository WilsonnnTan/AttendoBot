# Discord Attendance Bot — Technical Documentation

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Docker Setup](#docker-setup)
- [Environment Configuration](#environment-configuration)
- [Database Schema](#database-schema)
- [Business Logic](#business-logic)
- [Deployment](#deployment)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [License](#license)

---

## Architecture Overview

The Discord Attendance Bot is a modular Python application built on `discord.py`, using Google Forms for attendance collection and SQLAlchemy/Supabase for persistent storage. The bot restricts configuration commands to server admins for security.

**Key Components:**
- `app.py`: Bot entry point and event loop.
- `utils/GoogleForm.py`: Google Form integration and command implementations.
- `utils/database.py`: Database handler for CRUD operations.
- `schemas/models.py`: SQLAlchemy ORM models for the database.

---

## Docker Setup

### 1. Build the Docker image
```bash
docker build -t discord-attendance-bot .
```

### 2. Configure environment variables
Copy `.env.example` to `.env` and edit it with your credentials, or set variables in your deployment environment.

### 3. Run the bot container
```bash
docker run --env-file .env --name discord-attendance-bot discord-attendance-bot
```

### 4. (Optional) Run as a background service
```bash
docker run -d --env-file .env --name discord-attendance-bot discord-attendance-bot
```

### 5. Database Migrations
If you need to run Alembic migrations inside the container:
```bash
docker run --rm --env-file .env discord-attendance-bot alembic upgrade head
```

---

## Environment Configuration

Create a `.env` file based on `.env.example`:

```env
# Discord Bot Token (Required)
DISCORD_TOKEN=your_discord_bot_token

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# (Optional) Logging Level
LOG_LEVEL=WARNING
```

---

## Database Schema

### Tables
- **guilds**: Stores guild (server) configuration, including Google Form URL and attendance window.
- **attendances**: Records each user's attendance per guild.
- **Timezone**: Stores timezone offset per guild.

See `schemas/models.py` for SQLAlchemy ORM definitions.

---

## Business Logic

- **Attendance Marking**:  
  Users mark attendance with `!hadir`. The bot checks the configured time window and prevents duplicate attendance for the same day.

- **Google Form Integration**:  
  Admins configure a Google Form URL. The bot extracts field IDs, submits attendance, and validates URLs.

- **Admin Controls**:  
  Only users with `administrator` or `manage_guild` permissions can configure the bot.

- **Timezone & Attendance Window**:  
  Attendance is only accepted within the configured window and timezone.

---

## Deployment

- **Local:**  
  Follow the steps in the README for Python virtualenv setup.

- **Docker:**  
  See [Docker Setup](#docker-setup).

---

## Troubleshooting & FAQ

**Q: The bot doesn't respond to commands.**  
A: Check that the bot is running, has the correct token, and has permission to read/send messages in your Discord server.

**Q: Attendance is denied even during the correct window.**  
A: Verify your server timezone and attendance window configuration with `!show_timezone` and `!show_attendance_time`.

**Q: How do I reset the attendance window or form URL?**  
A: Use `!delete_attendance_time` or `!delete_gform_url` as an admin.

**Q: How do I migrate the database?**  
A: Use `alembic upgrade head` locally, or run the migration command inside your Docker container as shown above.

---

## License

This project is licensed under the terms specified in the LICENSE file.

---

For further questions or contributions, please submit an issue or pull request on GitHub.
